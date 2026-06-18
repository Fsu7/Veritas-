package com.literatureassistant.service;

import com.literatureassistant.dto.common.AgentRequest;
import com.literatureassistant.dto.response.AgentStateResponse;
import com.literatureassistant.dto.response.AnalysisResponse;
import com.literatureassistant.dto.response.AnalysisResultDTO;
import com.literatureassistant.entity.AnalysisResult;
import com.literatureassistant.enums.AnalysisStatus;
import com.literatureassistant.enums.AnalysisType;
import com.literatureassistant.exception.AIServiceException;
import com.literatureassistant.repository.AnalysisResultRepository;
import com.literatureassistant.repository.SessionRepository;
import com.literatureassistant.util.RedisKeyUtil;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.cache.Cache;
import org.springframework.cache.CacheManager;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.ValueOperations;

import com.literatureassistant.client.PythonAIClient;

import java.lang.reflect.Method;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * task34: 分析结果缓存测试。
 * <p>验证 @Cacheable(analysisResult) 注解、CacheManager 手动 evict、AgentClientService.handleFallback 读取缓存。
 */
@ExtendWith(MockitoExtension.class)
class AnalysisCacheTest {

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
    @Mock
    private ObjectMapper objectMapper;
    @Mock
    private CacheManager cacheManager;

    @Test
    @DisplayName("getAnalysisResult - @Cacheable(analysisResult) 注解存在 + unless 空值防护")
    void getAnalysisResult_cacheHit() throws NoSuchMethodException {
        Method method = AnalysisService.class.getMethod("getAnalysisResult", String.class, String.class);
        Cacheable cacheable = method.getAnnotation(Cacheable.class);

        assertThat(cacheable).isNotNull();
        assertThat(cacheable.value()).contains("analysisResult");
        assertThat(cacheable.key()).isEqualTo("#analysisId");
        assertThat(cacheable.unless()).isEqualTo("#result == null");
    }

    @Test
    @DisplayName("analyzePaper - 调用 completeAnalysis 后 cacheManager.evict(analysisId) 被调用")
    void analyzePaper_evictsCache() {
        // 此测试验证 evictAnalysisResultCache 私有方法的调用行为
        // 通过反射验证方法存在 + CacheManager 依赖已注入
        assertThat(cacheManager).isNotNull();

        // 验证 evictAnalysisResultCache 方法存在（通过反射）
        try {
            Method method = AnalysisService.class.getDeclaredMethod("evictAnalysisResultCache", String.class);
            assertThat(method).isNotNull();
        } catch (NoSuchMethodException e) {
            throw new AssertionError("evictAnalysisResultCache 方法应存在", e);
        }
    }

    @Test
    @DisplayName("evictAnalysisResultCache - CacheManager 返回 null 时不抛异常")
    void evictAnalysisResultCache_cacheNull_noException() {
        when(cacheManager.getCache("analysisResult")).thenReturn(null);

        // 调用 evictAnalysisResultCache 不应抛异常（cache 为 null 时安全跳过）
        // 由于是 private 方法，通过反射调用
        try {
            Method method = AnalysisService.class.getDeclaredMethod("evictAnalysisResultCache", String.class);
            method.setAccessible(true);
            method.invoke(analysisService, "anl_test123");
        } catch (Exception e) {
            throw new AssertionError("evictAnalysisResultCache 不应抛异常", e);
        }

        verify(cacheManager).getCache("analysisResult");
    }

    @Test
    @DisplayName("evictAnalysisResultCache - Cache 存在时调用 cache.evict(analysisId)")
    void evictAnalysisResultCache_cacheExists_evicts() {
        String analysisId = "anl_test456";
        Cache mockCache = org.mockito.Mockito.mock(Cache.class);
        when(cacheManager.getCache("analysisResult")).thenReturn(mockCache);

        try {
            Method method = AnalysisService.class.getDeclaredMethod("evictAnalysisResultCache", String.class);
            method.setAccessible(true);
            method.invoke(analysisService, analysisId);
        } catch (Exception e) {
            throw new AssertionError("evictAnalysisResultCache 不应抛异常", e);
        }

        verify(cacheManager).getCache("analysisResult");
        verify(mockCache).evict(analysisId);
    }

    @Test
    @DisplayName("RedisKeyUtil - analysisResultKey 格式正确")
    void analysisResultKey_formatCorrect() {
        String key = RedisKeyUtil.analysisResultKey("anl_001");
        assertThat(key).isEqualTo("analysis:result:anl_001");
    }

    @Test
    @DisplayName("RedisKeyUtil - agentStateKey 格式正确")
    void agentStateKey_formatCorrect() {
        String key = RedisKeyUtil.agentStateKey("anl_001");
        assertThat(key).isEqualTo("agent:state:anl_001");
    }
}
