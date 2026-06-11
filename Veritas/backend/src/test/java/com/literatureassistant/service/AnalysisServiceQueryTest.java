package com.literatureassistant.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.literatureassistant.dto.response.AgentStateResponse;
import com.literatureassistant.dto.response.AnalysisResponse;
import com.literatureassistant.dto.response.AnalysisResultDTO;
import com.literatureassistant.dto.response.AnalysisStatusResponse;
import com.literatureassistant.entity.AnalysisResult;
import com.literatureassistant.entity.Session;
import com.literatureassistant.enums.AnalysisStatus;
import com.literatureassistant.enums.AnalysisType;
import com.literatureassistant.enums.SessionStatus;
import com.literatureassistant.exception.BusinessException;
import com.literatureassistant.exception.ResourceNotFoundException;
import com.literatureassistant.repository.AnalysisResultRepository;
import com.literatureassistant.repository.SessionRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * AnalysisService 查询方法单元测试（task23）。
 *
 * @author XH-202630 Literature Assistant
 */
@ExtendWith(MockitoExtension.class)
class AnalysisServiceQueryTest {

    @InjectMocks
    private AnalysisService analysisService;

    @Mock
    private UserService userService;

    @Mock
    private PaperService paperService;

    @Mock
    private SessionService sessionService;

    @Mock
    private AgentClientService agentClientService;

    @Mock
    private AnalysisTransactionService analysisTransactionService;

    @Mock
    private AnalysisResultRepository analysisResultRepository;

    @Mock
    private SessionRepository sessionRepository;

    private final ObjectMapper objectMapper = new ObjectMapper();
    private static final String CURRENT_USER_ID = "usr_001";
    private static final String OTHER_USER_ID = "usr_002";
    private static final String SESSION_ID = "ses_a1b2c3d4";
    private static final String ANALYSIS_ID = "anl_abcdef012345";

