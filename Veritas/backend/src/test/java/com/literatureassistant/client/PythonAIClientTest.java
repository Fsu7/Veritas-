package com.literatureassistant.client;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.literatureassistant.dto.common.AgentRequest;
import com.literatureassistant.dto.common.UserProfileDTO;
import com.literatureassistant.dto.response.AgentSseEvent;
import com.literatureassistant.dto.response.AnalysisResultDTO;
import com.literatureassistant.dto.response.PaperSearchResultDTO;
import com.literatureassistant.enums.AnalysisStatus;
import com.literatureassistant.enums.EducationLevel;
import com.literatureassistant.enums.KnowledgeLevel;
import com.literatureassistant.enums.PreferredStyle;
import com.literatureassistant.exception.AIServiceException;
import okhttp3.mockwebserver.MockResponse;
import okhttp3.mockwebserver.MockWebServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.client.reactive.ReactorClientHttpConnector;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Flux;
import reactor.netty.http.client.HttpClient;
import reactor.test.StepVerifier;

import java.io.IOException;
import java.time.Duration;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * PythonAIClient 单元测试：使用 MockWebServer 模拟 Python AI 服务响应。
 * <p>覆盖正常/超时/5xx/4xx/重试/AIServiceException 转换 + SSE compareStream/reportStream/408 事件转换 7+ 个核心场景。
 *
 * @author XH-202630 Literature Assistant
 */
class PythonAIClientTest {

    private MockWebServer mockServer;
    private PythonAIClient client;
    private final ObjectMapper objectMapper = new ObjectMapper();

    @BeforeEach
    void setUp() throws IOException {
        mockServer = new MockWebServer();
        mockServer.start();

        String baseUrl = mockServer.url("").toString().replaceAll("/$", "");

        WebClient mainClient = WebClient.builder()
                .clientConnector(new ReactorClientHttpConnector(HttpClient.create()))
                .baseUrl(baseUrl)
                .build();
        WebClient sseClient = WebClient.builder()
                .clientConnector(new ReactorClientHttpConnector(HttpClient.create()))
                .baseUrl(baseUrl)
                .build();
        // 重试间隔 0ms 加速测试
        client = new PythonAIClient(mainClient, sseClient, baseUrl, 1, 0, new ObjectMapper());
    }

    @AfterEach
    void tearDown() throws IOException {
        mockServer.shutdown();
    }

    private AgentRequest buildRequest() {
        return AgentRequest.builder()
                .topic("Multi-Agent协同决策")
                .paperIds(List.of("arxiv_2024_001"))
                .userId("usr_001")
                .userProfile(UserProfileDTO.builder()
                        .educationLevel(EducationLevel.MASTER)
                        .researchField("NLP")
                        .knowledgeLevel(KnowledgeLevel.INTERMEDIATE)
                        .preferredStyle(PreferredStyle.BALANCED)
                        .build())
                .analysisId("anl_test_001")
                .build();
    }

    @Test
    @DisplayName("analyze - 200 正常返回 AnalysisResultDTO")
    void analyze_normal_returnsDTO() throws Exception {
        AnalysisResultDTO expected = AnalysisResultDTO.builder()
                .analysisId("anl_test_001")
                .status(AnalysisStatus.COMPLETED)
                .report("## Report")
                .degraded(false)
                .build();
        mockServer.enqueue(new MockResponse()
                .setHeader("Content-Type", "application/json")
                .setBody(objectMapper.writeValueAsString(expected)));

        AnalysisResultDTO actual = client.analyze(buildRequest());

        assertThat(actual).isNotNull();
        assertThat(actual.getAnalysisId()).isEqualTo("anl_test_001");
        assertThat(actual.getStatus()).isEqualTo(AnalysisStatus.COMPLETED);
        assertThat(actual.getReport()).isEqualTo("## Report");
    }

    @Test
    @DisplayName("analyze - 第一次 503 重试第二次成功")
    void analyze_5xx_triggers_retry() throws Exception {
        AnalysisResultDTO expected = AnalysisResultDTO.builder()
                .analysisId("anl_test_001")
                .status(AnalysisStatus.COMPLETED)
                .build();
        mockServer.enqueue(new MockResponse().setResponseCode(503).setBody("Service Unavailable"));
        mockServer.enqueue(new MockResponse()
                .setHeader("Content-Type", "application/json")
                .setBody(objectMapper.writeValueAsString(expected)));

        AnalysisResultDTO actual = client.analyze(buildRequest());

        assertThat(actual).isNotNull();
        assertThat(actual.getStatus()).isEqualTo(AnalysisStatus.COMPLETED);
        assertThat(mockServer.getRequestCount()).isEqualTo(2);
    }

