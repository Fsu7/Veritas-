package com.literatureassistant.service;

import com.literatureassistant.cache.CacheEvictionHelper;
import com.literatureassistant.entity.Session;
import com.literatureassistant.enums.SessionStatus;
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
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class SessionStateMachineTest {

    @Mock
    private SessionRepository sessionRepository;

    @Mock
    private SessionMapper sessionMapper;

    @Mock
    private AnalysisResultRepository analysisResultRepository;

    @Mock
    private CacheEvictionHelper cacheEvictionHelper;

    private SessionService sessionService;

    private static final String SESSION_ID = "ses_a1b2c3d4";

    @BeforeEach
    void setUp() {
        sessionService = new SessionService(sessionRepository, sessionMapper, analysisResultRepository, cacheEvictionHelper);
        SecurityContext context = SecurityContextHolder.createEmptyContext();
        context.setAuthentication(new UsernamePasswordAuthenticationToken("usr_001", null, List.of()));
        SecurityContextHolder.setContext(context);
    }

    @AfterEach
    void tearDown() {
        SecurityContextHolder.clearContext();
    }

    private Session buildSession(SessionStatus status) {
        return Session.builder()
                .id(1L)
                .sessionId(SESSION_ID)
                .userId("usr_001")
                .topic("Test")
                .status(status)
                .createdAt(LocalDateTime.of(2026, 5, 23, 10, 0, 0))
                .build();
    }

    @Test
    @DisplayName("markAsCompleted - ACTIVE→COMPLETED 合法")
    void markAsCompleted_activeToCompleted_succeeds() {
        Session session = buildSession(SessionStatus.ACTIVE);
        when(sessionRepository.findBySessionId(SESSION_ID)).thenReturn(Optional.of(session));
        when(sessionRepository.save(session)).thenReturn(session);

        var response = sessionService.markAsCompleted(SESSION_ID);

        verify(sessionRepository, times(1)).save(session);
        assertThat(session.getStatus()).isEqualTo(SessionStatus.COMPLETED);
    }

    @Test
    @DisplayName("markAsCompleted - COMPLETED→COMPLETED 抛 400 SAME_STATUS_NOOP")
    void markAsCompleted_completedToCompleted_throws400() {
        Session session = buildSession(SessionStatus.COMPLETED);
        when(sessionRepository.findBySessionId(SESSION_ID)).thenReturn(Optional.of(session));

        assertThatThrownBy(() -> sessionService.markAsCompleted(SESSION_ID))
                .isInstanceOf(BusinessException.class)
                .hasFieldOrPropertyWithValue("code", 400)
                .hasFieldOrPropertyWithValue("errorKey", "SAME_STATUS_NOOP")
                .hasMessageContaining("会话状态已是目标状态");
    }

    @Test
    @DisplayName("markAsCompleted - EXPIRED→COMPLETED 抛 400 INVALID_STATUS_TRANSITION")
    void markAsCompleted_expiredToCompleted_throws400() {
        Session session = buildSession(SessionStatus.EXPIRED);
        when(sessionRepository.findBySessionId(SESSION_ID)).thenReturn(Optional.of(session));

        assertThatThrownBy(() -> sessionService.markAsCompleted(SESSION_ID))
                .isInstanceOf(BusinessException.class)
                .hasFieldOrPropertyWithValue("code", 400)
                .hasFieldOrPropertyWithValue("errorKey", "INVALID_STATUS_TRANSITION")
                .hasMessageContaining("非法的状态转换");

        verify(sessionRepository, never()).save(session);
    }

    @Test
    @DisplayName("markAsCompleted - sessionId不存在抛 404")
    void markAsCompleted_sessionNotFound_throws404() {
        when(sessionRepository.findBySessionId("ses_unknown")).thenReturn(Optional.empty());

        assertThatThrownBy(() -> sessionService.markAsCompleted("ses_unknown"))
                .isInstanceOf(ResourceNotFoundException.class);
    }

    @Test
    @DisplayName("markAsExpired - ACTIVE→EXPIRED 合法")
    void markAsExpired_activeToExpired_succeeds() {
        Session session = buildSession(SessionStatus.ACTIVE);
        when(sessionRepository.findBySessionId(SESSION_ID)).thenReturn(Optional.of(session));
        when(sessionRepository.save(session)).thenReturn(session);

        var response = sessionService.markAsExpired(SESSION_ID);

        verify(sessionRepository, times(1)).save(session);
        assertThat(session.getStatus()).isEqualTo(SessionStatus.EXPIRED);
    }

    @Test
    @DisplayName("markAsExpired - COMPLETED→EXPIRED 抛 400")
    void markAsExpired_completedToExpired_throws400() {
        Session session = buildSession(SessionStatus.COMPLETED);
        when(sessionRepository.findBySessionId(SESSION_ID)).thenReturn(Optional.of(session));

        assertThatThrownBy(() -> sessionService.markAsExpired(SESSION_ID))
                .isInstanceOf(BusinessException.class)
                .hasFieldOrPropertyWithValue("code", 400)
                .hasFieldOrPropertyWithValue("errorKey", "INVALID_STATUS_TRANSITION")
                .hasMessageContaining("非法的状态转换");
    }

    @Test
    @DisplayName("markAsExpired - EXPIRED→EXPIRED 抛 400 SAME_STATUS_NOOP")
    void markAsExpired_expiredToExpired_throws400() {
        Session session = buildSession(SessionStatus.EXPIRED);
        when(sessionRepository.findBySessionId(SESSION_ID)).thenReturn(Optional.of(session));

        assertThatThrownBy(() -> sessionService.markAsExpired(SESSION_ID))
                .isInstanceOf(BusinessException.class)
                .hasFieldOrPropertyWithValue("code", 400)
                .hasFieldOrPropertyWithValue("errorKey", "SAME_STATUS_NOOP")
                .hasMessageContaining("会话状态已是目标状态");
    }

    @Test
    @DisplayName("updateStatus - ACTIVE→COMPLETED 合法 (走validateStatusTransition)")
    void updateStatus_activeToCompleted_succeeds() {
        Session session = buildSession(SessionStatus.ACTIVE);
        when(sessionRepository.findBySessionId(SESSION_ID)).thenReturn(Optional.of(session));
        when(sessionRepository.save(session)).thenReturn(session);

        sessionService.updateStatus(SESSION_ID, SessionStatus.COMPLETED);

        verify(sessionRepository, times(1)).save(session);
        assertThat(session.getStatus()).isEqualTo(SessionStatus.COMPLETED);
    }

    @Test
    @DisplayName("updateStatus - ACTIVE→ACTIVE 抛 400 SAME_STATUS_NOOP")
    void updateStatus_activeToActive_throws400() {
        Session session = buildSession(SessionStatus.ACTIVE);
        when(sessionRepository.findBySessionId(SESSION_ID)).thenReturn(Optional.of(session));

        assertThatThrownBy(() -> sessionService.updateStatus(SESSION_ID, SessionStatus.ACTIVE))
                .isInstanceOf(BusinessException.class)
                .hasFieldOrPropertyWithValue("code", 400)
                .hasFieldOrPropertyWithValue("errorKey", "SAME_STATUS_NOOP")
                .hasMessageContaining("会话状态已是目标状态");

        verify(sessionRepository, never()).save(session);
    }

    @Test
    @DisplayName("updateStatus - COMPLETED→ACTIVE 抛 400 INVALID_STATUS_TRANSITION")
    void updateStatus_completedToActive_throws400() {
        Session session = buildSession(SessionStatus.COMPLETED);
        when(sessionRepository.findBySessionId(SESSION_ID)).thenReturn(Optional.of(session));

        assertThatThrownBy(() -> sessionService.updateStatus(SESSION_ID, SessionStatus.ACTIVE))
                .isInstanceOf(BusinessException.class)
                .hasFieldOrPropertyWithValue("code", 400)
                .hasFieldOrPropertyWithValue("errorKey", "INVALID_STATUS_TRANSITION")
                .hasMessageContaining("非法的状态转换");
    }

    @Test
    @DisplayName("updateStatus - EXPIRED→任何状态抛 400")
    void updateStatus_expiredToAny_throws400() {
        Session session = buildSession(SessionStatus.EXPIRED);
        when(sessionRepository.findBySessionId(SESSION_ID)).thenReturn(Optional.of(session));

        assertThatThrownBy(() -> sessionService.updateStatus(SESSION_ID, SessionStatus.ACTIVE))
                .isInstanceOf(BusinessException.class)
                .hasFieldOrPropertyWithValue("code", 400);

        assertThatThrownBy(() -> sessionService.updateStatus(SESSION_ID, SessionStatus.COMPLETED))
                .isInstanceOf(BusinessException.class)
                .hasFieldOrPropertyWithValue("code", 400);
    }

    @Test
    @DisplayName("updateStatus - COMPLETED→EXPIRED 抛 400 (终态不可转换)")
    void updateStatus_completedToExpired_throws400() {
        Session session = buildSession(SessionStatus.COMPLETED);
        when(sessionRepository.findBySessionId(SESSION_ID)).thenReturn(Optional.of(session));

        assertThatThrownBy(() -> sessionService.updateStatus(SESSION_ID, SessionStatus.EXPIRED))
                .isInstanceOf(BusinessException.class)
                .hasFieldOrPropertyWithValue("code", 400)
                .hasFieldOrPropertyWithValue("errorKey", "INVALID_STATUS_TRANSITION")
                .hasMessageContaining("非法的状态转换");
    }

    @Test
    @DisplayName("markAsCompleted/markAsExpired - 不调用数据隔离校验 (受信任内部方法)")
    void markMethods_skipDataIsolation() {
        Session otherUserSession = buildSession(SessionStatus.ACTIVE);
        otherUserSession.setUserId("usr_OTHER");
        when(sessionRepository.findBySessionId(SESSION_ID)).thenReturn(Optional.of(otherUserSession));
        when(sessionRepository.save(otherUserSession)).thenReturn(otherUserSession);

        sessionService.markAsCompleted(SESSION_ID);

        assertThat(otherUserSession.getStatus()).isEqualTo(SessionStatus.COMPLETED);
    }
}
