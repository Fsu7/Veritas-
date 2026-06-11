package com.literatureassistant.sse;

import com.literatureassistant.controller.AgentController;
import com.literatureassistant.dto.response.AgentSseEvent;
import com.literatureassistant.service.AgentClientService;
import com.literatureassistant.service.AnalysisService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.codec.ServerSentEvent;

import java.lang.reflect.Method;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * SSE 事件格式标准化测试（task29）。
 * <p>验证 AgentController.toStandardizedSseEvent 对 7 种事件类型的 data 格式标准化。
 *
 * @author XH-202630 Literature Assistant
 * @since 0.4
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("SSE 事件格式标准化")
class SseEventFormatTest {

    @Mock
    private AnalysisService analysisService;

    @Mock
    private AgentClientService agentClientService;

    private AgentController controller;

    @BeforeEach
    void setUp() {
        controller = new AgentController(analysisService, agentClientService);
    }

    private Object invokeToStandardized(AgentSseEvent event) throws Exception {
        Method method = AgentController.class.getDeclaredMethod("toStandardizedSseEvent", AgentSseEvent.class);
        method.setAccessible(true);
        ServerSentEvent<?> sse = (ServerSentEvent<?>) method.invoke(controller, event);
        return sse.data();
    }

    @Test
    @DisplayName("agent_started → {agentName, analysisId, timestamp}")
    void sseEventFormat_agent_started_has_required_fields() throws Exception {
        AgentSseEvent event = AgentSseEvent.builder()
                .id(1L)
                .event("agent_started")
                .data(Map.of("agentName", "retriever", "analysisId", "anl_001"))
                .build();

        @SuppressWarnings("unchecked")
        Map<String, Object> data = (Map<String, Object>) invokeToStandardized(event);

        assertThat(data).containsKeys("agentName", "analysisId", "timestamp");
        assertThat(data.get("agentName")).isEqualTo("retriever");
        assertThat(data.get("analysisId")).isEqualTo("anl_001");
        assertThat((String) data.get("timestamp")).isNotBlank();
    }

    @Test
    @DisplayName("agent_state_update → {agentName, status, progress, intermediateResult, durationMs}")
    void sseEventFormat_agent_state_update_has_required_fields() throws Exception {
        AgentSseEvent event = AgentSseEvent.builder()
                .id(2L)
                .event("agent_state_update")
                .data(Map.of(
                        "agentName", "analyzer",
                        "status", "running",
                        "progress", 0.45,
                        "intermediateResult", "extracting key findings",
                        "durationMs", 3200L
                ))
                .build();

        @SuppressWarnings("unchecked")
        Map<String, Object> data = (Map<String, Object>) invokeToStandardized(event);

        assertThat(data).containsKeys("agentName", "status", "progress", "intermediateResult", "durationMs");
        assertThat(data.get("agentName")).isEqualTo("analyzer");
        assertThat(data.get("status")).isEqualTo("running");
        assertThat(data.get("progress")).isEqualTo(0.45);
        assertThat(data.get("intermediateResult")).isEqualTo("extracting key findings");
        assertThat(((Number) data.get("durationMs")).longValue()).isEqualTo(3200L);
    }

    @Test
    @DisplayName("agent_completed → {agentName, analysisId, result, timestamp}")
    void sseEventFormat_agent_completed_has_required_fields() throws Exception {
        AgentSseEvent event = AgentSseEvent.builder()
                .id(3L)
                .event("agent_completed")
                .data(Map.of("agentName", "retriever", "analysisId", "anl_001", "result", "search done"))
                .build();

        @SuppressWarnings("unchecked")
        Map<String, Object> data = (Map<String, Object>) invokeToStandardized(event);

        assertThat(data).containsKeys("agentName", "analysisId", "result", "timestamp");
        assertThat(data.get("agentName")).isEqualTo("retriever");
        assertThat(data.get("result")).isEqualTo("search done");
        assertThat((String) data.get("timestamp")).isNotBlank();
    }

    @Test
    @DisplayName("agent_failed → {agentName, error, timestamp}")
    void sseEventFormat_agent_failed_has_required_fields() throws Exception {
        AgentSseEvent event = AgentSseEvent.builder()
                .id(4L)
                .event("agent_failed")
                .data(Map.of("agentName", "generator", "error", "model unavailable"))
                .build();

        @SuppressWarnings("unchecked")
        Map<String, Object> data = (Map<String, Object>) invokeToStandardized(event);

        assertThat(data).containsKeys("agentName", "error", "timestamp");
        assertThat(data.get("agentName")).isEqualTo("generator");
        assertThat(data.get("error")).isEqualTo("model unavailable");
        assertThat((String) data.get("timestamp")).isNotBlank();
    }

