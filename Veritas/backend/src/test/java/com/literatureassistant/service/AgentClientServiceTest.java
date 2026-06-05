package com.literatureassistant.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.literatureassistant.client.PythonAIClient;
import com.literatureassistant.dto.common.AgentRequest;
import com.literatureassistant.dto.response.AgentStateResponse;
import com.literatureassistant.dto.response.AnalysisResultDTO;
import com.literatureassistant.enums.AnalysisStatus;
import com.literatureassistant.exception.AIServiceException;
import com.literatureassistant.util.RedisKeyUtil;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.core.HashOperations;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.ValueOperations;
import reactor.core.publisher.Mono;
import reactor.test.StepVerifier;

import java.time.Duration;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * AgentClientService 单元测试。
 *
 * @author XH-202630 Literature Assistant
 */
@ExtendWith(MockitoExtension.class)
class AgentClientServiceTest {

    @Mock
    private PythonAIClient pythonAIClient;

    @Mock
    private RedisTemplate<String, String> redisTemplate;

    @Mock
    private HashOperations<String, Object, Object> hashOperations;

    @Mock
    private ValueOperations<String, String> valueOperations;

    private AgentClientService service;
    private final ObjectMapper objectMapper = new ObjectMapper();

    @BeforeEach
    void setUp() {
        service = new AgentClientService(pythonAIClient, redisTemplate, objectMapper);
    }

    private AgentRequest buildRequest() {
        return AgentRequest.builder()
                .topic("Multi-Agent协同决策")
                .paperIds(List.of("arxiv_2024_001"))
                .userId("usr_001")
                .analysisId("anl_test_001")
                .build();
    }

    @Test
    @DisplayName("analyzePaper - 正常返回 DTO + 写 Redis Hash + 缓存")
    void analyzePaper_normal_returnsDTO() throws Exception {
        List<AgentStateResponse> agentStates = List.of(
                AgentStateResponse.builder()
                        .agentName("retriever")
                        .status("completed")
                        .progress(1.0)
                        .build()
        );
        AnalysisResultDTO expected = AnalysisResultDTO.builder()
                .analysisId("anl_test_001")
                .status(AnalysisStatus.COMPLETED)
                .agentStates(agentStates)
                .build();
        when(pythonAIClient.analyze(any(AgentRequest.class))).thenReturn(expected);
        when(redisTemplate.opsForHash()).thenReturn(hashOperations);
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);

        AnalysisResultDTO actual = service.analyzePaper(buildRequest());

