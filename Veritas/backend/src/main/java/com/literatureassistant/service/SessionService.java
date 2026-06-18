package com.literatureassistant.service;

import com.literatureassistant.cache.CacheEvictionHelper;
import com.literatureassistant.dto.common.PageResponse;
import com.literatureassistant.dto.request.SessionCreateRequest;
import com.literatureassistant.dto.response.SessionDetailResponse;
import com.literatureassistant.dto.response.SessionResponse;
import com.literatureassistant.entity.Session;
import com.literatureassistant.enums.SessionStatus;
import com.literatureassistant.exception.AuthenticationException;
import com.literatureassistant.exception.BusinessException;
import com.literatureassistant.exception.ResourceNotFoundException;
import com.literatureassistant.mapper.SessionMapper;
import com.literatureassistant.repository.AnalysisResultRepository;
import com.literatureassistant.repository.SessionRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class SessionService {

    private static final int DEFAULT_PAGE = 1;
    private static final int DEFAULT_SIZE = 10;
    private static final int MAX_SIZE = 100;

    private static final Map<SessionStatus, Set<SessionStatus>> ALLOWED_TRANSITIONS = Map.of(
            SessionStatus.ACTIVE, Set.of(SessionStatus.COMPLETED, SessionStatus.EXPIRED),
            SessionStatus.COMPLETED, Set.of(),
            SessionStatus.EXPIRED, Set.of()
    );

    private final SessionRepository sessionRepository;
    private final SessionMapper sessionMapper;
    private final AnalysisResultRepository analysisResultRepository;
    private final CacheEvictionHelper cacheEvictionHelper;

    @Transactional
    // P2-1: 移除 @CacheEvict(allEntries=true)，改用 CacheEvictionHelper 按用户前缀精准失效。
    // 原方案 allEntries=true 会清空整个 sessionList 缓存空间，影响其他用户的会话列表缓存。
    // 新方案在事务提交后按 "sessionList::session:list:{userId}:*" 前缀精准删除当前用户的分页缓存。
    public SessionResponse createSession(String userId, SessionCreateRequest request) {
        if (userId == null || userId.isBlank()) {
            throw new AuthenticationException("未认证，请先登录");
        }

        String sessionId = "ses_" + UUID.randomUUID().toString().replace("-", "").substring(0, 8);

        Session session = Session.builder()
                .sessionId(sessionId)
                .userId(userId)
                .topic(request.getTopic())
                .status(SessionStatus.ACTIVE)
                .build();

        Session saved = sessionRepository.save(session);

        // P2-1: 事务提交后精准失效该用户的会话列表缓存（写后删，避免脏读回填）
        cacheEvictionHelper.evictByPatternAfterCommit(
                "sessionList::session:list:" + userId + ":*");

        log.info("Session created: sessionId={}, userId={}", saved.getSessionId(), userId);

        return sessionMapper.toResponse(saved);
    }

    @org.springframework.cache.annotation.Cacheable(value = "sessionList",
            key = "T(com.literatureassistant.util.RedisKeyUtil).sessionListKey(#userId, #page, #size)")
    @Transactional(readOnly = true)
    public PageResponse<SessionResponse> listSessions(String userId, int page, int size) {
        if (userId == null || userId.isBlank()) {
            throw new AuthenticationException("未认证，请先登录");
        }

        int safePage = page < 1 ? DEFAULT_PAGE : page;
        int safeSize = size < 1 ? DEFAULT_SIZE : Math.min(size, MAX_SIZE);

        Pageable pageable = PageRequest.of(safePage - 1, safeSize);

        Page<Session> sessionPage = sessionRepository.findByUserIdOrderByCreatedAtDesc(userId, pageable);

        List<SessionResponse> items = sessionPage.getContent().stream()
                .map(sessionMapper::toResponse)
                .toList();

        log.info("Session list: userId={}, page={}, size={}, total={}",
                userId, safePage, safeSize, sessionPage.getTotalElements());

        return PageResponse.fromPage(sessionPage, items);
    }

    @Cacheable(value = "sessionState", key = "#sessionId", unless = "#result == null")
    @Transactional(readOnly = true)
    public SessionDetailResponse getSessionDetail(String sessionId) {
        // 修复 B-004: 数据隔离校验已上移到 Controller（validateSessionAccess），此处信任入参。
        // @Cacheable 命中时方法体不执行，内部 validateDataIsolation 会被绕过。
        Session session = sessionRepository.findBySessionId(sessionId)
                .orElseThrow(() -> new ResourceNotFoundException("Session", sessionId));

        SessionDetailResponse response = sessionMapper.toDetailResponse(session);
        int analysisCount = (int) analysisResultRepository.countBySessionId(sessionId);
        response.setAnalysisCount(analysisCount);

        log.info("Session detail fetched from DB: sessionId={}, analysisCount={}", sessionId, analysisCount);

        return response;
    }

    /**
     * 修复 B-004: 校验 sessionId 归属（供 Controller 在调用 @Cacheable 方法前使用）。
     * <p>数据隔离：sessionId 对应的 Session.userId 必须等于 currentUserId。
     * <p>@Cacheable 命中时 Service 方法体不执行，校验必须上移到 Controller 层。
     */
    public void validateSessionAccess(String userId, String sessionId) {
        Session session = sessionRepository.findBySessionId(sessionId)
                .orElseThrow(() -> new ResourceNotFoundException("Session", sessionId));
        if (!userId.equals(session.getUserId())) {
            throw new BusinessException(403, "无权限访问他人会话", "FORBIDDEN_ACCESS");
        }
    }

    @CacheEvict(value = "sessionState", key = "#sessionId")
    @Transactional
    public void updateStatus(String sessionId, SessionStatus newStatus) {
        Session session = sessionRepository.findBySessionId(sessionId)
                .orElseThrow(() -> new ResourceNotFoundException("Session", sessionId));

        validateDataIsolation(session.getUserId());

        SessionStatus fromStatus = session.getStatus();
        validateStatusTransition(session, newStatus);

        session.setStatus(newStatus);
        sessionRepository.save(session);

        log.info("Session status updated: sessionId={}, from={}, to={}",
                sessionId, fromStatus.getDbValue(), newStatus.getDbValue());
    }

    @CacheEvict(value = "sessionState", key = "#sessionId")
    @Transactional
    public SessionResponse markAsCompleted(String sessionId) {
        Session session = sessionRepository.findBySessionId(sessionId)
                .orElseThrow(() -> new ResourceNotFoundException("Session", sessionId));

        validateStatusTransition(session, SessionStatus.COMPLETED);

        session.setStatus(SessionStatus.COMPLETED);
        sessionRepository.save(session);

        log.info("Session marked as completed: sessionId={}", sessionId);

        return sessionMapper.toResponse(session);
    }

    @CacheEvict(value = "sessionState", key = "#sessionId")
    @Transactional
    public SessionResponse markAsExpired(String sessionId) {
        Session session = sessionRepository.findBySessionId(sessionId)
                .orElseThrow(() -> new ResourceNotFoundException("Session", sessionId));

        validateStatusTransition(session, SessionStatus.EXPIRED);

        session.setStatus(SessionStatus.EXPIRED);
        sessionRepository.save(session);

        log.info("Session marked as expired: sessionId={}", sessionId);

        return sessionMapper.toResponse(session);
    }

    @CacheEvict(value = "sessionState", key = "#sessionId")
    @Transactional
    public void deleteSession(String sessionId) {
        Session session = sessionRepository.findBySessionId(sessionId)
                .orElseThrow(() -> new ResourceNotFoundException("Session", sessionId));

        validateDataIsolation(session.getUserId());

        sessionRepository.delete(session);

        log.info("Session deleted (cascade analysis_results): sessionId={}", sessionId);
    }

    private void validateDataIsolation(String resourceUserId) {
        String currentUserId = getCurrentUserId();
        if (currentUserId == null) {
            throw new AuthenticationException("未认证，请先登录");
        }
        if (!currentUserId.equals(resourceUserId)) {
            throw new BusinessException(403, "无权限访问他人会话", "FORBIDDEN_ACCESS");
        }
    }

    private void validateStatusTransition(Session session, SessionStatus targetStatus) {
        SessionStatus currentStatus = session.getStatus();
        if (currentStatus == targetStatus) {
            throw new BusinessException(400,
                    "会话状态已是目标状态: " + targetStatus.getDbValue(),
                    "SAME_STATUS_NOOP");
        }
        Set<SessionStatus> allowed = ALLOWED_TRANSITIONS.getOrDefault(currentStatus, Set.of());
        if (!allowed.contains(targetStatus)) {
            throw new BusinessException(400,
                    "非法的状态转换: 从 " + currentStatus.getDbValue() + " 到 " + targetStatus.getDbValue(),
                    "INVALID_STATUS_TRANSITION");
        }
    }

    private boolean isTerminal(SessionStatus status) {
        return status == SessionStatus.COMPLETED || status == SessionStatus.EXPIRED;
    }

    private String getCurrentUserId() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication != null && authentication.getPrincipal() instanceof String principal) {
            return principal;
        }
        return null;
    }
}
