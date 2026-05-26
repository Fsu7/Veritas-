package com.literatureassistant.util;

import com.literatureassistant.config.RedisConfig;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.ValueOperations;
import org.springframework.test.util.ReflectionTestUtils;

import java.time.Duration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class JwtUtilTest {

    @InjectMocks
    private JwtUtil jwtUtil;

    @Mock
    private RedisTemplate<String, String> redisTemplate;

    @Mock
    private ValueOperations<String, String> valueOperations;

    @BeforeEach
    void setUp() {
        ReflectionTestUtils.setField(jwtUtil, "secret", "this-is-a-very-long-secret-key-for-testing-purposes-only-min-32-chars");
        ReflectionTestUtils.setField(jwtUtil, "expiration", 86400000L);
        jwtUtil.validateSecret();
    }

    @Test
    @DisplayName("generateToken - 正常生成Token")
    void generateToken_normal_returnsToken() {
        String token = jwtUtil.generateToken("usr_test1234", "testuser");

        assertThat(token).isNotNull();
        assertThat(token).isNotEmpty();
    }

    @Test
    @DisplayName("validateToken - 有效Token返回true")
    void validateToken_validToken_returnsTrue() {
        String token = jwtUtil.generateToken("usr_test1234", "testuser");

        boolean isValid = jwtUtil.validateToken(token);

        assertThat(isValid).isTrue();
    }

    @Test
    @DisplayName("validateToken - 无效Token返回false")
    void validateToken_invalidToken_returnsFalse() {
        boolean isValid = jwtUtil.validateToken("invalid-token");

        assertThat(isValid).isFalse();
    }

    @Test
    @DisplayName("getUserIdFromToken - 正常提取userId")
    void getUserIdFromToken_normal_returnsUserId() {
        String token = jwtUtil.generateToken("usr_test1234", "testuser");

        String userId = jwtUtil.getUserIdFromToken(token);

        assertThat(userId).isEqualTo("usr_test1234");
    }

    @Test
    @DisplayName("getUsernameFromToken - 正常提取username")
    void getUsernameFromToken_normal_returnsUsername() {
        String token = jwtUtil.generateToken("usr_test1234", "testuser");

        String username = jwtUtil.getUsernameFromToken(token);

        assertThat(username).isEqualTo("testuser");
    }

    @Test
    @DisplayName("blacklistToken - 正常加入黑名单")
    void blacklistToken_normal_addsToBlacklist() {
        String token = jwtUtil.generateToken("usr_test1234", "testuser");
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);

        boolean result = jwtUtil.blacklistToken(token);

        assertThat(result).isTrue();
        verify(valueOperations).set(anyString(), eq("1"), any(Duration.class));
    }

    @Test
    @DisplayName("isTokenBlacklisted - 黑名单中的Token返回true")
    void isTokenBlacklisted_blacklistedToken_returnsTrue() {
        String token = jwtUtil.generateToken("usr_test1234", "testuser");
        String jti = jwtUtil.getTokenJti(token);

        when(redisTemplate.hasKey(anyString())).thenReturn(true);

        boolean isBlacklisted = jwtUtil.isJtiBlacklisted(jti);

        assertThat(isBlacklisted).isTrue();
    }

    @Test
    @DisplayName("isTokenBlacklisted - 非黑名单Token返回false")
    void isTokenBlacklisted_nonBlacklistedToken_returnsFalse() {
        String token = jwtUtil.generateToken("usr_test1234", "testuser");
        String jti = jwtUtil.getTokenJti(token);

        when(redisTemplate.hasKey(anyString())).thenReturn(false);

        boolean isBlacklisted = jwtUtil.isJtiBlacklisted(jti);

        assertThat(isBlacklisted).isFalse();
    }

    @Test
    @DisplayName("extractBearerToken - 正常提取Bearer Token")
    void extractBearerToken_normal_returnsToken() {
        String result = jwtUtil.extractBearerToken("Bearer my-token");

        assertThat(result).isEqualTo("my-token");
    }

    @Test
    @DisplayName("extractBearerToken - 无Bearer前缀返回null")
    void extractBearerToken_noBearerPrefix_returnsNull() {
        String result = jwtUtil.extractBearerToken("my-token");

        assertThat(result).isNull();
    }

    @Test
    @DisplayName("extractBearerToken - null输入返回null")
    void extractBearerToken_nullInput_returnsNull() {
        String result = jwtUtil.extractBearerToken(null);

        assertThat(result).isNull();
    }

    @Test
    @DisplayName("isTokenExpired - 未过期Token返回false")
    void isTokenExpired_validToken_returnsFalse() {
        String token = jwtUtil.generateToken("usr_test1234", "testuser");

        boolean isExpired = jwtUtil.isTokenExpired(token);

        assertThat(isExpired).isFalse();
    }
}