        assertThat(actual).isNotNull();
        assertThat(actual.getAnalysisId()).isEqualTo("anl_test_001");
        assertThat(actual.getStatus()).isEqualTo(AnalysisStatus.COMPLETED);
        // 验证 Redis Hash 写入
        ArgumentCaptor<Map<String, String>> hashCaptor = ArgumentCaptor.forClass(Map.class);
        verify(hashOperations, times(1)).putAll(eq(RedisKeyUtil.agentStateKey("anl_test_001")), hashCaptor.capture());
        assertThat(hashCaptor.getValue()).containsKey("retriever");
        verify(redisTemplate, times(1)).expire(eq(RedisKeyUtil.agentStateKey("anl_test_001")), eq(Duration.ofMinutes(5)));
        // 验证分析结果 String 缓存
        verify(valueOperations, times(1))
                .set(eq(RedisKeyUtil.analysisResultKey("anl_test_001")), anyString(), eq(Duration.ofMinutes(30)));
    }

    @Test
    @DisplayName("analyzePaper - Python 抛 AIServiceException + Redis 无缓存 → 返回 degraded DTO")
    void analyzePaper_aiServiceException_triggers_fallback() {
        when(pythonAIClient.analyze(any(AgentRequest.class)))
                .thenThrow(new AIServiceException("AI service call failed: 503", new RuntimeException()));
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.get(RedisKeyUtil.agentFallbackKey("anl_test_001"))).thenReturn(null);

        AnalysisResultDTO actual = service.analyzePaper(buildRequest());

        assertThat(actual).isNotNull();
        assertThat(actual.getAnalysisId()).isEqualTo("anl_test_001");
        assertThat(actual.getDegraded()).isTrue();
        assertThat(actual.getDegradedReason()).contains("AI服务暂时不可用");
    }

    @Test
    @DisplayName("analyzePaper - Python 异常 + Redis 命中 fallback 缓存 → 返回 cached + degraded=true")
    void analyzePaper_cache_hit_returns_cached() throws Exception {
        when(pythonAIClient.analyze(any(AgentRequest.class)))
                .thenThrow(new AIServiceException("AI service call failed: 503", new RuntimeException()));
        AnalysisResultDTO cached = AnalysisResultDTO.builder()
                .analysisId("anl_test_001")
                .status(AnalysisStatus.COMPLETED)
                .report("cached report")
                .build();
        String cachedJson = objectMapper.writeValueAsString(cached);
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.get(RedisKeyUtil.agentFallbackKey("anl_test_001"))).thenReturn(cachedJson);

        AnalysisResultDTO actual = service.analyzePaper(buildRequest());

        assertThat(actual).isNotNull();
        assertThat(actual.getReport()).isEqualTo("cached report");
        assertThat(actual.getDegraded()).isTrue();
        assertThat(actual.getDegradedReason()).contains("缓存");
    }

    @Test
    @DisplayName("updateAgentState - 写入 Redis Hash + 设置 5min TTL")
    void updateAgentState_writes_to_redis_hash() {
        when(redisTemplate.opsForHash()).thenReturn(hashOperations);
        List<AgentStateResponse> states = List.of(
                AgentStateResponse.builder().agentName("retriever").status("completed").progress(1.0).build(),
                AgentStateResponse.builder().agentName("analyzer").status("running").progress(0.5).build()
        );

        service.updateAgentState("anl_001", states);

        ArgumentCaptor<Map<String, String>> captor = ArgumentCaptor.forClass(Map.class);
        verify(hashOperations, times(1)).putAll(eq(RedisKeyUtil.agentStateKey("anl_001")), captor.capture());
        assertThat(captor.getValue()).hasSize(2);
        assertThat(captor.getValue()).containsKey("retriever");
        assertThat(captor.getValue()).containsKey("analyzer");
        verify(redisTemplate, times(1)).expire(eq(RedisKeyUtil.agentStateKey("anl_001")), eq(Duration.ofMinutes(5)));
    }

    @Test
    @DisplayName("getAgentStates - Redis 空时返回 new ArrayList<>()（非 null）")
    void getAgentStates_empty_redis_returns_empty_list() {
        when(redisTemplate.opsForHash()).thenReturn(hashOperations);
        when(hashOperations.entries(RedisKeyUtil.agentStateKey("anl_empty"))).thenReturn(new HashMap<>());

        List<AgentStateResponse> result = service.getAgentStates("anl_empty");

        assertThat(result).isNotNull();
        assertThat(result).isEmpty();
        assertThat(result).isInstanceOf(ArrayList.class);
    }

    @Test
    @DisplayName("getAgentStates - 包含数据时反序列化为 List<AgentStateResponse>")
    void getAgentStates_with_data_deserializes() throws Exception {
        AgentStateResponse s1 = AgentStateResponse.builder()
                .agentName("retriever").status("completed").progress(1.0).build();
        AgentStateResponse s2 = AgentStateResponse.builder()
                .agentName("analyzer").status("running").progress(0.5).build();
        Map<Object, Object> entries = new HashMap<>();
        entries.put("retriever", objectMapper.writeValueAsString(s1));
        entries.put("analyzer", objectMapper.writeValueAsString(s2));

        when(redisTemplate.opsForHash()).thenReturn(hashOperations);
        when(hashOperations.entries(RedisKeyUtil.agentStateKey("anl_001"))).thenReturn(entries);

        List<AgentStateResponse> result = service.getAgentStates("anl_001");

        assertThat(result).hasSize(2);
        assertThat(result).extracting(AgentStateResponse::getAgentName)
                .containsExactlyInAnyOrder("retriever", "analyzer");
    }

    @Test
    @DisplayName("generateReport - Mono 可订阅并产生 AnalysisResultDTO")
    void generateReport_mono_subscribable() {
        AnalysisResultDTO expected = AnalysisResultDTO.builder()
                .analysisId("anl_001")
                .status(AnalysisStatus.COMPLETED)
                .build();
        when(pythonAIClient.analyze(any(AgentRequest.class))).thenReturn(expected);

        Mono<AnalysisResultDTO> mono = service.generateReport(buildRequest());

        // 触发 subscribe 才会真正执行内部 callable
        StepVerifier.create(mono)
                .expectNextMatches(r -> r.getAnalysisId().equals("anl_001")
                        && r.getStatus() == AnalysisStatus.COMPLETED)
                .verifyComplete();
        verify(pythonAIClient, times(1)).analyze(any(AgentRequest.class));
    }
}