    @Test
    @DisplayName("analysis_completed → {analysisId, status, report, citations}")
    void sseEventFormat_analysis_completed_has_required_fields() throws Exception {
        AgentSseEvent event = AgentSseEvent.builder()
                .id(5L)
                .event("analysis_completed")
                .data(Map.of("analysisId", "anl_001", "report", "# Summary\n..."))
                .build();

        @SuppressWarnings("unchecked")
        Map<String, Object> data = (Map<String, Object>) invokeToStandardized(event);

        assertThat(data).containsKeys("analysisId", "status", "report");
        assertThat(data.get("status")).isEqualTo("completed");
        assertThat(data.get("report")).isEqualTo("# Summary\n...");
    }

    @Test
    @DisplayName("error → {type, message}，不含堆栈/URL")
    void sseEventFormat_error_has_required_fields_no_stack_or_url() throws Exception {
        AgentSseEvent event = AgentSseEvent.builder()
                .id(6L)
                .event("error")
                .data(Map.of("message", "AI service unavailable"))
                .build();

        @SuppressWarnings("unchecked")
        Map<String, Object> data = (Map<String, Object>) invokeToStandardized(event);

        assertThat(data).containsKeys("type", "message");
        assertThat(data.get("type")).isEqualTo("internal");
        assertThat(data.get("message")).isEqualTo("AI service unavailable");

        // 验证不含堆栈/URL
        for (String key : data.keySet()) {
            assertThat(key).doesNotContain("stack", "trace", "url", "uri", "URL");
        }
        for (Object value : data.values()) {
            if (value instanceof String s) {
                assertThat(s).doesNotContain("at com.", "java.lang.", "http://", "https://");
            }
        }
    }

    @Test
    @DisplayName("ping → {timestamp}，timestamp 非空（ISO8601）")
    void sseEventFormat_ping_has_required_fields() throws Exception {
        AgentSseEvent event = AgentSseEvent.builder()
                .id(7L)
                .event("ping")
                .data(Map.of())
                .build();

        @SuppressWarnings("unchecked")
        Map<String, Object> data = (Map<String, Object>) invokeToStandardized(event);

        assertThat(data).containsKeys("timestamp");
        assertThat((String) data.get("timestamp")).isNotBlank();
    }

    @Test
    @DisplayName("timestamp 为 ISO8601 格式（非空字符串）")
    void sseEventFormat_timestamp_is_iso8601_non_empty() throws Exception {
        AgentSseEvent event = AgentSseEvent.builder()
                .id(8L)
                .event("agent_started")
                .data(Map.of("agentName", "coordinator", "analysisId", "anl_002"))
                .build();

        @SuppressWarnings("unchecked")
        Map<String, Object> data = (Map<String, Object>) invokeToStandardized(event);

        String timestamp = (String) data.get("timestamp");
        assertThat(timestamp).isNotBlank();
        // ISO8601 基本特征：包含 'T' 或 '-'
        assertThat(timestamp).matches(".*\\d{4}-\\d{2}-\\d{2}.*");
    }

    @Test
    @DisplayName("空事件类型 → data 不抛异常")
    void sseEventFormat_null_event_type_does_not_throw() throws Exception {
        AgentSseEvent event = AgentSseEvent.builder()
                .id(9L)
                .event(null)
                .data(Map.of("customKey", "customValue"))
                .build();

        @SuppressWarnings("unchecked")
        Map<String, Object> data = (Map<String, Object>) invokeToStandardized(event);

        assertThat(data).containsEntry("customKey", "customValue");
    }

    @Test
    @DisplayName("空 data → 不抛异常，事件类型仍正常补全字段")
    void sseEventFormat_null_data_does_not_throw() throws Exception {
        AgentSseEvent event = AgentSseEvent.builder()
                .id(10L)
                .event("agent_started")
                .data(null)
                .build();

        @SuppressWarnings("unchecked")
        Map<String, Object> data = (Map<String, Object>) invokeToStandardized(event);

        assertThat(data).containsKeys("timestamp");
        assertThat((String) data.get("timestamp")).isNotBlank();
    }

    @Test
    @DisplayName("error 事件不自动补全 agentName/analysisId 等 Agent 字段")
    void sseEventFormat_error_does_not_contain_agent_fields() throws Exception {
        AgentSseEvent event = AgentSseEvent.builder()
                .id(11L)
                .event("error")
                .data(Map.of("message", "timeout"))
                .build();

        @SuppressWarnings("unchecked")
        Map<String, Object> data = (Map<String, Object>) invokeToStandardized(event);

        // error 事件不应包含 agentName, analysisId, result, progress 等 Agent 专用字段
        assertThat(data).doesNotContainKeys("agentName", "analysisId", "result", "progress", "durationMs");
    }
}
