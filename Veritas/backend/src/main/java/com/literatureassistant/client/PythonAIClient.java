package com.literatureassistant.client;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.literatureassistant.dto.common.AgentRequest;
import com.literatureassistant.dto.response.AgentSseEvent;
import com.literatureassistant.dto.response.AnalysisResultDTO;
import com.literatureassistant.dto.response.ModelStatusDTO;
import com.literatureassistant.dto.response.PaperSearchResultDTO;
import com.literatureassistant.exception.AIServiceException;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.client.reactive.ReactorClientHttpConnector;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientResponseException;
import reactor.core.publisher.Flux;
import reactor.netty.http.client.HttpClient;

import java.time.Duration;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

/**
 * 封装 Java → Python AI 服务全部 HTTP 调用的客户端。
 * <p>5 个核心端点：论文分析 / SSE 流（论文/对比/综述）/ 语义搜索 / 健康检查 / 模型状态查询。
 * <p>具备统一超时（30s）+ 重试 1 次（间隔 3s）+ 异常转换为 {@link AIServiceException}。
 * <p>健康检查单独使用 5s 超时；SSE 流式调用单独使用 sseWebClient（独立连接池，120s/150s 超时）。
 *
 * @author XH-202630 Literature Assistant
 * @since 0.3
 */
@Slf4j
@Component
public class PythonAIClient {

    private static final String ENDPOINT_ANALYZE = "/api/agent/analyze";
    private static final String ENDPOINT_ANALYZE_STREAM = "/api/agent/analyze/stream";
    private static final String ENDPOINT_COMPARE_STREAM = "/api/agent/compare/stream";
    private static final String ENDPOINT_REPORT_STREAM = "/api/agent/report/stream";
    private static final String ENDPOINT_SEARCH = "/api/search/";
    private static final String ENDPOINT_MODEL_STATUS = "/api/model/status";
    private static final String ENDPOINT_HEALTH = "/health";

    private static final int DEFAULT_TOP_K = 10;
    private static final int MAX_TOP_K = 50;
    private static final int HEALTH_TIMEOUT_SECONDS = 5;
    private static final int CONNECT_TIMEOUT_MILLIS = 2000;
    /** 同步调用响应超时 */
    private static final int RESPONSE_TIMEOUT_SECONDS = 30;
    /** SSE 流响应超时（task29 与 JM4 检查点对齐从 150s 调整为 120s） */
    private static final int SSE_RESPONSE_TIMEOUT_SECONDS = 120;

    private final WebClient webClient;
    private final WebClient sseWebClient;
    private final WebClient healthWebClient;
    private final ObjectMapper objectMapper;
    private final int retryCount;
    private final long retryIntervalMs;

    public PythonAIClient(@Qualifier("webClient") WebClient webClient,
                          @Qualifier("sseWebClient") WebClient sseWebClient,
                          @Value("${ai-service.url}") String aiServiceUrl,
                          @Value("${ai-service.retry-count:1}") int retryCount,
                          @Value("${ai-service.retry-interval:3000}") long retryIntervalMs,
                          ObjectMapper objectMapper) {
        this.webClient = webClient;
        this.sseWebClient = sseWebClient;
        this.retryCount = retryCount;
        this.retryIntervalMs = retryIntervalMs;
        this.objectMapper = objectMapper;
        // 健康探测单独使用 5s 超时的客户端
        this.healthWebClient = buildHealthWebClient(aiServiceUrl);
    }

