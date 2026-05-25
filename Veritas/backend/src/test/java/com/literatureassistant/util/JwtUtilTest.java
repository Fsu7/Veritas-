package com.literatureassistant.util;

import io.jsonwebtoken.Claims;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.HashSet;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

class JwtUtilTest {

    private static final String VALID_SECRET = "literature-assistant-jwt-secret-key-2026-minimum-32chars";

    private Set<String> blacklistedKeys;
    private JwtUtil jwtUtil;

    @SuppressWarnings({"unchecked", "rawtypes"})
    @BeforeEach
    void setUp() {
        blacklistedKeys = new HashSet<>();
        RedisTemplate redisTemplate = new RedisTemplate() {
            @Override
            public Boolean hasKey(Object key) {
                return blacklistedKeys.contains(key);
            }
        };
        jwtUtil = new JwtUtil(redisTemplate);
        ReflectionTestUtils.setField(jwtUtil, "secret", VALID_SECRET);
        ReflectionTestUtils.setField(jwtUtil, "expiration", 86400000L);
    }

    @Test
    @DisplayName("generateToken should generate non-empty token")
    void shouldGenerateValidToken() {
        String token = jwtUtil.generateToken("usr_001", "testuser");
        assertNotNull(token);
        assertFalse(token.isEmpty());
    }

    @Test
    @DisplayName("parseToken should correctly parse token with userId/username/jti")
    void shouldParseTokenSuccessfully() {
        String token = jwtUtil.generateToken("usr_001", "testuser");
        Claims claims = jwtUtil.parseToken(token);

        assertNotNull(claims);
        assertEquals("usr_001", claims.getSubject());
        assertEquals("testuser", claims.get("username", String.class));
        assertNotNull(claims.getId());
    }

    @Test
    @DisplayName("parseToken should return null for invalid token")
    void shouldReturnNullForInvalidToken() {
        assertNull(jwtUtil.parseToken("invalid.token.string"));
    }

    @Test
    @DisplayName("parseToken should return null for empty token")
    void shouldReturnNullForEmptyToken() {
        assertNull(jwtUtil.parseToken(""));
    }

    @Test
    @DisplayName("parseToken should return null for null token")
    void shouldReturnNullForNullToken() {
        assertNull(jwtUtil.parseToken(null));
    }

    @Test
    @DisplayName("validateToken should return true for valid token")
    void shouldValidateToken() {
        String token = jwtUtil.generateToken("usr_001", "testuser");
        assertTrue(jwtUtil.validateToken(token));
    }

    @Test
    @DisplayName("validateToken should return false for invalid token")
    void shouldNotValidateInvalidToken() {
        assertFalse(jwtUtil.validateToken("invalid.token.string"));
    }

    @Test
    @DisplayName("getUserIdFromToken should extract userId")
    void shouldExtractUserIdFromToken() {
        String token = jwtUtil.generateToken("usr_001", "testuser");
        assertEquals("usr_001", jwtUtil.getUserIdFromToken(token));
    }

    @Test
    @DisplayName("getUsernameFromToken should extract username")
    void shouldExtractUsernameFromToken() {
        String token = jwtUtil.generateToken("usr_001", "testuser");
        assertEquals("testuser", jwtUtil.getUsernameFromToken(token));
    }

    @Test
    @DisplayName("getTokenJti should extract jti")
    void shouldExtractJtiFromToken() {
        String token = jwtUtil.generateToken("usr_001", "testuser");
        String jti = jwtUtil.getTokenJti(token);
        assertNotNull(jti);
        assertFalse(jti.isEmpty());
    }

    @Test
    @DisplayName("getTokenRemainingTime should return positive value for valid token")
    void shouldReturnTokenRemainingTime() {
        String token = jwtUtil.generateToken("usr_001", "testuser");
        long remaining = jwtUtil.getTokenRemainingTime(token);
        assertTrue(remaining > 0);
        assertTrue(remaining <= 86400000L);
    }

    @Test
    @DisplayName("getTokenRemainingTime should return 0 for invalid token")
    void shouldReturnZeroRemainingTimeForInvalidToken() {
        assertEquals(0, jwtUtil.getTokenRemainingTime("invalid.token"));
    }

    @Test
    @DisplayName("validateSecret should throw IllegalStateException when secret is too short")
    void shouldThrowWhenSecretTooShort() {
        ReflectionTestUtils.setField(jwtUtil, "secret", "short");
        assertThrows(IllegalStateException.class, () ->
                jwtUtil.validateSecret());
    }

    @Test
    @DisplayName("isTokenBlacklisted should return true when token is in blacklist")
    void shouldDetectBlacklistedToken() {
        String token = jwtUtil.generateToken("usr_001", "testuser");
        String jti = jwtUtil.getTokenJti(token);
        String blacklistKey = RedisKeyUtil.authBlacklistKey(jti);
        blacklistedKeys.add(blacklistKey);

        assertTrue(jwtUtil.isTokenBlacklisted(token));
    }

    @Test
    @DisplayName("isTokenBlacklisted should return false when token is not in blacklist")
    void shouldNotDetectNonBlacklistedToken() {
        String token = jwtUtil.generateToken("usr_001", "testuser");

        assertFalse(jwtUtil.isTokenBlacklisted(token));
    }

    @Test
    @DisplayName("isTokenBlacklisted should return true for invalid token")
    void shouldReturnTrueForInvalidTokenBlacklistCheck() {
        assertTrue(jwtUtil.isTokenBlacklisted("invalid.token"));
    }
}