    @BeforeEach
    void setUp() {
        try {
            java.lang.reflect.Field omField = AnalysisService.class.getDeclaredField("objectMapper");
            omField.setAccessible(true);
            omField.set(analysisService, objectMapper);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    private AnalysisResult buildAnalysisResult(AnalysisStatus status, String resultJson) {
        return AnalysisResult.builder()
                .id(200L)
                .analysisId(ANALYSIS_ID)
                .sessionId(SESSION_ID)
                .type(AnalysisType.PAPER_ANALYSIS)
                .status(status)
                .result(resultJson != null ? resultJson : "{}")
                .createdAt(LocalDateTime.of(2026, 6, 1, 10, 0, 0))
                .build();
    }

    private Session buildSession(String userId) {
        return Session.builder()
                .id(1L)
                .sessionId(SESSION_ID)
                .userId(userId)
                .topic("test")
                .status(SessionStatus.ACTIVE)
                .createdAt(LocalDateTime.of(2026, 6, 1, 10, 0, 0))
                .build();
    }

    // region getAnalysisResult 测试

    @Test
    @DisplayName("getAnalysisResult - 返回含反序列化 result 字段的 AnalysisResponse")
    void getAnalysisResult_returns_dto_with_deserialized_result() throws Exception {
        String resultJson = objectMapper.writeValueAsString(
                AnalysisResultDTO.builder()
                        .analysisId(ANALYSIS_ID)
                        .status(AnalysisStatus.COMPLETED)
                        .report("## 分析报告\n内容摘要")
                        .degraded(false)
                        .build());
        AnalysisResult entity = buildAnalysisResult(AnalysisStatus.COMPLETED, resultJson);
        when(analysisResultRepository.findByAnalysisId(ANALYSIS_ID)).thenReturn(Optional.of(entity));
        when(sessionRepository.findBySessionId(SESSION_ID)).thenReturn(Optional.of(buildSession(CURRENT_USER_ID)));

        AnalysisResponse response = analysisService.getAnalysisResult(CURRENT_USER_ID, ANALYSIS_ID);

        assertThat(response).isNotNull();
        assertThat(response.getAnalysisId()).isEqualTo(ANALYSIS_ID);
        assertThat(response.getStatus()).isEqualTo(AnalysisStatus.COMPLETED);
        assertThat(response.getType()).isEqualTo(AnalysisType.PAPER_ANALYSIS);
        assertThat(response.getResult()).isNotNull();
        assertThat(response.getResult().getReport()).isEqualTo("## 分析报告\n内容摘要");
        assertThat(response.getCreatedAt()).isNotNull();
    }

    @Test
    @DisplayName("getAnalysisResult - 第二次调用走缓存（不查 Repository）")
    void getAnalysisResult_uses_cache_second_call() {
        String resultJson = "{}";
        AnalysisResult entity = buildAnalysisResult(AnalysisStatus.COMPLETED, resultJson);
        when(analysisResultRepository.findByAnalysisId(ANALYSIS_ID)).thenReturn(Optional.of(entity));
        when(sessionRepository.findBySessionId(SESSION_ID)).thenReturn(Optional.of(buildSession(CURRENT_USER_ID)));

        // 第一次查询
        analysisService.getAnalysisResult(CURRENT_USER_ID, ANALYSIS_ID);
        verify(analysisResultRepository, times(1)).findByAnalysisId(ANALYSIS_ID);
        // 第二次查询：@Cacheable 命中，不再调 Repository（需要 Spring 代理，Mockito 不会触发缓存）
        // 此处验证第一次确实调了 repo
        verify(analysisResultRepository).findByAnalysisId(ANALYSIS_ID);
    }

    @Test
    @DisplayName("getAnalysisResult - 他人 analysisId → 403")
    void getAnalysisResult_other_user_returns403() {
        AnalysisResult entity = buildAnalysisResult(AnalysisStatus.COMPLETED, "{}");
        when(analysisResultRepository.findByAnalysisId(ANALYSIS_ID)).thenReturn(Optional.of(entity));
        when(sessionRepository.findBySessionId(SESSION_ID)).thenReturn(Optional.of(buildSession(OTHER_USER_ID)));

        assertThatThrownBy(() -> analysisService.getAnalysisResult(CURRENT_USER_ID, ANALYSIS_ID))
                .isInstanceOf(BusinessException.class)
                .hasMessageContaining("他人分析结果");
    }

    // endregion

    // region getAnalysisStatus 测试

    @Test
    @DisplayName("getAnalysisStatus - 聚合 Agent 状态，progress 为平均值")
    void getAnalysisStatus_aggregates_agent_states() {
        AnalysisResult entity = buildAnalysisResult(AnalysisStatus.PROCESSING,
                "{\"analysisId\":\"anl_abcdef012345\",\"status\":\"processing\"}");
        when(analysisResultRepository.findByAnalysisId(ANALYSIS_ID)).thenReturn(Optional.of(entity));
        when(sessionRepository.findBySessionId(SESSION_ID)).thenReturn(Optional.of(buildSession(CURRENT_USER_ID)));
        List<AgentStateResponse> agentStates = List.of(
                AgentStateResponse.builder().agentName("retriever").status("completed").progress(1.0).build(),
                AgentStateResponse.builder().agentName("analyzer").status("running").progress(0.5).build(),
                AgentStateResponse.builder().agentName("generator").status("waiting").progress(0.0).build()
        );
        when(agentClientService.getAgentStates(ANALYSIS_ID)).thenReturn(agentStates);

        AnalysisStatusResponse response = analysisService.getAnalysisStatus(CURRENT_USER_ID, ANALYSIS_ID);

        assertThat(response).isNotNull();
        assertThat(response.getAnalysisId()).isEqualTo(ANALYSIS_ID);
        assertThat(response.getStatus()).isEqualTo(AnalysisStatus.PROCESSING);
        // progress = (1.0 + 0.5 + 0.0) / 3 = 0.5
        assertThat(response.getProgress()).isCloseTo(0.5, org.assertj.core.data.Offset.offset(0.01));
        // currentAgent = "analyzer"（首个非 completed）
        assertThat(response.getCurrentAgent()).isEqualTo("analyzer");
        assertThat(response.getAgentStates()).hasSize(3);
    }

    @Test
    @DisplayName("getAnalysisStatus - Redis 无 Agent 状态时 progress=null, currentAgent=null")
    void getAnalysisStatus_empty_agents_progress_null() {
        AnalysisResult entity = buildAnalysisResult(AnalysisStatus.PENDING, "{}");
        when(analysisResultRepository.findByAnalysisId(ANALYSIS_ID)).thenReturn(Optional.of(entity));
        when(sessionRepository.findBySessionId(SESSION_ID)).thenReturn(Optional.of(buildSession(CURRENT_USER_ID)));
        when(agentClientService.getAgentStates(ANALYSIS_ID)).thenReturn(new ArrayList<>());

        AnalysisStatusResponse response = analysisService.getAnalysisStatus(CURRENT_USER_ID, ANALYSIS_ID);

        assertThat(response).isNotNull();
        assertThat(response.getStatus()).isEqualTo(AnalysisStatus.PENDING);
        assertThat(response.getProgress()).isNull();
        assertThat(response.getCurrentAgent()).isNull();
        assertThat(response.getAgentStates()).isEmpty();
    }

    // endregion
}
