package com.literatureassistant.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.literatureassistant.dto.common.AgentRequest;
import com.literatureassistant.dto.common.UserProfileDTO;
import com.literatureassistant.dto.request.CompareRequest;
import com.literatureassistant.dto.request.PaperAnalysisRequest;
import com.literatureassistant.dto.response.AnalysisResultDTO;
import com.literatureassistant.dto.response.AnalysisTaskResponse;
import com.literatureassistant.dto.response.PaperDetailResponse;
import com.literatureassistant.dto.response.ProfileResponse;
import com.literatureassistant.dto.response.SessionResponse;
import com.literatureassistant.entity.AnalysisResult;
import com.literatureassistant.entity.Session;
import com.literatureassistant.enums.AnalysisStatus;
import com.literatureassistant.enums.AnalysisType;
import com.literatureassistant.enums.SessionStatus;
import com.literatureassistant.exception.BusinessException;
import com.literatureassistant.exception.ResourceNotFoundException;
import com.literatureassistant.repository.AnalysisResultRepository;
import com.literatureassistant.repository.SessionRepository;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContext;
import org.springframework.security.core.context.SecurityContextHolder;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * AnalysisService 单元测试。
 * <p>task24 重构后：使用 {@code @Mock AnalysisTransactionService} 替代原 self 反射调用。
 *
 * @author XH-202630 Literature Assistant
 */
@ExtendWith(MockitoExtension.class)
class AnalysisServiceTest {

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
    private static final String PAPER_ID = "arxiv_2024_001";

