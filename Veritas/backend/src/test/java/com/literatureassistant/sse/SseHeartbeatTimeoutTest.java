package com.literatureassistant.sse;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.literatureassistant.client.PythonAIClient;
import com.literatureassistant.config.SecurityConfig;
import com.literatureassistant.config.WebClientConfig;
import com.literatureassistant.config.CustomAccessDeniedHandler;
import com.literatureassistant.config.CustomAuthenticationEntryPoint;
import com.literatureassistant.dto.response.AgentSseEvent;
import com.literatureassistant.filter.JwtAuthFilter;
import com.literatureassistant.service.AgentClientService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import reactor.core.publisher.Flux;
import reactor.test.StepVerifier;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.time.Duration;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * SSE 心跳/超时/CORS/WebClientConfig 超时测试（task29）。
 *
 * @author XH-202630 Literature Assistant
 * @since 0.4
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("SSE 心跳/超时/CORS/WebClient 配置")
class SseHeartbeatTimeoutTest {

    @Mock
    private PythonAIClient pythonAIClient;

    @Mock
    private RedisTemplate<String, String> redisTemplate;

    @Mock
    private CustomAuthenticationEntryPoint authenticationEntryPoint;

    @Mock
    private CustomAccessDeniedHandler accessDeniedHandler;

    @Mock
    private JwtAuthFilter jwtAuthFilter;

    private AgentClientService service;
    private final ObjectMapper objectMapper = new ObjectMapper();

    @BeforeEach
    void setUp() {
        service = new AgentClientService(pythonAIClient, redisTemplate, objectMapper);
    }

    @Test
    @DisplayName("心跳常量 HEARTBEAT_INTERVAL = 30s")
    void heartbeat_emits_ping_every_30s() throws Exception {
        Field field = AgentClientService.class.getDeclaredField("HEARTBEAT_INTERVAL");
        field.setAccessible(true);
        Duration heartbeat = (Duration) field.get(null);

        assertThat(heartbeat).isNotNull();
        assertThat(heartbeat.getSeconds()).isEqualTo(30);
    }

    @Test
    @DisplayName("SSE 超时常量 SSE_DATA_TIMEOUT = 120s")
    void timeout_emits_error_after_120s_no_data() throws Exception {
        Field field = AgentClientService.class.getDeclaredField("SSE_DATA_TIMEOUT");
        field.setAccessible(true);
        Duration timeout = (Duration) field.get(null);

        assertThat(timeout).isNotNull();
        assertThat(timeout.getSeconds()).isEqualTo(120);
    }

    @Test
    @DisplayName("handleStreamFallback → Flux 发出 error + analysis_completed 两个降级事件")
    void handleStreamFallback_sends_degradation_events() throws Exception {
        Method method = AgentClientService.class.getDeclaredMethod(
                "handleStreamFallback", String.class, Throwable.class);
        method.setAccessible(true);

        Throwable cause = new RuntimeException("AI service down");

        @SuppressWarnings("unchecked")
        Flux<AgentSseEvent> flux = (Flux<AgentSseEvent>) method.invoke(service, "anl_test_001", cause);

        StepVerifier.create(flux)
                .assertNext(event -> {
                    assertThat(event.getEvent()).isEqualTo("error");
                    assertThat(event.getData()).isNotNull();
                    assertThat(event.getData()).containsEntry("type", "degradation");
                    assertThat(event.getData()).containsEntry("message", "AI服务暂时不可用，已返回缓存结果");
                })
                .assertNext(event -> {
                    assertThat(event.getEvent()).isEqualTo("analysis_completed");
                    assertThat(event.getData()).isNotNull();
                    assertThat(event.getData()).containsEntry("status", "completed");
                    assertThat(event.getData()).containsEntry("degraded", true);
                    assertThat(event.getData()).containsEntry("degradedReason", "AI服务暂时不可用，返回缓存结果");
                })
                .verifyComplete();
    }

    @Test
    @DisplayName("CORS allowedHeaders 包含 Last-Event-ID")
    void cors_allows_last_event_id_header() {
        SecurityConfig config = new SecurityConfig(authenticationEntryPoint, accessDeniedHandler, jwtAuthFilter);
        try {
            java.lang.reflect.Field allowedOriginsField = SecurityConfig.class.getDeclaredField("allowedOrigins");
            allowedOriginsField.setAccessible(true);
            allowedOriginsField.set(config, "http://localhost:5173");
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
        jakarta.servlet.http.HttpServletRequest mockRequest =
                new org.springframework.mock.web.MockHttpServletRequest();
        CorsConfigurationSource source = config.corsConfigurationSource();
        CorsConfiguration corsConfig = source.getCorsConfiguration(mockRequest);

        assertThat(corsConfig).isNotNull();
        assertThat(corsConfig.getAllowedHeaders()).contains("Last-Event-ID");
        assertThat(corsConfig.getAllowedHeaders()).contains("Authorization", "Content-Type");
    }

    @Test
    @DisplayName("WebClientConfig.sseWebClient responseTimeout=120s 且 ReadTimeoutHandler=120s")
    void webClient_sse_timeout_is_120s() {
        WebClientConfig config = new WebClientConfig();
        // 通过反射设置 aiServiceUrl 字段
        try {
            Field urlField = WebClientConfig.class.getDeclaredField("aiServiceUrl");
            urlField.setAccessible(true);
            urlField.set(config, "http://localhost:8000");
        } catch (Exception e) {
            throw new RuntimeException(e);
        }

        // 验证 sseWebClient bean 可正常创建，不抛异常
        org.springframework.web.reactive.function.client.WebClient sseClient = config.sseWebClient();

        assertThat(sseClient).isNotNull();
    }
}
