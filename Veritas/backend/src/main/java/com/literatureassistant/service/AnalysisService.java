package com.literatureassistant.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.literatureassistant.dto.common.AgentRequest;
import com.literatureassistant.dto.common.UserProfileDTO;
import com.literatureassistant.dto.request.CompareRequest;
import com.literatureassistant.dto.request.PaperAnalysisRequest;
import com.literatureassistant.dto.request.ReportRequest;
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
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/**
 * 分析服务编排层。
 * <p>完整编排 3 种分析任务：论文分析（{@code PAPER_ANALYSIS}）/对比分析（{@code COMPARE}）/综述生成（{@code REPORT}）。
 * 7 步编排：1) 画像 → 2) 论文校验 → 3) Session 复用/创建 → 4) 生成 analysisId →
 * 5) 存 AnalysisResult(PENDING) → 6) 调 AgentClientService → 7) 更新 AnalysisResult 状态。
 * <p>事务边界：@Transactional 仅覆盖 DB 写入（{@link AnalysisTransactionService#savePending} / {@link AnalysisTransactionService#completeAnalysis}）；
 * AI 调用（agentClientService.analyzePaper）显式无 @Transactional，避免 30s 长事务。
 * <p>重构历史：task24 消除 {@code @Autowired @Lazy self} 自注入反模式，事务方法迁移到 {@link AnalysisTransactionService}。
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
    private final AnalysisTransactionService analysisTransactionService;
    private final AnalysisResultRepository analysisResultRepository;
    private final SessionRepository sessionRepository;
    private final ObjectMapper objectMapper;

    /**
     * 论文分析入口（POST /api/analysis/paper）。
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
        String sessionId = resolveOrCreateSession(userId, request.getSessionId(), request.getTopic());

        // 4) 生成 analysisId
        String analysisId = generateAnalysisId();

        // 5) 保存 AnalysisResult(PENDING) — 短事务
        AnalysisResult pending = analysisTransactionService.savePending(analysisId, sessionId, AnalysisType.PAPER_ANALYSIS);

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
        return analysisTransactionService.completeAnalysis(pending.getId(), result);
    }

    /**
     * 对比分析入口（POST /api/analysis/compare，task25）。
     * <p>8 步编排：buildUserProfile → 验证所有 paperIds 存在 → resolveOrCreateSession
     * → savePending(COMPARE) → buildAgentRequest(paperIds 列表) → callAI → completeAnalysis
     */
    public AnalysisTaskResponse comparePapers(String userId, CompareRequest request) {
        log.info("comparePapers start: userId={}, paperCount={}, topic={}",
                userId, request.getPaperIds().size(), truncate(request.getTopic(), 50));

        // 1) 用户画像
        UserProfileDTO userProfile = buildUserProfile(userId);

        // 2) 验证所有 paperIds 存在
        for (String paperId : request.getPaperIds()) {
            PaperDetailResponse paper = paperService.getPaperDetail(paperId);
            log.debug("compare paper validated: paperId={}, title={}", paper.getPaperId(), paper.getTitle());
        }

        // 3) Session 复用/创建
        String sessionId = resolveOrCreateSession(userId, request.getSessionId(), request.getTopic());

        // 4) 生成 analysisId
        String analysisId = generateAnalysisId();

        // 5) 保存 PENDING
        AnalysisResult pending = analysisTransactionService.savePending(analysisId, sessionId, AnalysisType.COMPARE);

        // 6) 调 AI 服务
        AgentRequest agentRequest = AgentRequest.builder()
                .topic(request.getTopic())
                .paperIds(new ArrayList<>(request.getPaperIds()))
                .userId(userId)
                .userProfile(userProfile)
                .analysisType(AnalysisType.COMPARE)
                .analysisId(analysisId)
                .build();
        AnalysisResultDTO result = agentClientService.analyzePaper(agentRequest);

        // 7) 完成分析
        return analysisTransactionService.completeAnalysis(pending.getId(), result);
    }

    /**
     * 综述生成入口（POST /api/analysis/report，task26）。
     * <p>7 步编排：buildUserProfile → 验证所有 paperIds 存在 → resolveOrCreateSession
     * → savePending(REPORT) → buildAgentRequest(paperIds 列表) → callAI → completeAnalysis
     */
    public AnalysisTaskResponse generateReport(String userId, ReportRequest request) {
        log.info("generateReport start: userId={}, paperCount={}, topic={}",
                userId, request.getPaperIds().size(), truncate(request.getTopic(), 50));

        // 1) 用户画像
        UserProfileDTO userProfile = buildUserProfile(userId);

        // 2) 验证所有 paperIds 存在
        for (String paperId : request.getPaperIds()) {
            PaperDetailResponse paper = paperService.getPaperDetail(paperId);
            log.debug("report paper validated: paperId={}, title={}", paper.getPaperId(), paper.getTitle());
        }

        // 3) Session 复用/创建
        String sessionId = resolveOrCreateSession(userId, request.getSessionId(), request.getTopic());

        // 4) 生成 analysisId
        String analysisId = generateAnalysisId();

        // 5) 保存 PENDING
        AnalysisResult pending = analysisTransactionService.savePending(analysisId, sessionId, AnalysisType.REPORT);

        // 6) 调 AI 服务
        AgentRequest agentRequest = AgentRequest.builder()
                .topic(request.getTopic())
                .paperIds(new ArrayList<>(request.getPaperIds()))
                .userId(userId)
                .userProfile(userProfile)
                .analysisType(AnalysisType.REPORT)
                .analysisId(analysisId)
                .build();
        AnalysisResultDTO result = agentClientService.analyzePaper(agentRequest);

        // 7) 完成分析
        if (result != null && result.getCitations() == null) {
            log.warn("综述报告引用列表为空: analysisId={}", analysisId);
        } else if (result != null) {
            log.info("综述报告完成: analysisId={}, citations={}", analysisId, result.getCitations().size());
        }
        return analysisTransactionService.completeAnalysis(pending.getId(), result);
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

    // region 私有方法（无事务）

    private String generateAnalysisId() {
        return "anl_" + UUID.randomUUID().toString().replace("-", "").substring(0, 12);
    }

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

    /**
     * 解析或创建 Session：抽出公共逻辑供 analyzePaper/comparePapers/generateReport 复用。
     * @param sessionId 可空；非空时复用并校验归属 + ACTIVE 状态
     * @param topic 新建 Session 时使用
     */
    private String resolveOrCreateSession(String userId, String sessionId, String topic) {
        if (sessionId != null && !sessionId.isBlank()) {
            Session session = sessionRepository.findBySessionId(sessionId)
                    .orElseThrow(() -> new ResourceNotFoundException("Session", sessionId));
            if (!userId.equals(session.getUserId())) {
                throw new BusinessException(403, "无权限访问他人会话", "FORBIDDEN_ACCESS");
            }
            if (session.getStatus() != SessionStatus.ACTIVE) {
                throw new BusinessException(400, "会话状态非ACTIVE: " + session.getStatus().getDbValue(),
                        "INVALID_SESSION_STATUS");
            }
            return session.getSessionId();
        }
        SessionCreateRequest newSession = SessionCreateRequest.builder().topic(topic).build();
        SessionResponse created = sessionService.createSession(userId, newSession);
        return created.getSessionId();
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