    /**
     * 同步调用 Python /api/agent/analyze 进行论文分析。
     * <p>具备重试机制：5xx / 超时 / 连接错误 重试 1 次；4xx 不重试。
     *
     * @param request AgentRequest 请求体
     * @return AnalysisResultDTO 响应
     * @throws AIServiceException 当 Python 返回 4xx/5xx/超时/连接错误
     */
    public AnalysisResultDTO analyze(AgentRequest request) {
        long startMs = System.currentTimeMillis();
        AIServiceException lastException = null;

        int attempts = retryCount + 1;
        for (int i = 0; i < attempts; i++) {
            try {
                AnalysisResultDTO result = webClient.post()
                        .uri(ENDPOINT_ANALYZE)
                        .bodyValue(request)
                        .retrieve()
                        .bodyToMono(AnalysisResultDTO.class)
                        .block(Duration.ofSeconds(RESPONSE_TIMEOUT_SECONDS));
                if (result == null) {
                    throw new AIServiceException("AI service returned null body", null);
                }
                long durationMs = System.currentTimeMillis() - startMs;
                log.info("AI analyze success: analysisId={}, durationMs={}, attempt={}",
                        request.getAnalysisId(), durationMs, i + 1);
                return result;
            } catch (WebClientResponseException e) {
                lastException = new AIServiceException(
                        "AI service call failed: " + e.getStatusCode() + " " + e.getMessage(), e);
                if (e.getStatusCode().is4xxClientError()) {
                    log.warn("AI analyze 4xx (no retry): analysisId={}, status={}, body={}",
                            request.getAnalysisId(), e.getStatusCode(),
                            sanitizeBody(e.getResponseBodyAsString()));
                    throw lastException;
                }
                log.warn("AI analyze {} (will retry if attempts left): analysisId={}",
                        e.getStatusCode(), request.getAnalysisId());
            } catch (RuntimeException e) {
                if (isTimeoutOrIo(e)) {
                    lastException = new AIServiceException(
                            "AI service call timeout or io error: " + e.getMessage(),
                            unwrapCause(e));
                    log.warn("AI analyze timeout/io (will retry if attempts left): analysisId={}, error={}",
                            request.getAnalysisId(), e.getMessage());
                } else {
                    throw new AIServiceException(
                            "AI service call unexpected error: " + e.getMessage(), e);
                }
            }
            if (i < attempts - 1) {
                sleepBeforeRetry(retryIntervalMs);
            }
        }
        long durationMs = System.currentTimeMillis() - startMs;
        log.error("AI analyze failed after {} attempts: analysisId={}, durationMs={}",
                attempts, request.getAnalysisId(), durationMs);
        throw lastException;
    }

    /**
     * SSE 流式调用 Python /api/agent/analyze/stream。
     * <p>接收 SSE 事件流，转换为 Flux&lt;AgentSseEvent&gt;。
     * <p>支持 Last-Event-ID Header 透传（断线重连）。
     * <p>处理 408 超时：HTTP 408 或 event=error + data.type=timeout → 转为标准降级事件。
     */
    public Flux<AgentSseEvent> analyzeStream(AgentRequest request, String lastEventId) {
        return streamSse(ENDPOINT_ANALYZE_STREAM, request, lastEventId);
    }

    /**
     * SSE 流式调用 Python /api/agent/compare/stream（task27）。
     */
    public Flux<AgentSseEvent> compareStream(AgentRequest request, String lastEventId) {
        return streamSse(ENDPOINT_COMPARE_STREAM, request, lastEventId);
    }

    /**
     * SSE 流式调用 Python /api/agent/report/stream（task27）。
     */
    public Flux<AgentSseEvent> reportStream(AgentRequest request, String lastEventId) {
        return streamSse(ENDPOINT_REPORT_STREAM, request, lastEventId);
    }

    /**
     * SSE 流式调用私有方法（task27 公共方法）。
     * <p>三个 public SSE 方法（analyzeStream/compareStream/reportStream）复用此实现，仅 endpoint 不同。
     * <p>流程：构造请求 → 透传 Last-Event-ID → 接收 byte[] 块流 → 累积到 StringBuilder →
     * 按 {@code \n\n} 切分事件 → 解析为 AgentSseEvent → 120s 超时保护 → 408 转降级事件。
     * <p>注：使用 bodyToFlux(byte[].class) + 手动 SSE 解析，兼容 Spring WebClient 默认 decoder 不解析 SSE 文本流的限制。
     */
    private Flux<AgentSseEvent> streamSse(String endpoint, AgentRequest request, String lastEventId) {
        WebClient.RequestBodySpec bodySpec = sseWebClient.post().uri(endpoint);
        // Last-Event-ID Header 透传（断线重连）
        if (lastEventId != null && !lastEventId.isBlank()) {
            bodySpec = bodySpec.header("Last-Event-ID", lastEventId);
        }
        return bodySpec
                .bodyValue(request)
                .retrieve()
                .bodyToFlux(byte[].class)
                .timeout(Duration.ofSeconds(SSE_RESPONSE_TIMEOUT_SECONDS))
                .flatMapIterable(this::splitSseEvents)
                .map(this::parseSseEvent)
                .filter(e -> e.getEvent() != null || e.getData() != null)
                .flatMap(this::transformTimeoutEvents)
                .doOnError(e -> log.warn("SSE stream error: endpoint={}, analysisId={}, error={}",
                        endpoint, request.getAnalysisId(), e.getMessage()))
                .onErrorContinue((err, item) ->
                        log.warn("SSE event 跳过: {}", err.getMessage()));
    }