    @BeforeEach
    void setUp() {
        SecurityContext context = SecurityContextHolder.createEmptyContext();
        context.setAuthentication(new UsernamePasswordAuthenticationToken(CURRENT_USER_ID, null, List.of()));
        SecurityContextHolder.setContext(context);

        // @InjectMocks 不会注入 final 字段或 @Autowired 字段，需要手动注入 objectMapper
        try {
            java.lang.reflect.Field omField = AnalysisService.class.getDeclaredField("objectMapper");
            omField.setAccessible(true);
            omField.set(analysisService, objectMapper);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    @AfterEach
    void tearDown() {
        SecurityContextHolder.clearContext();
    }

    private PaperAnalysisRequest buildRequest() {
        return PaperAnalysisRequest.builder()
                .topic("Multi-Agent协同决策")
                .paperId(PAPER_ID)
                .build();
    }

    private PaperDetailResponse buildPaper(String paperId) {
        return PaperDetailResponse.builder()
                .paperId(paperId)
                .title("Attention Is All You Need")
                .build();
    }

    private ProfileResponse buildProfile() {
        return ProfileResponse.builder()
                .userId(CURRENT_USER_ID)
                .educationLevel("master")
                .researchField("NLP")
                .knowledgeLevel("intermediate")
                .preferredStyle("balanced")
                .build();
    }

    private Session buildSession(String userId, SessionStatus status) {
        return Session.builder()
                .id(1L)
                .sessionId(SESSION_ID)
                .userId(userId)
                .topic("Multi-Agent")
                .status(status)
                .createdAt(LocalDateTime.of(2026, 6, 1, 10, 0, 0))
                .build();
    }

    private AnalysisResult buildPendingEntity(Long id, AnalysisType type) {
        return AnalysisResult.builder()
                .id(id)
                .analysisId("anl_" + id)
                .sessionId(SESSION_ID)
                .type(type)
                .status(AnalysisStatus.PENDING)
                .result("{}")
                .createdAt(LocalDateTime.now())
                .build();
    }

    // region analyzePaper (task22/23 既有测试)

    @Test
    @DisplayName("analyzePaper - 正常流程：7 步执行，状态 PENDING→COMPLETED")
    void analyzeService_normal_completes_analysisResult() {
        AnalysisResult savedEntity = buildPendingEntity(100L, AnalysisType.PAPER_ANALYSIS);
        when(userService.getProfile(CURRENT_USER_ID)).thenReturn(buildProfile());
        when(paperService.getPaperDetail(PAPER_ID)).thenReturn(buildPaper(PAPER_ID));
        when(sessionService.createSession(eq(CURRENT_USER_ID), any()))
                .thenReturn(SessionResponse.builder().sessionId(SESSION_ID).userId(CURRENT_USER_ID).build());
        when(analysisTransactionService.savePending(anyString(), eq(SESSION_ID), eq(AnalysisType.PAPER_ANALYSIS)))
                .thenReturn(savedEntity);
        when(analysisTransactionService.completeAnalysis(eq(100L), any(AnalysisResultDTO.class)))
                .thenReturn(AnalysisTaskResponse.builder()
                        .analysisId("anl_100")
                        .status(AnalysisStatus.COMPLETED)
                        .message("分析完成")
                        .createdAt(LocalDateTime.now())
                        .build());
        when(agentClientService.analyzePaper(any(AgentRequest.class)))
                .thenReturn(AnalysisResultDTO.builder()
                        .analysisId("anl_100")
                        .status(AnalysisStatus.COMPLETED)
                        .report("## Report")
                        .build());

        AnalysisTaskResponse response = analysisService.analyzePaper(CURRENT_USER_ID, buildRequest());

        assertThat(response).isNotNull();
        assertThat(response.getStatus()).isEqualTo(AnalysisStatus.COMPLETED);
        assertThat(response.getMessage()).isEqualTo("分析完成");
        verify(analysisTransactionService, times(1)).savePending(anyString(), eq(SESSION_ID), eq(AnalysisType.PAPER_ANALYSIS));
        verify(analysisTransactionService, times(1)).completeAnalysis(eq(100L), any(AnalysisResultDTO.class));
        verify(agentClientService, times(1)).analyzePaper(any(AgentRequest.class));
    }

    @Test
    @DisplayName("analyzePaper - AI 返回 degraded → status=COMPLETED + degraded=true")
    void analyzeService_aiFailure_marks_degraded() {
        AnalysisResult savedEntity = buildPendingEntity(101L, AnalysisType.PAPER_ANALYSIS);
        when(userService.getProfile(CURRENT_USER_ID)).thenReturn(buildProfile());
        when(paperService.getPaperDetail(PAPER_ID)).thenReturn(buildPaper(PAPER_ID));
        when(sessionService.createSession(eq(CURRENT_USER_ID), any()))
                .thenReturn(SessionResponse.builder().sessionId(SESSION_ID).userId(CURRENT_USER_ID).build());
        when(analysisTransactionService.savePending(anyString(), eq(SESSION_ID), eq(AnalysisType.PAPER_ANALYSIS)))
                .thenReturn(savedEntity);
        when(analysisTransactionService.completeAnalysis(eq(101L), any(AnalysisResultDTO.class)))
                .thenAnswer(inv -> {
                    AnalysisResultDTO r = inv.getArgument(1);
                    return AnalysisTaskResponse.builder()
                            .analysisId("anl_101")
                            .status(AnalysisStatus.COMPLETED)
                            .message("分析完成（降级）：" + r.getDegradedReason())
                            .createdAt(LocalDateTime.now())
                            .build();
                });
        when(agentClientService.analyzePaper(any(AgentRequest.class)))
                .thenReturn(AnalysisResultDTO.builder()
                        .analysisId("anl_101")
                        .degraded(true)
                        .degradedReason("AI服务暂时不可用")
                        .build());

        AnalysisTaskResponse response = analysisService.analyzePaper(CURRENT_USER_ID, buildRequest());

        assertThat(response).isNotNull();
        assertThat(response.getStatus()).isEqualTo(AnalysisStatus.COMPLETED);
        assertThat(response.getMessage()).contains("降级");
    }

    @Test
    @DisplayName("analyzePaper - 复用他人 sessionId → 抛 BusinessException(403)")
    void analyzeService_sessionIsolation_throws403() {
        PaperAnalysisRequest req = PaperAnalysisRequest.builder()
                .topic("Multi-Agent")
                .paperId(PAPER_ID)
                .sessionId(SESSION_ID)
                .build();
        when(userService.getProfile(CURRENT_USER_ID)).thenReturn(buildProfile());
        when(paperService.getPaperDetail(PAPER_ID)).thenReturn(buildPaper(PAPER_ID));
        when(sessionRepository.findBySessionId(SESSION_ID))
                .thenReturn(Optional.of(buildSession(OTHER_USER_ID, SessionStatus.ACTIVE)));

        assertThatThrownBy(() -> analysisService.analyzePaper(CURRENT_USER_ID, req))
                .isInstanceOf(BusinessException.class)
                .hasMessageContaining("他人会话");
    }

    @Test
    @DisplayName("analyzePaper - 论文不存在 → 抛 ResourceNotFoundException(404)")
    void analyzeService_paperNotFound_throws404() {
        when(userService.getProfile(CURRENT_USER_ID)).thenReturn(buildProfile());
        when(paperService.getPaperDetail("invalid_paper"))
                .thenThrow(new ResourceNotFoundException("Paper", "invalid_paper"));

        PaperAnalysisRequest req = PaperAnalysisRequest.builder()
                .topic("test")
                .paperId("invalid_paper")
                .build();

        assertThatThrownBy(() -> analysisService.analyzePaper(CURRENT_USER_ID, req))
                .isInstanceOf(ResourceNotFoundException.class);
        // AI 永远不被调用
        verify(agentClientService, never()).analyzePaper(any(AgentRequest.class));
    }

    @Test
    @DisplayName("analyzePaper - 用户画像缺失时使用默认画像")
    void analyzeService_noProfile_usesDefault() {
        AnalysisResult savedEntity = buildPendingEntity(102L, AnalysisType.PAPER_ANALYSIS);
        when(userService.getProfile(CURRENT_USER_ID))
                .thenThrow(new ResourceNotFoundException("UserProfile", CURRENT_USER_ID));
        when(paperService.getPaperDetail(PAPER_ID)).thenReturn(buildPaper(PAPER_ID));
        when(sessionService.createSession(eq(CURRENT_USER_ID), any()))
                .thenReturn(SessionResponse.builder().sessionId(SESSION_ID).userId(CURRENT_USER_ID).build());
        when(analysisTransactionService.savePending(anyString(), eq(SESSION_ID), eq(AnalysisType.PAPER_ANALYSIS)))
                .thenReturn(savedEntity);
        when(analysisTransactionService.completeAnalysis(eq(102L), any(AnalysisResultDTO.class)))
                .thenReturn(AnalysisTaskResponse.builder()
                        .analysisId("anl_102")
                        .status(AnalysisStatus.COMPLETED)
                        .message("分析完成")
                        .build());
        when(agentClientService.analyzePaper(any(AgentRequest.class)))
                .thenReturn(AnalysisResultDTO.builder()
                        .analysisId("anl_102")
                        .status(AnalysisStatus.COMPLETED)
                        .build());

        AnalysisTaskResponse response = analysisService.analyzePaper(CURRENT_USER_ID, buildRequest());

        assertThat(response).isNotNull();
        assertThat(response.getStatus()).isEqualTo(AnalysisStatus.COMPLETED);
        // 验证 AgentRequest 携带默认画像
        ArgumentCaptor<AgentRequest> captor = ArgumentCaptor.forClass(AgentRequest.class);
        verify(agentClientService).analyzePaper(captor.capture());
        assertThat(captor.getValue().getUserProfile().getEducationLevel().getDbValue()).isEqualTo("master");
        assertThat(captor.getValue().getUserProfile().getKnowledgeLevel().getDbValue()).isEqualTo("intermediate");
    }

    @Test
    @DisplayName("analyzePaper - 复用本人 ACTIVE sessionId → 复用成功")
    void analyzeService_reuseOwnSession() {
        PaperAnalysisRequest req = PaperAnalysisRequest.builder()
                .topic("Multi-Agent")
                .paperId(PAPER_ID)
                .sessionId(SESSION_ID)
                .build();
        AnalysisResult savedEntity = buildPendingEntity(103L, AnalysisType.PAPER_ANALYSIS);
        when(userService.getProfile(CURRENT_USER_ID)).thenReturn(buildProfile());
        when(paperService.getPaperDetail(PAPER_ID)).thenReturn(buildPaper(PAPER_ID));
        when(sessionRepository.findBySessionId(SESSION_ID))
                .thenReturn(Optional.of(buildSession(CURRENT_USER_ID, SessionStatus.ACTIVE)));
        when(analysisTransactionService.savePending(anyString(), eq(SESSION_ID), eq(AnalysisType.PAPER_ANALYSIS)))
                .thenReturn(savedEntity);
        when(analysisTransactionService.completeAnalysis(eq(103L), any(AnalysisResultDTO.class)))
                .thenReturn(AnalysisTaskResponse.builder()
                        .analysisId("anl_103")
                        .status(AnalysisStatus.COMPLETED)
                        .build());
        when(agentClientService.analyzePaper(any(AgentRequest.class)))
                .thenReturn(AnalysisResultDTO.builder()
                        .analysisId("anl_103")
                        .status(AnalysisStatus.COMPLETED)
                        .build());

        AnalysisTaskResponse response = analysisService.analyzePaper(CURRENT_USER_ID, req);

        assertThat(response).isNotNull();
        // sessionService.createSession 不应被调用
        verify(sessionService, never()).createSession(anyString(), any());
    }

    // endregion

    // region comparePapers (task25 新增)

    @Test
    @DisplayName("comparePapers - 正常流程：3 篇论文 → 编排完整执行")
    void comparePapers_normal_flow_completes() {
        CompareRequest req = CompareRequest.builder()
                .topic("对比多Agent框架")
                .paperIds(List.of("p1", "p2", "p3"))
                .build();
        AnalysisResult pending = buildPendingEntity(200L, AnalysisType.COMPARE);
        when(userService.getProfile(CURRENT_USER_ID)).thenReturn(buildProfile());
        when(paperService.getPaperDetail("p1")).thenReturn(buildPaper("p1"));
        when(paperService.getPaperDetail("p2")).thenReturn(buildPaper("p2"));
        when(paperService.getPaperDetail("p3")).thenReturn(buildPaper("p3"));
        when(sessionService.createSession(eq(CURRENT_USER_ID), any()))
                .thenReturn(SessionResponse.builder().sessionId(SESSION_ID).userId(CURRENT_USER_ID).build());
        when(analysisTransactionService.savePending(anyString(), eq(SESSION_ID), eq(AnalysisType.COMPARE)))
                .thenReturn(pending);
        when(analysisTransactionService.completeAnalysis(eq(200L), any(AnalysisResultDTO.class)))
                .thenReturn(AnalysisTaskResponse.builder()
                        .analysisId("anl_200")
                        .status(AnalysisStatus.COMPLETED)
                        .message("分析完成")
                        .build());
        when(agentClientService.analyzePaper(any(AgentRequest.class)))
                .thenReturn(AnalysisResultDTO.builder()
                        .analysisId("anl_200")
                        .status(AnalysisStatus.COMPLETED)
                        .build());

        AnalysisTaskResponse response = analysisService.comparePapers(CURRENT_USER_ID, req);

        assertThat(response).isNotNull();
        assertThat(response.getStatus()).isEqualTo(AnalysisStatus.COMPLETED);
        verify(analysisTransactionService).savePending(anyString(), eq(SESSION_ID), eq(AnalysisType.COMPARE));
    }

    @Test
    @DisplayName("comparePapers - 任一 paperId 不存在 → 404，不进入 AI")
    void comparePapers_paperId_not_found_throws404() {
        CompareRequest req = CompareRequest.builder()
                .topic("对比")
                .paperIds(List.of("p1", "invalid"))
                .build();
        when(userService.getProfile(CURRENT_USER_ID)).thenReturn(buildProfile());
        when(paperService.getPaperDetail("p1")).thenReturn(buildPaper("p1"));
        when(paperService.getPaperDetail("invalid"))
                .thenThrow(new ResourceNotFoundException("Paper", "invalid"));

        assertThatThrownBy(() -> analysisService.comparePapers(CURRENT_USER_ID, req))
                .isInstanceOf(ResourceNotFoundException.class);
        verify(agentClientService, never()).analyzePaper(any(AgentRequest.class));
    }

    @Test
    @DisplayName("comparePapers - 他人 sessionId → 403")
    void comparePapers_other_user_session_throws403() {
        CompareRequest req = CompareRequest.builder()
                .topic("对比")
                .paperIds(List.of("p1", "p2"))
                .sessionId(SESSION_ID)
                .build();
        when(userService.getProfile(CURRENT_USER_ID)).thenReturn(buildProfile());
        when(paperService.getPaperDetail("p1")).thenReturn(buildPaper("p1"));
        when(paperService.getPaperDetail("p2")).thenReturn(buildPaper("p2"));
        when(sessionRepository.findBySessionId(SESSION_ID))
                .thenReturn(Optional.of(buildSession(OTHER_USER_ID, SessionStatus.ACTIVE)));

        assertThatThrownBy(() -> analysisService.comparePapers(CURRENT_USER_ID, req))
                .isInstanceOf(BusinessException.class)
                .hasMessageContaining("他人会话");
    }

    @Test
    @DisplayName("comparePapers - AgentRequest.paperIds 包含所有论文ID + analysisType=COMPARE")
    void comparePapers_agentRequest_contains_all_paperIds() {
        CompareRequest req = CompareRequest.builder()
                .topic("对比")
                .paperIds(List.of("p1", "p2", "p3", "p4"))
                .build();
        AnalysisResult pending = buildPendingEntity(201L, AnalysisType.COMPARE);
        when(userService.getProfile(CURRENT_USER_ID)).thenReturn(buildProfile());
        when(paperService.getPaperDetail(anyString())).thenAnswer(inv -> buildPaper(inv.getArgument(0)));
        when(sessionService.createSession(eq(CURRENT_USER_ID), any()))
                .thenReturn(SessionResponse.builder().sessionId(SESSION_ID).userId(CURRENT_USER_ID).build());
        when(analysisTransactionService.savePending(anyString(), eq(SESSION_ID), eq(AnalysisType.COMPARE)))
                .thenReturn(pending);
        when(analysisTransactionService.completeAnalysis(eq(201L), any(AnalysisResultDTO.class)))
                .thenReturn(AnalysisTaskResponse.builder()
                        .analysisId("anl_201")
                        .status(AnalysisStatus.COMPLETED)
                        .build());
        when(agentClientService.analyzePaper(any(AgentRequest.class)))
                .thenReturn(AnalysisResultDTO.builder()
                        .analysisId("anl_201")
                        .status(AnalysisStatus.COMPLETED)
                        .build());

        analysisService.comparePapers(CURRENT_USER_ID, req);

        ArgumentCaptor<AgentRequest> captor = ArgumentCaptor.forClass(AgentRequest.class);
        verify(agentClientService).analyzePaper(captor.capture());
        assertThat(captor.getValue().getAnalysisType()).isEqualTo(AnalysisType.COMPARE);
        assertThat(captor.getValue().getPaperIds()).containsExactly("p1", "p2", "p3", "p4");
    }

    // endregion
}
