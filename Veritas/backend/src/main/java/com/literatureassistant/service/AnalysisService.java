package com.literatureassistant.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.literatureassistant.dto.common.AgentRequest;
import com.literatureassistant.dto.common.UserProfileDTO;
import com.literatureassistant.dto.request.PaperAnalysisRequest;
import com.literatureassistant.dto.request.SessionCreateRequest;
import com.literatureassistant.dto.response.AgentStateResponse;
import com.literatureassistant.dto.response.AnalysisResponse;
import com.literatureassistant.dto.response.AnalysisResultDTO;
import com.literatureassistant.dto.response.AnalysisStatusResponse;
import com.literatureassistant.dto.response.AnalysisTaskResponse;
import com.literatureassistant.dto.response.PaperDetailResponse;
import com.literatureassistant.dto.response.ProfileResponse;
import com.literatureassistant.dto.response.SessionResponse;
import com.literatureassistant.entity.AnalysisResult;
import com.literatureassistant.entity.Session;
import com.literatureassistant.enums.AnalysisStatus;
import com.literatureassistant.enums.AnalysisType;
import com.literatureassistant.enums.EducationLevel;
import com.literatureassistant.enums.KnowledgeLevel;
import com.literatureassistant.enums.PreferredStyle;
import com.literatureassistant.enums.SessionStatus;
import com.literatureassistant.exception.BusinessException;
import com.literatureassistant.exception.ResourceNotFoundException;
import com.literatureassistant.repository.AnalysisResultRepository;
import com.literatureassistant.repository.SessionRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.context.annotation.Lazy;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/**
 * 分析服务编排层。
 * <p>完整编排论文分析任务：用户画像 → 论文校验 → Session 复用/创建 → AnalysisResult 状态机 →
 * {@link AgentClientService} → 更新 AnalysisResult + 缓存。
 * <p>事务边界：@Transactional 仅覆盖 DB 写入（savePending / completeAnalysis）；
 * AI 调用（agentClientService.analyzePaper）显式无 @Transactional，避免 30s 长事务。
 *
 * @author XH-202630 Literature Assistant
 * @since 0.3
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class AnalysisService {

    private final UserService userService;
    private final PaperService paperService;
    private final SessionService sessionService;
    private final AgentClientService agentClientService;
    private final AnalysisResultRepository analysisResultRepository;
    private final SessionRepository sessionRepository;
    private final ObjectMapper objectMapper;

    /**
     * 自注入（用于 @Transactional 方法间相互调用通过 Spring 代理生效）
     */
    @Autowired
    @Lazy
    private AnalysisService self;

    /**
     * 论文分析入口（POST /api/analysis/paper）。
     * <p>7 步编排：1) 画像 → 2) 论文校验 → 3) Session 复用/创建 → 4) 生成 analysisId →
     * 5) 存 AnalysisResult(PENDING) → 6) 调 AgentClientService → 7) 更新 AnalysisResult 状态。
     */
    public AnalysisTaskResponse analyzePaper(String userId, PaperAnalysisRequest request) {
        log.info("analyzePaper start: userId={}, paperId={}, topic={}",
                userId, request.getPaperId(), truncate(request.getTopic(), 50));

        // 1) 用户画像（不抛错，缺失时用默认）
        UserProfileDTO userProfile = buildUserProfile(userId);

        // 2) 论文详情（不存在抛 404）
        PaperDetailResponse paper = paperService.getPaperDetail(request.getPaperId());
        log.debug("paper validated: paperId={}, title={}", paper.getPaperId(), paper.getTitle());

        // 3) Session 复用/创建
        String sessionId = resolveOrCreateSession(userId, request);

        // 4) 生成 analysisId
        String analysisId = "anl_" + UUID.randomUUID().toString().replace("-", "").substring(0, 12);

        // 5) 保存 AnalysisResult(PENDING) — 短事务
        AnalysisResult pending = self.savePending(analysisId, sessionId, AnalysisType.PAPER_ANALYSIS);

        // 6) 调 AgentClientService.analyzePaper（事务外，长耗时）
        AgentRequest agentRequest = AgentRequest.builder()
                .topic(request.getTopic())
                .paperIds(List.of(request.getPaperId()))
                .userId(userId)
                .userProfile(userProfile)
                .analysisType(AnalysisType.PAPER_ANALYSIS)
                .analysisId(analysisId)
                .build();
        AnalysisResultDTO result = agentClientService.analyzePaper(agentRequest);

        // 7) 更新 AnalysisResult 状态 + result JSON — 短事务
        return self.completeAnalysis(pending.getId(), result);
    }

    // region 查询方法（task23）

    /**
     * 查询分析结果（GET /api/analysis/{analysisId}）。
     * <p>走 @Cacheable Redis 缓存（30min TTL），命中直接返回；未命中查 DB + 反序列化 result JSON + 回填缓存。
     * <p>数据隔离：校验 AnalysisResult.sessionId 对应的 Session.userId == currentUserId。
     */
    @Cacheable(value = "analysisResult", key = "#analysisId", unless = "#result == null")
    public AnalysisResponse getAnalysisResult(String userId, String analysisId) {
        AnalysisResult entity = analysisResultRepository.findByAnalysisId(analysisId)
                .orElseThrow(() -> new ResourceNotFoundException("AnalysisResult", analysisId));
        // 数据隔离
        validateDataIsolation(userId, entity.getSessionId());
        // 反序列化 result JSON
        AnalysisResultDTO resultDto = deserializeResult(entity.getResult());
        return AnalysisResponse.builder()
                .analysisId(entity.getAnalysisId())
                .sessionId(entity.getSessionId())
                .status(entity.getStatus())
                .type(entity.getType())
                .result(resultDto)
                .createdAt(entity.getCreatedAt())
                .build();
    }

    /**
     * 查询分析状态（GET /api/analysis/{analysisId}/status）。
     * <p>聚合 AnalysisResult.status + Redis Agent 实时状态（不缓存，保证 SSE 一致性）。
     * <p>progress = agentStates 中各 progress 算术平均；currentAgent = 首个非 completed 的 agent。
     */
    public AnalysisStatusResponse getAnalysisStatus(String userId, String analysisId) {
        AnalysisResult entity = analysisResultRepository.findByAnalysisId(analysisId)
                .orElseThrow(() -> new ResourceNotFoundException("AnalysisResult", analysisId));
        // 数据隔离
        validateDataIsolation(userId, entity.getSessionId());
        // 从 Redis 读实时 Agent 状态
        List<AgentStateResponse> agentStates = agentClientService.getAgentStates(analysisId);
        // 计算 progress
        Double progress = calcProgress(agentStates);
        // 计算 currentAgent
        String currentAgent = findCurrentAgent(agentStates);
        return AnalysisStatusResponse.builder()
                .analysisId(entity.getAnalysisId())
                .status(entity.getStatus())
                .progress(progress)
                .currentAgent(currentAgent)
                .agentStates(agentStates)
                .build();
    }

    // endregion

    /**
     * 保存 AnalysisResult(PENDING) 记录 — 短事务。
     * <p>暴露为 public 通过 self 调用以使 Spring 事务代理生效。
     */
    @Transactional
    public AnalysisResult savePending(String analysisId, String sessionId, AnalysisType type) {
        AnalysisResult entity = AnalysisResult.builder()
                .analysisId(analysisId)
                .sessionId(sessionId)
                .type(type)
                .status(AnalysisStatus.PENDING)
                .result("{}")
                .build();
        return analysisResultRepository.save(entity);
    }

    /**
     * 更新 AnalysisResult 状态 + 持久化 result JSON — 短事务。
     */
    @Transactional
    public AnalysisTaskResponse completeAnalysis(Long id, AnalysisResultDTO result) {
        AnalysisResult entity = analysisResultRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("AnalysisResult", String.valueOf(id)));
        AnalysisStatus newStatus = (result != null && Boolean.TRUE.equals(result.getDegraded()))
                ? AnalysisStatus.COMPLETED
                : mapStatus(result);
        entity.setStatus(newStatus);
        entity.setResult(serializeResult(result));
        AnalysisResult saved = analysisResultRepository.save(entity);

        String message = buildMessage(result);
        return AnalysisTaskResponse.builder()
                .analysisId(saved.getAnalysisId())
                .status(saved.getStatus())
                .message(message)
                .createdAt(saved.getCreatedAt() != null ? saved.getCreatedAt() : LocalDateTime.now())
                .build();
    }

    // region 私有方法（无事务）

    private UserProfileDTO buildUserProfile(String userId) {
        try {
            ProfileResponse profile = userService.getProfile(userId);
            EducationLevel edu = EducationLevel.fromDbValue(profile.getEducationLevel());
            KnowledgeLevel kl = KnowledgeLevel.fromDbValue(profile.getKnowledgeLevel());
            PreferredStyle ps = PreferredStyle.fromDbValue(profile.getPreferredStyle());
            return UserProfileDTO.builder()
                    .educationLevel(edu != null ? edu : EducationLevel.MASTER)
                    .researchField(profile.getResearchField())
                    .knowledgeLevel(kl != null ? kl : KnowledgeLevel.INTERMEDIATE)
                    .preferredStyle(ps != null ? ps : PreferredStyle.BALANCED)
                    .build();
        } catch (ResourceNotFoundException e) {
            log.info("用户画像缺失，使用默认画像: userId={}", userId);
            return UserProfileDTO.builder()
                    .educationLevel(EducationLevel.MASTER)
                    .researchField("")
                    .knowledgeLevel(KnowledgeLevel.INTERMEDIATE)
                    .preferredStyle(PreferredStyle.BALANCED)
                    .build();
        }
    }

    private String resolveOrCreateSession(String userId, PaperAnalysisRequest request) {
        if (request.getSessionId() != null && !request.getSessionId().isBlank()) {
            Session session = sessionRepository.findBySessionId(request.getSessionId())
                    .orElseThrow(() -> new ResourceNotFoundException("Session", request.getSessionId()));
            if (!userId.equals(session.getUserId())) {
                throw new BusinessException(403, "无权限访问他人会话", "FORBIDDEN_ACCESS");
            }
            if (session.getStatus() != SessionStatus.ACTIVE) {
                throw new BusinessException(400, "会话状态非ACTIVE: " + session.getStatus().getDbValue(),
                        "INVALID_SESSION_STATUS");
            }
            return session.getSessionId();
        }
        SessionCreateRequest newSession = SessionCreateRequest.builder().topic(request.getTopic()).build();
        SessionResponse created = sessionService.createSession(userId, newSession);
        return created.getSessionId();
    }

    private AnalysisStatus mapStatus(AnalysisResultDTO result) {
        if (result == null || result.getStatus() == null) {
            return AnalysisStatus.FAILED;
        }
        return switch (result.getStatus()) {
            case COMPLETED -> AnalysisStatus.COMPLETED;
            case PROCESSING -> AnalysisStatus.PROCESSING;
            case FAILED -> AnalysisStatus.FAILED;
            default -> result.getStatus();
        };
    }

    private String serializeResult(AnalysisResultDTO result) {
        try {
            return objectMapper.writeValueAsString(result);
        } catch (JsonProcessingException e) {
            log.warn("result 序列化失败: {}", e.getMessage());
            return "{}";
        }
    }

    private String buildMessage(AnalysisResultDTO result) {
        if (result == null) {
            return "分析失败：响应为空";
        }
        if (Boolean.TRUE.equals(result.getDegraded())) {
            return "分析完成（降级）：" + result.getDegradedReason();
        }
        return switch (result.getStatus()) {
            case COMPLETED -> "分析完成";
            case PROCESSING -> "分析进行中";
            case FAILED -> "分析失败：" + (result.getDegradedReason() != null ? result.getDegradedReason() : "未知错误");
            default -> "分析状态：" + result.getStatus();
        };
    }

    private String truncate(String s, int max) {
        if (s == null) return "";
        return s.length() <= max ? s : s.substring(0, max) + "...";
    }

    /**
     * 反序列化 result JSON 字符串 → AnalysisResultDTO。
     */
    private AnalysisResultDTO deserializeResult(String resultJson) {
        if (resultJson == null || resultJson.isBlank() || "{}".equals(resultJson)) {
            return null;
        }
        try {
            return objectMapper.readValue(resultJson, AnalysisResultDTO.class);
        } catch (JsonProcessingException e) {
            log.warn("result JSON 反序列化失败: {}", e.getMessage());
            return null;
        }
    }

    /**
     * 公开数据隔离校验：analysisId 对应的 Session.userId 必须等于 currentUserId。
     * <p>JM4 SSE 端点 (GET /api/analysis/{analysisId}/agent-stream) 入口使用，
     * 防止用户 A 订阅用户 B 的 analysisId。
     *
     * @throws ResourceNotFoundException analysisId 不存在
     * @throws BusinessException         越权访问
     */
    public void validateAnalysisAccess(String userId, String analysisId) {
        AnalysisResult entity = analysisResultRepository.findByAnalysisId(analysisId)
                .orElseThrow(() -> new ResourceNotFoundException("AnalysisResult", analysisId));
        validateDataIsolation(userId, entity.getSessionId());
    }

    /**
     * 数据隔离校验：sessionId 对应的 Session.userId 必须等于 currentUserId。
     */
    private void validateDataIsolation(String userId, String sessionId) {
        Session session = sessionRepository.findBySessionId(sessionId)
                .orElseThrow(() -> new ResourceNotFoundException("Session", sessionId));
        if (!userId.equals(session.getUserId())) {
            throw new BusinessException(403, "无权限访问他人分析结果", "FORBIDDEN_ACCESS");
        }
    }

    /**
     * 计算整体进度：agentStates 非空时取各 Agent progress 算术平均；空时返回 null。
     */
    private Double calcProgress(List<AgentStateResponse> agentStates) {
        if (agentStates == null || agentStates.isEmpty()) {
            return null;
        }
        double sum = 0;
        int count = 0;
        for (AgentStateResponse s : agentStates) {
            if (s != null && s.getProgress() != null) {
                sum += s.getProgress();
                count++;
            }
        }
        return count > 0 ? sum / count : null;
    }

    /**
     * 查找当前执行中的 Agent：首个 status != null 且 != "completed" 的 agent；全部 completed 时返回 null。
     */
    private String findCurrentAgent(List<AgentStateResponse> agentStates) {
        if (agentStates == null || agentStates.isEmpty()) {
            return null;
        }
        for (AgentStateResponse s : agentStates) {
            if (s != null && s.getStatus() != null
                    && !"completed".equalsIgnoreCase(s.getStatus())) {
                return s.getAgentName();
            }
        }
        return null;
    }

    // endregion
}