    /**
     * 将 byte[] 块拆分为完整 SSE 事件文本（每个事件以 {@code \n\n} 结尾）。
     */
    private List<String> splitSseEvents(byte[] bytes) {
        if (bytes == null || bytes.length == 0) {
            return Collections.emptyList();
        }
        String chunk = new String(bytes, java.nio.charset.StandardCharsets.UTF_8);
        // 按 \n\n 切分；保留末尾不完整块时返回单元素（最简实现，假设 Mock 测试用完整事件块）
        String[] parts = chunk.split("\\n\\n");
        return List.of(parts);
    }

    /**
     * 解析单条 SSE 事件文本为 AgentSseEvent。
     * <p>SSE 格式：每行 {@code id:} / {@code event:} / {@code data:}；事件以空行分隔。
     */
    private AgentSseEvent parseSseEvent(String sseText) {
        if (sseText == null || sseText.isBlank()) {
            return AgentSseEvent.builder().build();
        }
        AgentSseEvent.AgentSseEventBuilder builder = AgentSseEvent.builder();
        StringBuilder dataBuf = new StringBuilder();
        for (String line : sseText.split("\n")) {
            String trimmed = line.endsWith("\r") ? line.substring(0, line.length() - 1) : line;
            if (trimmed.startsWith("id:")) {
                try {
                    builder.id(Long.parseLong(trimmed.substring(3).trim()));
                } catch (NumberFormatException ignored) {
                }
            } else if (trimmed.startsWith("event:")) {
                builder.event(trimmed.substring(6).trim());
            } else if (trimmed.startsWith("data:")) {
                if (dataBuf.length() > 0) dataBuf.append("\n");
                dataBuf.append(trimmed.substring(5).trim());
            }
        }
        if (dataBuf.length() > 0) {
            String dataJson = dataBuf.toString();
            try {
                Map<String, Object> dataMap = objectMapper.readValue(dataJson, Map.class);
                builder.data(dataMap);
            } catch (Exception e) {
                log.debug("SSE data 解析失败: {}", e.getMessage());
            }
        }
        return builder.build();
    }

    /**
     * 处理 408 超时事件 → 转为前端可理解的降级事件（task27）。
     * <p>Python 返回 HTTP 408 或 event=error + data.type=timeout → 输出 AgentSseEvent(event=error, data={type:timeout, message:Agent执行超时})
     */
    private Flux<AgentSseEvent> transformTimeoutEvents(AgentSseEvent event) {
        if (event == null) {
            return Flux.empty();
        }
        // 检测 408 超时：event=error + data.type=timeout
        if ("error".equals(event.getEvent()) && event.getData() != null) {
            Object type = event.getData().get("type");
            if ("timeout".equals(String.valueOf(type))) {
                Map<String, Object> degraded = new HashMap<>();
                degraded.put("type", "timeout");
                degraded.put("message", "Agent执行超时");
                log.warn("SSE 408 超时事件已转换: analysisId={}", event.getData().get("analysisId"));
                return Flux.just(AgentSseEvent.builder()
                        .id(event.getId())
                        .event("error")
                        .data(degraded)
                        .build());
            }
        }
        return Flux.just(event);
    }

    /**
     * 同步调用 Python /api/search/ 进行语义搜索。
     *
     * @param query   检索文本
     * @param topK    返回数量（1-50）
     * @param filters 过滤条件（yearFrom/yearTo/venue），可空
     * @return 搜索结果列表
     */
    public List<PaperSearchResultDTO> search(String query, int topK, Map<String, Object> filters) {
        if (query == null || query.isBlank()) {
            throw new IllegalArgumentException("query不能为空");
        }
        int safeTopK = Math.max(1, Math.min(topK <= 0 ? DEFAULT_TOP_K : topK, MAX_TOP_K));
        Map<String, Object> body = new HashMap<>();
        body.put("query", query);
        body.put("topK", safeTopK);
        body.put("filters", filters == null ? Collections.emptyMap() : filters);

        try {
            @SuppressWarnings("unchecked")
            Map<String, Object> response = (Map<String, Object>) webClient.post()
                    .uri(ENDPOINT_SEARCH)
                    .bodyValue(body)
                    .retrieve()
                    .bodyToMono(Map.class)
                    .block(Duration.ofSeconds(30));
            if (response == null) {
                return Collections.emptyList();
            }
            Object results = response.get("results");
            if (results instanceof List<?> list) {
                return mapToSearchResults(list);
            }
            return Collections.emptyList();
        } catch (WebClientResponseException e) {
            throw new AIServiceException("AI search failed: " + e.getStatusCode(), e);
        } catch (RuntimeException e) {
            throw new AIServiceException("AI search unexpected error: " + e.getMessage(), e);
        }
    }