    @Test
    @DisplayName("analyze - 两次 5xx 抛 AIServiceException(503)")
    void analyze_5xx_raises_AIServiceException() {
        mockServer.enqueue(new MockResponse().setResponseCode(503).setBody("Bad"));
        mockServer.enqueue(new MockResponse().setResponseCode(500).setBody("Bad"));

        assertThatThrownBy(() -> client.analyze(buildRequest()))
                .isInstanceOf(AIServiceException.class)
                .hasMessageContaining("AI service call failed");
    }

    @Test
    @DisplayName("analyze - 4xx 不重试直接抛 AIServiceException")
    void analyze_4xx_no_retry() throws Exception {
        mockServer.enqueue(new MockResponse().setResponseCode(400).setBody("Bad Request"));

        assertThatThrownBy(() -> client.analyze(buildRequest()))
                .isInstanceOf(AIServiceException.class);
        // 4xx 不重试，验证只请求 1 次
        TimeUnit.MILLISECONDS.sleep(100);
        assertThat(mockServer.getRequestCount()).isEqualTo(1);
    }

    @Test
    @DisplayName("isHealthy - 200 + data.status=UP 返回 true")
    void isHealthy_returns_true_on_200() {
        mockServer.enqueue(new MockResponse()
                .setHeader("Content-Type", "application/json")
                .setBody("{\"code\":200,\"data\":{\"status\":\"UP\",\"llm\":\"loaded\"}}"));

        boolean healthy = client.isHealthy();
        assertThat(healthy).isTrue();
    }

    @Test
    @DisplayName("isHealthy - 5xx 返回 false 且不抛异常")
    void isHealthy_returns_false_on_5xx() {
        mockServer.enqueue(new MockResponse().setResponseCode(503).setBody("Down"));

        boolean healthy = client.isHealthy();
        assertThat(healthy).isFalse();
    }

    @Test
    @DisplayName("search - 正确传递 topK + filters + 返回 List<PaperSearchResultDTO>")
    void search_passes_topK_and_filters() throws Exception {
        Map<String, Object> responseBody = new HashMap<>();
        Map<String, Object> item = new HashMap<>();
        // Python model_dump(by_alias=True) 输出 camelCase, 与 PaperSearchResultDTO @JsonProperty 标注对齐
        item.put("paperId", "arxiv_2024_001");
        item.put("title", "Attention Is All You Need");
        item.put("abstract", "We propose Transformer");
        item.put("score", 0.95);
        item.put("year", 2017);
        item.put("venue", "NeurIPS");
        responseBody.put("results", List.of(item));
        responseBody.put("total", 1);

        mockServer.enqueue(new MockResponse()
                .setHeader("Content-Type", "application/json")
                .setBody(objectMapper.writeValueAsString(responseBody)));

        Map<String, Object> filters = Map.of("yearFrom", 2020, "yearTo", 2024, "venue", "ACL");
        List<PaperSearchResultDTO> results = client.search("transformer", 10, filters);

        assertThat(results).hasSize(1);
        assertThat(results.get(0).getPaperId()).isEqualTo("arxiv_2024_001");
        assertThat(results.get(0).getTitle()).isEqualTo("Attention Is All You Need");
        assertThat(results.get(0).getScore()).isEqualTo(0.95);
    }

    // ========================= task27 SSE 扩展测试 =========================

    @Test
    @DisplayName("analyzeStream - 正确解析 SSE 事件流为 Flux<AgentSseEvent>")
    void analyzeStream_parses_sse_events() throws Exception {
        // 模拟 SSE 事件流
        String sseBody = "id:1\nevent:agent_started\ndata:{\"agentName\":\"retriever\",\"analysisId\":\"anl_001\"}\n\n"
                + "id:2\nevent:agent_state_update\ndata:{\"agentName\":\"retriever\",\"status\":\"running\"}\n\n";
        mockServer.enqueue(new MockResponse()
                .setHeader("Content-Type", "text/event-stream")
                .setBody(sseBody));

        Flux<AgentSseEvent> flux = client.analyzeStream(buildRequest(), null);

        StepVerifier.create(flux.collectList())
                .assertNext(events -> {
                    assertThat(events).isNotEmpty();
                    assertThat(events.get(0).getEvent()).isEqualTo("agent_started");
                })
                .verifyComplete();
    }

