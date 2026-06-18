package com.literatureassistant.service;

import com.literatureassistant.cache.CacheEvictionHelper;
import com.literatureassistant.dto.common.PageResponse;
import com.literatureassistant.dto.request.SessionCreateRequest;
import com.literatureassistant.dto.response.SessionDetailResponse;
import com.literatureassistant.dto.response.SessionResponse;
import com.literatureassistant.entity.Session;
import com.literatureassistant.enums.SessionStatus;
import com.literatureassistant.exception.AuthenticationException;
import com.literatureassistant.exception.BusinessException;
import com.literatureassistant.exception.ResourceNotFoundException;
import com.literatureassistant.mapper.SessionMapper;
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
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContext;
import org.springframework.security.core.context.SecurityContextHolder;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class SessionServiceTest {

    @InjectMocks
    private SessionService sessionService;

    @Mock
    private SessionRepository sessionRepository;

    @Mock
    private SessionMapper sessionMapper;

    @Mock
    private AnalysisResultRepository analysisResultRepository;

    @Mock
    private CacheEvictionHelper cacheEvictionHelper;

    private static final String CURRENT_USER_ID = "usr_001";
    private static final String OTHER_USER_ID = "usr_002";
    private static final String SESSION_ID = "ses_a1b2c3d4";

    @BeforeEach
    void setUp() {
        SecurityContext context = SecurityContextHolder.createEmptyContext();
        context.setAuthentication(new UsernamePasswordAuthenticationToken(CURRENT_USER_ID, null, List.of()));
        SecurityContextHolder.setContext(context);
    }

    @AfterEach
    void tearDown() {
        SecurityContextHolder.clearContext();
    }

    private Session buildSession(String userId, SessionStatus status) {
        return Session.builder()
                .id(1L)
                .sessionId(SESSION_ID)
                .userId(userId)
                .topic("Multi-Agent协同决策")
                .status(status)
                .createdAt(LocalDateTime.of(2026, 5, 23, 10, 0, 0))
                .build();
    }

    @Test
    @DisplayName("createSession - 正常返回SessionResponse，sessionId以ses_开头，status=active")
    void createSession_normal_returnsResponseWithSesPrefix() {
        SessionCreateRequest request = SessionCreateRequest.builder()
                .topic("Multi-Agent协同决策")
                .build();
        LocalDateTime fixedNow = LocalDateTime.of(2026, 5, 23, 10, 0, 0);
        when(sessionRepository.save(any(Session.class))).thenAnswer(inv -> {
            Session arg = inv.getArgument(0);
            arg.setCreatedAt(fixedNow);
            return arg;
        });
        when(sessionMapper.toResponse(any(Session.class))).thenAnswer(inv -> {
            Session arg = inv.getArgument(0);
            return SessionResponse.builder()
                    .sessionId(arg.getSessionId())
                    .userId(arg.getUserId())
                    .topic(arg.getTopic())
                    .status(arg.getStatus().getDbValue())
                    .createdAt(arg.getCreatedAt())
                    .build();
        });

        SessionResponse response = sessionService.createSession(CURRENT_USER_ID, request);

        assertThat(response.getSessionId()).startsWith("ses_");
        assertThat(response.getSessionId()).hasSize(12);
        assertThat(response.getUserId()).isEqualTo(CURRENT_USER_ID);
        assertThat(response.getTopic()).isEqualTo("Multi-Agent协同决策");
        assertThat(response.getStatus()).isEqualTo("active");
        assertThat(response.getCreatedAt()).isEqualTo(fixedNow);
        verify(sessionMapper, times(1)).toResponse(any(Session.class));
    }

    @Test
    @DisplayName("createSession - userId为null抛401 AuthenticationException")
    void createSession_nullUserId_throws401() {
        SessionCreateRequest request = SessionCreateRequest.builder().topic("Test").build();

        assertThatThrownBy(() -> sessionService.createSession(null, request))
                .isInstanceOf(AuthenticationException.class)
                .hasMessageContaining("未认证");
    }

    @Test
    @DisplayName("listSessions - 分页正常返回PageResponse<SessionResponse>")
    void listSessions_normal_returnsPageResponse() {
        List<Session> sessions = List.of(
                buildSession(CURRENT_USER_ID, SessionStatus.ACTIVE),
                buildSession(CURRENT_USER_ID, SessionStatus.ACTIVE)
        );
        Page<Session> page = new PageImpl<>(sessions, PageRequest.of(0, 10), 2);
        when(sessionRepository.findByUserIdOrderByCreatedAtDesc(
                org.mockito.ArgumentMatchers.eq(CURRENT_USER_ID),
                org.mockito.ArgumentMatchers.any()))
                .thenReturn(page);
        when(sessionMapper.toResponse(any(Session.class))).thenAnswer(inv -> {
            Session arg = inv.getArgument(0);
            return SessionResponse.builder()
                    .sessionId(arg.getSessionId())
                    .status(arg.getStatus().getDbValue())
                    .build();
        });

        PageResponse<SessionResponse> response = sessionService.listSessions(CURRENT_USER_ID, 1, 10);

        assertThat(response.getItems()).hasSize(2);
        assertThat(response.getTotal()).isEqualTo(2L);
        assertThat(response.getPage()).isEqualTo(1);
        assertThat(response.getSize()).isEqualTo(10);
        assertThat(response.getItems().get(0).getStatus()).isEqualTo("active");
    }

    @Test
    @DisplayName("listSessions - page<1被修正为1")
    void listSessions_pageLessThanOne_clampsToOne() {
        Page<Session> emptyPage = new PageImpl<>(List.of(), PageRequest.of(0, 10), 0);
        when(sessionRepository.findByUserIdOrderByCreatedAtDesc(
                org.mockito.ArgumentMatchers.eq(CURRENT_USER_ID),
                org.mockito.ArgumentMatchers.any()))
                .thenReturn(emptyPage);

        sessionService.listSessions(CURRENT_USER_ID, 0, 10);

        ArgumentCaptor<PageRequest> captor = ArgumentCaptor.forClass(PageRequest.class);
        verify(sessionRepository).findByUserIdOrderByCreatedAtDesc(
                org.mockito.ArgumentMatchers.eq(CURRENT_USER_ID), captor.capture());
        assertThat(captor.getValue().getPageNumber()).isEqualTo(0);
    }

    @Test
    @DisplayName("listSessions - size>100被修正为100")
    void listSessions_sizeExceedsMax_clampsTo100() {
        Page<Session> emptyPage = new PageImpl<>(List.of(), PageRequest.of(0, 100), 0);
        when(sessionRepository.findByUserIdOrderByCreatedAtDesc(
                org.mockito.ArgumentMatchers.eq(CURRENT_USER_ID),
                org.mockito.ArgumentMatchers.any()))
                .thenReturn(emptyPage);

        sessionService.listSessions(CURRENT_USER_ID, 1, 200);

        ArgumentCaptor<PageRequest> captor = ArgumentCaptor.forClass(PageRequest.class);
        verify(sessionRepository).findByUserIdOrderByCreatedAtDesc(
                org.mockito.ArgumentMatchers.eq(CURRENT_USER_ID), captor.capture());
        assertThat(captor.getValue().getPageSize()).isEqualTo(100);
    }

    @Test
    @DisplayName("getSessionDetail - 正常返回SessionDetailResponse（含analysisCount）")
    void getSessionDetail_normal_returnsDetailResponseWithAnalysisCount() {
        Session session = buildSession(CURRENT_USER_ID, SessionStatus.ACTIVE);
        when(sessionRepository.findBySessionId(SESSION_ID)).thenReturn(Optional.of(session));
        when(sessionMapper.toDetailResponse(session)).thenReturn(
                SessionDetailResponse.builder()
                        .sessionId(SESSION_ID)
                        .userId(CURRENT_USER_ID)
                        .topic("Multi-Agent协同决策")
                        .status("active")
                        .createdAt(session.getCreatedAt())
                        .build()
        );
        when(analysisResultRepository.countBySessionId(SESSION_ID)).thenReturn(3L);

        SessionDetailResponse response = sessionService.getSessionDetail(SESSION_ID);

        assertThat(response.getSessionId()).isEqualTo(SESSION_ID);
        assertThat(response.getUserId()).isEqualTo(CURRENT_USER_ID);
        assertThat(response.getStatus()).isEqualTo("active");
        assertThat(response.getAnalysisCount()).isEqualTo(3);
        verify(analysisResultRepository, times(1)).countBySessionId(SESSION_ID);
    }

    @Test
    @DisplayName("getSessionDetail - sessionId不存在抛404")
    void getSessionDetail_sessionNotFound_throws404() {
        when(sessionRepository.findBySessionId("ses_unknown")).thenReturn(Optional.empty());

        assertThatThrownBy(() -> sessionService.getSessionDetail("ses_unknown"))
                .isInstanceOf(ResourceNotFoundException.class);
    }

    // 修复 B-004: 数据隔离校验已上移到 Controller（validateSessionAccess），
    // Service 层 getSessionDetail 不再内部校验。原 getSessionDetail_dataIsolationViolation_throws403
    // 测试已删除，数据隔离测试由 SessionControllerTest 和 Jm5IntegrationTest 覆盖。

    @Test
    @DisplayName("updateStatus - ACTIVE→COMPLETED 正常更新save")
    void updateStatus_activeToCompleted_savesNewStatus() {
        Session session = buildSession(CURRENT_USER_ID, SessionStatus.ACTIVE);
        when(sessionRepository.findBySessionId(SESSION_ID)).thenReturn(Optional.of(session));
        when(sessionRepository.save(any(Session.class))).thenAnswer(inv -> inv.getArgument(0));

        sessionService.updateStatus(SESSION_ID, SessionStatus.COMPLETED);

        ArgumentCaptor<Session> captor = ArgumentCaptor.forClass(Session.class);
        verify(sessionRepository, times(1)).save(captor.capture());
        assertThat(captor.getValue().getStatus()).isEqualTo(SessionStatus.COMPLETED);
    }

    @Test
    @DisplayName("updateStatus - 相同状态抛 400 SAME_STATUS_NOOP（task18 状态机校验）")
    void updateStatus_sameStatus_throws400() {
        Session session = buildSession(CURRENT_USER_ID, SessionStatus.ACTIVE);
        when(sessionRepository.findBySessionId(SESSION_ID)).thenReturn(Optional.of(session));

        assertThatThrownBy(() -> sessionService.updateStatus(SESSION_ID, SessionStatus.ACTIVE))
                .isInstanceOf(BusinessException.class)
                .hasFieldOrPropertyWithValue("code", 400)
                .hasFieldOrPropertyWithValue("errorKey", "SAME_STATUS_NOOP")
                .hasMessageContaining("会话状态已是目标状态");

        verify(sessionRepository, never()).save(any(Session.class));
    }

    @Test
    @DisplayName("updateStatus - sessionId不存在抛404")
    void updateStatus_sessionNotFound_throws404() {
        when(sessionRepository.findBySessionId("ses_unknown")).thenReturn(Optional.empty());

        assertThatThrownBy(() -> sessionService.updateStatus("ses_unknown", SessionStatus.COMPLETED))
                .isInstanceOf(ResourceNotFoundException.class);
    }

    @Test
    @DisplayName("updateStatus - 越权抛403")
    void updateStatus_dataIsolationViolation_throws403() {
        Session otherSession = buildSession(OTHER_USER_ID, SessionStatus.ACTIVE);
        when(sessionRepository.findBySessionId(SESSION_ID)).thenReturn(Optional.of(otherSession));

        assertThatThrownBy(() -> sessionService.updateStatus(SESSION_ID, SessionStatus.COMPLETED))
                .isInstanceOf(BusinessException.class)
                .hasFieldOrPropertyWithValue("code", 403);
    }

    @Test
    @DisplayName("updateStatus - 非法状态转换抛 400 INVALID_STATUS_TRANSITION")
    void updateStatus_invalidTransition_throws400() {
        Session session = buildSession(CURRENT_USER_ID, SessionStatus.COMPLETED);
        when(sessionRepository.findBySessionId(SESSION_ID)).thenReturn(Optional.of(session));

        assertThatThrownBy(() -> sessionService.updateStatus(SESSION_ID, SessionStatus.ACTIVE))
                .isInstanceOf(BusinessException.class)
                .hasFieldOrPropertyWithValue("code", 400)
                .hasFieldOrPropertyWithValue("errorKey", "INVALID_STATUS_TRANSITION")
                .hasMessageContaining("非法的状态转换");

        verify(sessionRepository, never()).save(any(Session.class));
    }

    @Test
    @DisplayName("deleteSession - 正常删除（级联由FK ON DELETE CASCADE）")
    void deleteSession_normal_callsDelete() {
        Session session = buildSession(CURRENT_USER_ID, SessionStatus.ACTIVE);
        when(sessionRepository.findBySessionId(SESSION_ID)).thenReturn(Optional.of(session));

        sessionService.deleteSession(SESSION_ID);

        verify(sessionRepository, times(1)).delete(session);
    }

    @Test
    @DisplayName("deleteSession - sessionId不存在抛404")
    void deleteSession_sessionNotFound_throws404() {
        when(sessionRepository.findBySessionId("ses_unknown")).thenReturn(Optional.empty());

        assertThatThrownBy(() -> sessionService.deleteSession("ses_unknown"))
                .isInstanceOf(ResourceNotFoundException.class);
    }

    @Test
    @DisplayName("deleteSession - 越权抛403")
    void deleteSession_dataIsolationViolation_throws403() {
        Session otherSession = buildSession(OTHER_USER_ID, SessionStatus.ACTIVE);
        when(sessionRepository.findBySessionId(SESSION_ID)).thenReturn(Optional.of(otherSession));

        assertThatThrownBy(() -> sessionService.deleteSession(SESSION_ID))
                .isInstanceOf(BusinessException.class)
                .hasFieldOrPropertyWithValue("code", 403);
    }

    // 修复 B-004: 数据隔离校验已上移到 Controller（validateSessionAccess），
    // Service 层 getSessionDetail 不再内部校验。原 getSessionDetail_unauthenticated_throws401
    // 测试已删除，认证校验由 Controller 层保证。
}
