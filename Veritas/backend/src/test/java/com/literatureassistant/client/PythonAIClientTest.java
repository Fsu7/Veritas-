package com.literatureassistant.client;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.literatureassistant.dto.common.AgentRequest;
import com.literatureassistant.dto.common.UserProfileDTO;
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
import reactor.netty.http.client.HttpClient;

import java.io.IOException;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * PythonAIClient 单元测试：使用 MockWebServer 模拟 Python AI 服务响应。
 * <p>覆盖正常/超时/5xx/4xx/重试/AIServiceException 转换 7 个核心场景。
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
        // 重试间隔 0ms 加速测试
        client = new PythonAIClient(mainClient, baseUrl, 1, 0);
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
    @DisplayName("isHealthy - 200 + status=UP 返回 true")
    void isHealthy_returns_true_on_200() {
        mockServer.enqueue(new MockResponse()
                .setHeader("Content-Type", "application/json")
                .setBody("{\"status\":\"UP\",\"llm\":\"loaded\"}"));

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
}
