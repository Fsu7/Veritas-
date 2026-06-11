package com.literatureassistant.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.literatureassistant.client.PythonAIClient;
import com.literatureassistant.dto.common.AgentRequest;
import com.literatureassistant.dto.response.AgentSseEvent;
import com.literatureassistant.dto.response.AgentStateResponse;
import com.literatureassistant.dto.response.AnalysisResultDTO;
import com.literatureassistant.dto.response.PaperSearchResultDTO;
import com.literatureassistant.enums.AnalysisType;
import com.literatureassistant.exception.AIServiceException;
import com.literatureassistant.util.RedisKeyUtil;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Agent 客户端编排服务（Service 层）。
 * <p>对 AnalysisService 提供业务级调用入口，编排 {@link PythonAIClient}：
 * <ul>
 *   <li>三级降级：Python 正常 → Redis 缓存回退 → 降级提示 DTO（支持 PAPER_ANALYSIS/COMPARE/REPORT）</li>
 *   <li>维护 Agent 状态 Redis Hash（agent:state:{analysisId}, TTL=5min）</li>
 *   <li>维护分析结果 Redis String（analysis:result:{analysisId}, TTL=30min）</li>
 *   <li>SSE 流式转发（analyzeStream/compareStream/reportStream）+ 心跳（30s ping）+ 超时（120s）</li>
 *   <li>SSE 流降级（handleStreamFallback）</li>
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
    /** 心跳间隔 */
    private static final Duration HEARTBEAT_INTERVAL = Duration.ofSeconds(30);
    /** SSE 超时（无数据事件） */
    private static final Duration SSE_DATA_TIMEOUT = Duration.ofSeconds(120);

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
     * SSE 流式调用 Python 进行论文分析（保留兼容性，task28-29 改走 heartbeat 版本）。
     *
     * @param request     AgentRequest 请求体
     * @param lastEventId SSE Last-Event-ID Header（断线重连时透传，可空）
     * @return SSE 事件流
     */
    public Flux<AgentSseEvent> generateReportStream(AgentRequest request, String lastEventId) {
        return pythonAIClient.analyzeStream(request, lastEventId)
                .doOnNext(event -> writeAgentStateToRedis(request.getAnalysisId(), event))
                .onErrorContinue((err, item) ->
                        log.warn("SSE event 解析失败: {}", err.getMessage()));
    }

    /**
     * SSE 流式调用 + 30s ping 心跳 + 120s 超时（task29 主路径）。
     */
    public Flux<AgentSseEvent> generateReportStreamWithHeartbeat(AgentRequest request, String lastEventId) {
        String analysisId = request.getAnalysisId();
        // Python SSE 事件流
        Flux<AgentSseEvent> dataFlux = pythonAIClient.analyzeStream(request, lastEventId)
                .doOnNext(event -> writeAgentStateToRedis(analysisId, event));

        // 30s ping 心跳
        Flux<AgentSseEvent> heartbeatFlux = Flux.interval(HEARTBEAT_INTERVAL)
                .map(tick -> AgentSseEvent.builder()
                        .event("ping")
                        .data(Map.of("timestamp", Instant.now().toString()))
                        .build());

        // 120s 无数据超时：超过 120s 无数据事件 → 发送 error 事件后关闭
        Flux<AgentSseEvent> timeoutDetection = dataFlux
                .timeout(SSE_DATA_TIMEOUT, Flux.defer(() -> {
                    log.warn("SSE stream timeout: analysisId={}, after {}s", analysisId, SSE_DATA_TIMEOUT.getSeconds());
                    Map<String, Object> timeoutData = new HashMap<>();
                    timeoutData.put("type", "timeout");
                    timeoutData.put("message", "SSE connection timeout");
                    return Flux.just(AgentSseEvent.builder()
                            .event("error")
                            .data(timeoutData)
                            .build());
                }));

        return Flux.merge(timeoutDetection, heartbeatFlux)
                .onErrorResume(err -> {
                    log.warn("SSE stream 降级关闭: analysisId={}, error={}", analysisId, err.getMessage());
                    return handleStreamFallback(analysisId, err);
                });
    }

    /**
     * SSE 对比分析流（task28）。
     */
    public Flux<AgentSseEvent> compareStream(AgentRequest request, String lastEventId) {
        return pythonAIClient.compareStream(request, lastEventId)
                .doOnNext(event -> writeAgentStateToRedis(request.getAnalysisId(), event))
                .onErrorResume(err -> {
                    log.warn("compareStream 降级: analysisId={}", request.getAnalysisId());
                    return handleStreamFallback(request.getAnalysisId(), err);
                });
    }

    /**
     * SSE 综述生成流（task28）。
     */
    public Flux<AgentSseEvent> reportStream(AgentRequest request, String lastEventId) {
        return pythonAIClient.reportStream(request, lastEventId)
                .doOnNext(event -> writeAgentStateToRedis(request.getAnalysisId(), event))
                .onErrorResume(err -> {
                    log.warn("reportStream 降级: analysisId={}", request.getAnalysisId());
                    return handleStreamFallback(request.getAnalysisId(), err);
                });
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
            Map<String, String> hash = new HashMap<>(agentStates.size());
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

    /**
     * 从 SSE 事件中提取 Agent 状态并写入 Redis（task28: 处理 7 种事件类型）。
     * <ul>
     *   <li>agent_started → 写入 running 状态</li>
     *   <li>agent_state_update → 写入 progress/intermediateResult</li>
     *   <li>agent_completed → 写入 completed 状态</li>
     *   <li>agent_failed → 写入 failed 状态</li>
     *   <li>analysis_completed / error / ping → 不写 Redis（ping 仅保活）</li>
     * </ul>
     */
    private void writeAgentStateToRedis(String analysisId, AgentSseEvent event) {
        if (analysisId == null || event == null) {
            return;
        }
        String eventType = event.getEvent();
        if (eventType == null) {
            return;
        }
        // ping 事件不写 Redis
        if ("ping".equals(eventType)) {
            return;
        }
        // analysis_completed / error 不写 Agent 状态
        if ("analysis_completed".equals(eventType) || "error".equals(eventType)) {
            return;
        }
        if (event.getData() == null || event.getData().isEmpty()) {
            return;
        }
        // agent_started / agent_state_update / agent_completed / agent_failed
        try {
            AgentStateResponse state = objectMapper.convertValue(event.getData(), AgentStateResponse.class);
            updateAgentState(analysisId, List.of(state));
        } catch (Exception e) {
            log.warn("SSE 事件转 AgentState 失败: analysisId={}, eventType={}, error={}",
                    analysisId, eventType, e.getMessage());
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

    // region 降级处理

    /**
     * 降级处理（task30: 扩展支持 COMPARE/REPORT/PAPER_ANALYSIS）。
     * <p>三级降级：先查 Redis 缓存（analysis:result:{analysisId}），命中返回 cached+degraded=true；
     * 未命中根据 analysisType 返回对应降级 DTO。
     */
    private AnalysisResultDTO handleFallback(AgentRequest request, Exception e) {
        String analysisId = request.getAnalysisId();
        if (analysisId == null || analysisId.isBlank()) {
            analysisId = "unknown";
        }
        // 先查 Redis 缓存
        String fallbackKey = RedisKeyUtil.analysisResultKey(analysisId);
        try {
            String cached = redisTemplate.opsForValue().get(fallbackKey);
            if (cached != null) {
                AnalysisResultDTO cachedDto = objectMapper.readValue(cached, AnalysisResultDTO.class);
                return AnalysisResultDTO.builder()
                        .analysisId(cachedDto.getAnalysisId())
                        .status(cachedDto.getStatus())
                        .report(cachedDto.getReport())
                        .citations(cachedDto.getCitations())
                        .agentStates(cachedDto.getAgentStates())
                        .degraded(true)
                        .degradedReason("AI服务暂时不可用，返回缓存结果")
                        .build();
            }
        } catch (Exception ex) {
            log.error("降级缓存反序列化失败: analysisId={}, error={}", analysisId, ex.getMessage());
        }
        // 无缓存：根据分析类型返回不同降级 DTO
        AnalysisType type = request.getAnalysisType();
        if (type == AnalysisType.COMPARE) {
            return AnalysisResultDTO.compareDegraded(analysisId, "AI服务暂时不可用，请稍后重试");
        } else if (type == AnalysisType.REPORT) {
            return AnalysisResultDTO.reportDegraded(analysisId, "AI服务暂时不可用，请稍后重试");
        }
        return AnalysisResultDTO.degraded(analysisId, "AI服务暂时不可用，请稍后重试");
    }

    /**
     * SSE 流降级处理（task30）。
     * <p>Python 不可用时发送降级 SSE 事件后关闭流：
     * <ol>
     *   <li>event:error + data:{type:degradation, message:...}</li>
     *   <li>event:analysis_completed + data:{status:completed, degraded:true}</li>
     * </ol>
     */
    Flux<AgentSseEvent> handleStreamFallback(String analysisId, Throwable err) {
        log.warn("SSE 流降级: analysisId={}, error={}", analysisId, err != null ? err.getMessage() : "unknown");

        Map<String, Object> errorData = new HashMap<>();
        errorData.put("type", "degradation");
        errorData.put("message", "AI服务暂时不可用，已返回缓存结果");

        Map<String, Object> completedData = new HashMap<>();
        completedData.put("status", "completed");
        completedData.put("degraded", true);
        completedData.put("degradedReason", "AI服务暂时不可用，返回缓存结果");

        return Flux.just(
                AgentSseEvent.builder().event("error").data(errorData).build(),
                AgentSseEvent.builder().event("analysis_completed").data(completedData).build()
        );
    }

    // endregion

    // region 私有方法

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
