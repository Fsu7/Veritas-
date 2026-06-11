package com.literatureassistant.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.literatureassistant.dto.common.AgentRequest;
import com.literatureassistant.dto.request.ReportRequest;
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
import java.util.Map;
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
 * AnalysisService.generateReport 单元测试（task26）。
 *
 * @author XH-202630 Literature Assistant
 * @since 0.4
 */
@ExtendWith(MockitoExtension.class)
class AnalysisServiceReportTest {

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
    private static final String SESSION_ID = "ses_report01";

    @BeforeEach
    void setUp() {
        SecurityContext context = SecurityContextHolder.createEmptyContext();
        context.setAuthentication(new UsernamePasswordAuthenticationToken(CURRENT_USER_ID, null, List.of()));
        SecurityContextHolder.setContext(context);

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

    private ReportRequest buildRequest(List<String> paperIds) {
        return ReportRequest.builder()
                .topic("LLM综述")
                .paperIds(paperIds)
                .build();
    }

    private PaperDetailResponse buildPaper(String paperId) {
        return PaperDetailResponse.builder()
                .paperId(paperId)
                .title("Paper " + paperId)
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
                .topic("LLM综述")
                .status(status)
                .createdAt(LocalDateTime.now())
                .build();
    }

    @Test
    @DisplayName("generateReport - 正常流程：3 篇论文 → 完整 7 步编排 + citations 非空")
    void generateReport_normal_flow_returns_task_response() {
        ReportRequest req = buildRequest(List.of("p1", "p2", "p3"));
        AnalysisResult pending = AnalysisResult.builder()
                .id(300L)
                .analysisId("anl_300")
                .sessionId(SESSION_ID)
                .type(AnalysisType.REPORT)
                .status(AnalysisStatus.PENDING)
                .result("{}")
                .createdAt(LocalDateTime.now())
                .build();
        when(userService.getProfile(CURRENT_USER_ID)).thenReturn(buildProfile());
        when(paperService.getPaperDetail(anyString())).thenAnswer(inv -> buildPaper(inv.getArgument(0)));
        when(sessionService.createSession(eq(CURRENT_USER_ID), any()))
                .thenReturn(SessionResponse.builder().sessionId(SESSION_ID).userId(CURRENT_USER_ID).build());
        when(analysisTransactionService.savePending(anyString(), eq(SESSION_ID), eq(AnalysisType.REPORT)))
                .thenReturn(pending);
        when(analysisTransactionService.completeAnalysis(eq(300L), any(AnalysisResultDTO.class)))
                .thenReturn(AnalysisTaskResponse.builder()
                        .analysisId("anl_300")
                        .status(AnalysisStatus.COMPLETED)
                        .message("分析完成")
                        .build());
        when(agentClientService.analyzePaper(any(AgentRequest.class)))
                .thenReturn(AnalysisResultDTO.builder()
                        .analysisId("anl_300")
                        .status(AnalysisStatus.COMPLETED)
                        .report("## 综述")
                        .citations(List.of(Map.of("index", 1, "paper_id", "p1")))
                        .build());

        AnalysisTaskResponse response = analysisService.generateReport(CURRENT_USER_ID, req);

        assertThat(response).isNotNull();
        assertThat(response.getStatus()).isEqualTo(AnalysisStatus.COMPLETED);
        verify(analysisTransactionService, times(1)).savePending(anyString(), eq(SESSION_ID), eq(AnalysisType.REPORT));
        verify(agentClientService, times(1)).analyzePaper(any(AgentRequest.class));
    }

    @Test
    @DisplayName("generateReport - paperId 不存在 → 抛 ResourceNotFoundException")
    void generateReport_paperId_not_found_throws404() {
        ReportRequest req = buildRequest(List.of("p1", "invalid"));
        when(userService.getProfile(CURRENT_USER_ID)).thenReturn(buildProfile());
        when(paperService.getPaperDetail("p1")).thenReturn(buildPaper("p1"));
        when(paperService.getPaperDetail("invalid"))
                .thenThrow(new ResourceNotFoundException("Paper", "invalid"));

        assertThatThrownBy(() -> analysisService.generateReport(CURRENT_USER_ID, req))
                .isInstanceOf(ResourceNotFoundException.class);
        verify(agentClientService, never()).analyzePaper(any(AgentRequest.class));
    }

    @Test
    @DisplayName("generateReport - AgentRequest.analysisType=REPORT + paperIds 包含全部论文ID")
    void generateReport_analysisType_is_REPORT() {
        ReportRequest req = buildRequest(List.of("p1", "p2", "p3", "p4", "p5"));
        AnalysisResult pending = AnalysisResult.builder()
                .id(301L)
                .analysisId("anl_301")
                .sessionId(SESSION_ID)
                .type(AnalysisType.REPORT)
                .status(AnalysisStatus.PENDING)
                .result("{}")
                .createdAt(LocalDateTime.now())
                .build();
        when(userService.getProfile(CURRENT_USER_ID)).thenReturn(buildProfile());
        when(paperService.getPaperDetail(anyString())).thenAnswer(inv -> buildPaper(inv.getArgument(0)));
        when(sessionService.createSession(eq(CURRENT_USER_ID), any()))
                .thenReturn(SessionResponse.builder().sessionId(SESSION_ID).userId(CURRENT_USER_ID).build());
        when(analysisTransactionService.savePending(anyString(), eq(SESSION_ID), eq(AnalysisType.REPORT)))
                .thenReturn(pending);
        when(analysisTransactionService.completeAnalysis(eq(301L), any(AnalysisResultDTO.class)))
                .thenReturn(AnalysisTaskResponse.builder()
                        .analysisId("anl_301")
                        .status(AnalysisStatus.COMPLETED)
                        .build());
        when(agentClientService.analyzePaper(any(AgentRequest.class)))
                .thenReturn(AnalysisResultDTO.builder()
                        .analysisId("anl_301")
                        .status(AnalysisStatus.COMPLETED)
                        .build());

        analysisService.generateReport(CURRENT_USER_ID, req);

        ArgumentCaptor<AgentRequest> captor = ArgumentCaptor.forClass(AgentRequest.class);
        verify(agentClientService).analyzePaper(captor.capture());
        assertThat(captor.getValue().getAnalysisType()).isEqualTo(AnalysisType.REPORT);
        assertThat(captor.getValue().getPaperIds()).containsExactly("p1", "p2", "p3", "p4", "p5");
    }

    @Test
    @DisplayName("generateReport - 复用他人 sessionId → 抛 BusinessException(403)")
    void generateReport_other_user_session_throws403() {
        ReportRequest req = ReportRequest.builder()
                .topic("LLM综述")
                .paperIds(List.of("p1"))
                .sessionId(SESSION_ID)
                .build();
        when(userService.getProfile(CURRENT_USER_ID)).thenReturn(buildProfile());
        when(paperService.getPaperDetail("p1")).thenReturn(buildPaper("p1"));
        when(sessionRepository.findBySessionId(SESSION_ID))
                .thenReturn(Optional.of(buildSession(OTHER_USER_ID, SessionStatus.ACTIVE)));

        assertThatThrownBy(() -> analysisService.generateReport(CURRENT_USER_ID, req))
                .isInstanceOf(BusinessException.class)
                .hasMessageContaining("他人会话");
    }

    @Test
    @DisplayName("generateReport - citations 为空时 log.warn 但不阻断")
    void generateReport_citations_empty_warns() {
        ReportRequest req = buildRequest(List.of("p1"));
        AnalysisResult pending = AnalysisResult.builder()
                .id(302L)
                .analysisId("anl_302")
                .sessionId(SESSION_ID)
                .type(AnalysisType.REPORT)
                .status(AnalysisStatus.PENDING)
                .result("{}")
                .createdAt(LocalDateTime.now())
                .build();
        when(userService.getProfile(CURRENT_USER_ID)).thenReturn(buildProfile());
        when(paperService.getPaperDetail("p1")).thenReturn(buildPaper("p1"));
        when(sessionService.createSession(eq(CURRENT_USER_ID), any()))
                .thenReturn(SessionResponse.builder().sessionId(SESSION_ID).userId(CURRENT_USER_ID).build());
        when(analysisTransactionService.savePending(anyString(), eq(SESSION_ID), eq(AnalysisType.REPORT)))
                .thenReturn(pending);
        when(analysisTransactionService.completeAnalysis(eq(302L), any(AnalysisResultDTO.class)))
                .thenReturn(AnalysisTaskResponse.builder()
                        .analysisId("anl_302")
                        .status(AnalysisStatus.COMPLETED)
                        .build());
        when(agentClientService.analyzePaper(any(AgentRequest.class)))
                .thenReturn(AnalysisResultDTO.builder()
                        .analysisId("anl_302")
                        .status(AnalysisStatus.COMPLETED)
                        .report("## Report")
                        .citations(null)  // 引用列表为空
                        .build());

        AnalysisTaskResponse response = analysisService.generateReport(CURRENT_USER_ID, req);

        // 即使 citations 为空，流程仍正常返回
        assertThat(response).isNotNull();
        assertThat(response.getStatus()).isEqualTo(AnalysisStatus.COMPLETED);
    }

    @Test
    @DisplayName("generateReport - 复用本人 ACTIVE sessionId → 复用成功")
    void generateReport_reuse_session() {
        ReportRequest req = ReportRequest.builder()
                .topic("LLM综述")
                .paperIds(List.of("p1"))
                .sessionId(SESSION_ID)
                .build();
        AnalysisResult pending = AnalysisResult.builder()
                .id(303L)
                .analysisId("anl_303")
                .sessionId(SESSION_ID)
                .type(AnalysisType.REPORT)
                .status(AnalysisStatus.PENDING)
                .result("{}")
                .createdAt(LocalDateTime.now())
                .build();
        when(userService.getProfile(CURRENT_USER_ID)).thenReturn(buildProfile());
        when(paperService.getPaperDetail("p1")).thenReturn(buildPaper("p1"));
        when(sessionRepository.findBySessionId(SESSION_ID))
                .thenReturn(Optional.of(buildSession(CURRENT_USER_ID, SessionStatus.ACTIVE)));
        when(analysisTransactionService.savePending(anyString(), eq(SESSION_ID), eq(AnalysisType.REPORT)))
                .thenReturn(pending);
        when(analysisTransactionService.completeAnalysis(eq(303L), any(AnalysisResultDTO.class)))
                .thenReturn(AnalysisTaskResponse.builder()
                        .analysisId("anl_303")
                        .status(AnalysisStatus.COMPLETED)
                        .build());
        when(agentClientService.analyzePaper(any(AgentRequest.class)))
                .thenReturn(AnalysisResultDTO.builder()
                        .analysisId("anl_303")
                        .status(AnalysisStatus.COMPLETED)
                        .build());

        analysisService.generateReport(CURRENT_USER_ID, req);

        verify(sessionService, never()).createSession(anyString(), any());
    }
}
