package com.literatureassistant.service;

import com.literatureassistant.cache.CacheEvictionHelper;
import com.literatureassistant.dto.common.PageResponse;
import com.literatureassistant.dto.request.SessionCreateRequest;
import com.literatureassistant.dto.response.SessionResponse;
import com.literatureassistant.entity.Session;
import com.literatureassistant.enums.SessionStatus;
import com.literatureassistant.mapper.SessionMapper;
import com.literatureassistant.repository.AnalysisResultRepository;
import com.literatureassistant.repository.SessionRepository;
import com.literatureassistant.util.RedisKeyUtil;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;

import java.lang.reflect.Method;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * task34: 会话状态缓存测试。
 * <p>验证 @Cacheable(sessionList) / CacheEvictionHelper / @CacheEvict(sessionState) 配置正确性。
 */
@ExtendWith(MockitoExtension.class)
class SessionCacheTest {

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

    @Test
    @DisplayName("listSessions - @Cacheable(sessionList) 注解存在 + Key 用 RedisKeyUtil.sessionListKey")
    void listSessions_cacheHit() throws NoSuchMethodException {
        Method method = SessionService.class.getMethod("listSessions", String.class, int.class, int.class);
        Cacheable cacheable = method.getAnnotation(Cacheable.class);

        assertThat(cacheable).isNotNull();
        assertThat(cacheable.value()).contains("sessionList");
        assertThat(cacheable.key())
                .contains("RedisKeyUtil")
                .contains("sessionListKey");
    }

    @Test
    @DisplayName("createSession - P2-1: 不再使用 @CacheEvict(allEntries=true)，改用 CacheEvictionHelper 精准失效")
    void createSession_evictsListCache() throws NoSuchMethodException {
        Method method = SessionService.class.getMethod("createSession", String.class, SessionCreateRequest.class);
        CacheEvict cacheEvict = method.getAnnotation(CacheEvict.class);

        // P2-1: createSession 不再标注 @CacheEvict(allEntries=true)，
        // 改用 CacheEvictionHelper 按用户前缀精准失效，避免清空整个 sessionList 缓存空间影响其他用户。
        assertThat(cacheEvict)
                .as("P2-1: createSession 不应再标注 @CacheEvict，改用 CacheEvictionHelper")
                .isNull();
    }

    @Test
    @DisplayName("updateStatus - @CacheEvict(sessionState, key=#sessionId) 注解存在")
    void updateStatus_evictsStateCache() throws NoSuchMethodException {
        Method method = SessionService.class.getMethod("updateStatus", String.class, SessionStatus.class);
        CacheEvict cacheEvict = method.getAnnotation(CacheEvict.class);

        assertThat(cacheEvict).isNotNull();
        assertThat(cacheEvict.value()).contains("sessionState");
        assertThat(cacheEvict.key()).isEqualTo("#sessionId");
    }

    @Test
    @DisplayName("RedisKeyUtil - sessionListKey 格式正确")
    void sessionListKey_formatCorrect() {
        String key = RedisKeyUtil.sessionListKey("usr_001", 1, 10);
        assertThat(key).isEqualTo("session:list:usr_001:1:10");
    }

    @Test
    @DisplayName("RedisKeyUtil - sessionStateKey 格式正确")
    void sessionStateKey_formatCorrect() {
        String key = RedisKeyUtil.sessionStateKey("ses_001");
        assertThat(key).isEqualTo("session:state:ses_001");
    }

    @Test
    @DisplayName("listSessions - 正常分页查询返回 PageResponse")
    void listSessions_normal_returnsPageResponse() {
        // 注意：由于 listSessions 有 @Cacheable 注解，Mockito 不会触发注解行为
        // 此测试验证业务逻辑正确性（Mockito 不走 Spring Cache 代理）
        Session session = Session.builder()
                .sessionId("ses_001")
                .userId("usr_001")
                .topic("Test")
                .status(SessionStatus.ACTIVE)
                .build();
        Page<Session> mockPage = new PageImpl<>(List.of(session), PageRequest.of(0, 10), 1);
        SessionResponse sessionResponse = SessionResponse.builder()
                .sessionId("ses_001")
                .userId("usr_001")
                .topic("Test")
                .status("active")
                .build();

        when(sessionRepository.findByUserIdOrderByCreatedAtDesc(anyString(), any(Pageable.class)))
                .thenReturn(mockPage);
        when(sessionMapper.toResponse(session)).thenReturn(sessionResponse);

        PageResponse<SessionResponse> result = sessionService.listSessions("usr_001", 1, 10);

        assertThat(result).isNotNull();
        assertThat(result.getItems()).hasSize(1);
        assertThat(result.getItems().get(0).getSessionId()).isEqualTo("ses_001");
    }
}