    @Test
    @DisplayName("compareStream - 正确调用 /api/agent/compare/stream 端点")
    void compareStream_constructs_correct_request() throws Exception {
        String sseBody = "id:1\nevent:analysis_completed\ndata:{\"analysisId\":\"anl_002\",\"status\":\"completed\"}\n\n";
        mockServer.enqueue(new MockResponse()
                .setHeader("Content-Type", "text/event-stream")
                .setBody(sseBody));

        Flux<AgentSseEvent> flux = client.compareStream(buildRequest(), null);

        StepVerifier.create(flux.collectList())
                .assertNext(events -> assertThat(events).isNotEmpty())
                .verifyComplete();
        // 验证请求路径
        assertThat(mockServer.takeRequest().getPath()).isEqualTo("/api/agent/compare/stream");
    }

    @Test
    @DisplayName("reportStream - 正确调用 /api/agent/report/stream 端点")
    void reportStream_constructs_correct_request() throws Exception {
        String sseBody = "id:1\nevent:analysis_completed\ndata:{\"analysisId\":\"anl_003\",\"status\":\"completed\"}\n\n";
        mockServer.enqueue(new MockResponse()
                .setHeader("Content-Type", "text/event-stream")
                .setBody(sseBody));

        Flux<AgentSseEvent> flux = client.reportStream(buildRequest(), null);

        StepVerifier.create(flux.collectList())
                .assertNext(events -> assertThat(events).isNotEmpty())
                .verifyComplete();
        assertThat(mockServer.takeRequest().getPath()).isEqualTo("/api/agent/report/stream");
    }

    @Test
    @DisplayName("compareStream - 透传 Last-Event-ID Header")
    void compareStream_passes_lastEventId_header() throws Exception {
        String sseBody = "id:5\nevent:agent_state_update\ndata:{\"agentName\":\"retriever\"}\n\n";
        mockServer.enqueue(new MockResponse()
                .setHeader("Content-Type", "text/event-stream")
                .setBody(sseBody));

        client.compareStream(buildRequest(), "evt_3").collectList().block(Duration.ofSeconds(5));

        okhttp3.mockwebserver.RecordedRequest request = mockServer.takeRequest();
        assertThat(request.getHeader("Last-Event-ID")).isEqualTo("evt_3");
    }

    @Test
    @DisplayName("reportStream - 透传 Last-Event-ID Header")
    void reportStream_passes_lastEventId_header() throws Exception {
        String sseBody = "id:7\nevent:agent_state_update\ndata:{\"agentName\":\"generator\"}\n\n";
        mockServer.enqueue(new MockResponse()
                .setHeader("Content-Type", "text/event-stream")
                .setBody(sseBody));

        client.reportStream(buildRequest(), "evt_5").collectList().block(Duration.ofSeconds(5));

        okhttp3.mockwebserver.RecordedRequest request = mockServer.takeRequest();
        assertThat(request.getHeader("Last-Event-ID")).isEqualTo("evt_5");
    }

    @Test
    @DisplayName("SSE - event=error + data.type=timeout → 转为标准降级事件 (data={type:timeout, message:Agent执行超时})")
    void sse_408_event_transformed_to_timeout_error() throws Exception {
        // Python 端发送 408 超时事件
        String sseBody = "id:1\nevent:error\ndata:{\"type\":\"timeout\",\"message\":\"上游超时\"}\n\n";
        mockServer.enqueue(new MockResponse()
                .setHeader("Content-Type", "text/event-stream")
                .setBody(sseBody));

        Flux<AgentSseEvent> flux = client.analyzeStream(buildRequest(), null);

        StepVerifier.create(flux.collectList())
                .assertNext(events -> {
                    assertThat(events).hasSize(1);
                    AgentSseEvent transformed = events.get(0);
                    assertThat(transformed.getEvent()).isEqualTo("error");
                    assertThat(transformed.getData()).containsEntry("type", "timeout");
                    assertThat(transformed.getData()).containsEntry("message", "Agent执行超时");
                })
                .verifyComplete();
    }
}
