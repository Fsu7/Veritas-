package com.literatureassistant.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.literatureassistant.client.PythonAIClient;
import com.literatureassistant.dto.common.AgentRequest;
import com.literatureassistant.dto.response.AgentStateResponse;
import com.literatureassistant.dto.response.AnalysisResultDTO;
import com.literatureassistant.dto.response.PaperSearchResultDTO;
import com.literatureassistant.exception.AIServiceException;
import com.literatureassistant.util.RedisKeyUtil;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;
import reactor.core.scheduler.Schedulers;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Agent 客户端编排服务（Service 层）。
 * <p>对 AnalysisService 提供业务级调用入口，编排 {@link PythonAIClient}：
 * <ul>
 *   <li>三级降级：Python 正常 → Redis 缓存回退 → 降级提示 DTO</li>
 *   <li>维护 Agent 状态 Redis Hash（agent:state:{analysisId}, TTL=5min）</li>
 *   <li>维护分析结果 Redis String（analysis:result:{analysisId}, TTL=30min）</li>
 *   <li>异步 Mono 占位（generateReport）供 JM4 SSE 扩展</li>
 * </ul>
 *
 * @author XH-202630 Literature Assistant
 * @since 0.3
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class AgentClientService {

    /** Agent 状态 Redis Hash 过期时间 */
    private static final Duration AGENT_STATE_TTL = Duration.ofMinutes(5);
    /** 分析结果 Redis String 过期时间 */
    private static final Duration ANALYSIS_RESULT_TTL = Duration.ofMinutes(30);

    private final PythonAIClient pythonAIClient;
    private final RedisTemplate<String, String> redisTemplate;
    private final ObjectMapper objectMapper;

    // region 业务编排入口

    /**
     * 同步调用 Python 进行论文分析。
     * <p>三级降级：Python 正常 → 写 Redis → 返回原 DTO；Python 异常 → handleFallback 降级处理。
     */
    public AnalysisResultDTO analyzePaper(AgentRequest request) {
        String analysisId = request.getAnalysisId();
        try {
            AnalysisResultDTO result = pythonAIClient.analyze(request);
            // 成功后写 Redis：Agent 状态 Hash + 分析结果 String
            updateAgentState(analysisId, result.getAgentStates());
            cacheAnalysisResult(analysisId, result);
            return result;
        } catch (AIServiceException e) {
            log.warn("AI服务调用失败，进入降级: analysisId={}, error={}", analysisId, e.getMessage());
            return handleFallback(request, e);
        }
    }

    /**
     * 异步预留接口（JM4 SSE 扩展用）。
     * <p>当前实现为 Mono 占位，包装同步方法。
     */
    public Mono<AnalysisResultDTO> generateReport(AgentRequest request) {
        return Mono.fromCallable(() -> analyzePaper(request))
                .subscribeOn(Schedulers.boundedElastic());
    }

    /**
     * 语义搜索（直接委托 pythonAIClient.search）。
     */
    public List<PaperSearchResultDTO> search(String query, int topK, Map<String, Object> filters) {
        return pythonAIClient.search(query, topK, filters);
    }

    // endregion

    // region Agent 状态维护

    /**
     * 把 Agent 状态写入 Redis Hash。
     * <p>key = agent:state:{analysisId}；field = agentName；value = JSON(AgentStateResponse)；TTL=5min。
     */
    public void updateAgentState(String analysisId, List<AgentStateResponse> agentStates) {
        if (analysisId == null || analysisId.isBlank() || agentStates == null || agentStates.isEmpty()) {
            return;
        }
        String key = RedisKeyUtil.agentStateKey(analysisId);
        try {
            Map<String, String> hash = new java.util.HashMap<>(agentStates.size());
            for (AgentStateResponse state : agentStates) {
                if (state == null || state.getAgentName() == null) continue;
                try {
                    hash.put(state.getAgentName(), objectMapper.writeValueAsString(state));
                } catch (Exception e) {
                    log.warn("AgentState序列化失败: agentName={}, error={}", state.getAgentName(), e.getMessage());
                }
            }
            if (!hash.isEmpty()) {
                redisTemplate.opsForHash().putAll(key, hash);
                redisTemplate.expire(key, AGENT_STATE_TTL);
            }
        } catch (Exception e) {
            log.warn("Agent状态写入Redis失败: analysisId={}, error={}", analysisId, e.getMessage());
        }
    }

    /**
     * 从 Redis Hash 读取 Agent 状态。
     * <p>Redis 不存在或为空时返回 new ArrayList<>()（禁止 null）。
     */
    public List<AgentStateResponse> getAgentStates(String analysisId) {
        if (analysisId == null || analysisId.isBlank()) {
            return new ArrayList<>();
        }
        String key = RedisKeyUtil.agentStateKey(analysisId);
        try {
            Map<Object, Object> entries = redisTemplate.opsForHash().entries(key);
            if (entries == null || entries.isEmpty()) {
                return new ArrayList<>();
            }
            List<AgentStateResponse> result = new ArrayList<>(entries.size());
            for (Object value : entries.values()) {
                if (value == null) continue;
                try {
                    result.add(objectMapper.readValue(value.toString(), AgentStateResponse.class));
                } catch (Exception e) {
                    log.warn("AgentState反序列化失败: value={}, error={}", value, e.getMessage());
                }
            }
            return result;
        } catch (Exception e) {
            log.warn("Agent状态读取Redis失败: analysisId={}, error={}", analysisId, e.getMessage());
            return new ArrayList<>();
        }
    }

    // endregion

    // region 健康探测

    /**
     * AI 服务健康探测（委托 pythonAIClient.isHealthy），供 HealthController 集成用。
     */
    public boolean isHealthy() {
        return pythonAIClient.isHealthy();
    }

    // endregion

    // region 私有方法

    /**
     * 降级处理：先查 Redis 缓存（agent:fallback:{analysisId}），命中返回 cached+degraded=true；未命中返回 degraded DTO。
     */
    private AnalysisResultDTO handleFallback(AgentRequest request, Exception e) {
        String analysisId = request.getAnalysisId();
        if (analysisId == null || analysisId.isBlank()) {
            analysisId = "unknown";
        }
        String fallbackKey = RedisKeyUtil.agentFallbackKey(analysisId);
        try {
            String cached = redisTemplate.opsForValue().get(fallbackKey);
            if (cached != null) {
                AnalysisResultDTO cachedDto = objectMapper.readValue(cached, AnalysisResultDTO.class);
                cachedDto.setDegraded(true);
                cachedDto.setDegradedReason("AI服务暂时不可用，返回缓存结果");
                return cachedDto;
            }
        } catch (Exception ex) {
            log.error("降级缓存反序列化失败: analysisId={}, error={}", analysisId, ex.getMessage());
        }
        return AnalysisResultDTO.degraded(analysisId, "AI服务暂时不可用，请稍后重试");
    }

    /**
     * 把分析结果写入 Redis 缓存（analysis:result:{analysisId}, TTL=30min）。
     */
    private void cacheAnalysisResult(String analysisId, AnalysisResultDTO dto) {
        if (analysisId == null || analysisId.isBlank() || dto == null) {
            return;
        }
        String key = RedisKeyUtil.analysisResultKey(analysisId);
        try {
            String json = objectMapper.writeValueAsString(dto);
            redisTemplate.opsForValue().set(key, json, ANALYSIS_RESULT_TTL);
        } catch (Exception e) {
            log.warn("分析结果缓存失败: analysisId={}, error={}", analysisId, e.getMessage());
        }
    }

    // endregion
}