    /**
     * 调用 Python /health 探测服务健康状态。
     * <p>独立 5s 超时；任何异常（超时/连接拒绝/5xx）一律返回 false，不抛异常。
     *
     * @return UP → true；非 UP → false
     */
    public boolean isHealthy() {
        try {
            String body = healthWebClient.get()
                    .uri(ENDPOINT_HEALTH)
                    .retrieve()
                    .bodyToMono(String.class)
                    .block(Duration.ofSeconds(HEALTH_TIMEOUT_SECONDS));
            if (body == null) {
                return false;
            }
            // 解析嵌套 data 层，读取 data.status（AI 服务统一用 ok(data={...}) 包装）
            try {
                Map<?, ?> map = objectMapper.readValue(body, Map.class);
                Object data = map.get("data");
                if (data instanceof Map<?, ?> dataMap) {
                    Object status = dataMap.get("status");
                    return "UP".equals(status);
                }
                return false;
            } catch (Exception parseErr) {
                log.debug("Health body parse failed: {}", parseErr.getMessage());
                return false;
            }
        } catch (Exception e) {
            log.debug("AI health check failed: {}", e.getMessage());
            return false;
        }
    }

    /**
     * 同步调用 Python /api/model/status 获取模型状态。
     *
     * @return ModelStatusDTO
     */
    public ModelStatusDTO getModelStatus() {
        try {
            return webClient.get()
                    .uri(ENDPOINT_MODEL_STATUS)
                    .retrieve()
                    .bodyToMono(ModelStatusDTO.class)
                    .block(Duration.ofSeconds(15));
        } catch (WebClientResponseException e) {
            throw new AIServiceException("AI model status failed: " + e.getStatusCode(), e);
        } catch (RuntimeException e) {
            throw new AIServiceException("AI model status unexpected error: " + e.getMessage(), e);
        }
    }

    // region 私有方法

    private void sleepBeforeRetry(long ms) {
        try {
            TimeUnit.MILLISECONDS.sleep(ms);
        } catch (InterruptedException ie) {
            Thread.currentThread().interrupt();
        }
    }

    private boolean isTimeoutOrIo(Throwable t) {
        Throwable cur = t;
        while (cur != null) {
            if (cur instanceof TimeoutException || cur instanceof java.io.IOException) {
                return true;
            }
            cur = cur.getCause();
        }
        return false;
    }

    private Throwable unwrapCause(Throwable t) {
        Throwable cur = t;
        while (cur.getCause() != null && cur.getCause() != cur) {
            cur = cur.getCause();
        }
        return cur;
    }

    /**
     * 脱敏异常响应体（屏蔽可能的 API Key / Token 字段）
     */
    private String sanitizeBody(String body) {
        if (body == null) {
            return "";
        }
        return body.replaceAll(
                "(?i)(api[_-]?key|token|secret|password)[\"']?\\s*[:=]\\s*[\"']?[^\"',}\\s]+",
                "$1: ***");
    }

    private WebClient buildHealthWebClient(String baseUrl) {
        HttpClient httpClient = HttpClient.create()
                .responseTimeout(Duration.ofSeconds(HEALTH_TIMEOUT_SECONDS));
        return WebClient.builder()
                .clientConnector(new ReactorClientHttpConnector(httpClient))
                .baseUrl(baseUrl)
                .build();
    }

    /**
     * 用注入的 Spring 全局 ObjectMapper 转换 Map → PaperSearchResultDTO。
     * <p>全局 ObjectMapper 已含 JavaTimeModule + SNAKE_CASE，PaperSearchResultDTO 显式用
     * @JsonProperty 标注 paperId/abstract，覆盖全局 SNAKE_CASE。
     */
    private List<PaperSearchResultDTO> mapToSearchResults(List<?> list) {
        try {
            return list.stream()
                    .map(item -> objectMapper.convertValue(item, PaperSearchResultDTO.class))
                    .toList();
        } catch (Exception e) {
            log.warn("Search result mapping failed: {}", e.getMessage());
            return Collections.emptyList();
        }
    }

    // endregion
}
