package com.literatureassistant.filter;

import com.literatureassistant.util.JwtUtil;
import com.literatureassistant.util.RedisKeyUtil;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.security.core.context.SecurityContextHolder;

import java.io.IOException;
import java.util.HashSet;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class JwtAuthFilterTest {

    private static final String VALID_SECRET = "literature-assistant-jwt-secret-key-2026-minimum-32chars";

    @Mock
    private FilterChain filterChain;

    private JwtUtil jwtUtil;

    private JwtAuthFilter jwtAuthFilter;

    private Set<String> blacklistedKeys;

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
        org.springframework.test.util.ReflectionTestUtils.setField(jwtUtil, "secret", VALID_SECRET);
        org.springframework.test.util.ReflectionTestUtils.setField(jwtUtil, "expiration", 86400000L);
        jwtAuthFilter = new JwtAuthFilter(jwtUtil);
        SecurityContextHolder.clearContext();
    }

    @Test
    @DisplayName("有效Token应设置SecurityContext认证信息")
    void doFilterInternal_validToken_setsAuthentication() throws ServletException, IOException {
        String token = jwtUtil.generateToken("usr_001", "testuser");
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.addHeader("Authorization", "Bearer " + token);
        MockHttpServletResponse response = new MockHttpServletResponse();

        jwtAuthFilter.doFilterInternal(request, response, filterChain);

        assertNotNull(SecurityContextHolder.getContext().getAuthentication());
        assertEquals("usr_001", SecurityContextHolder.getContext().getAuthentication().getPrincipal());
        verify(filterChain).doFilter(request, response);
    }

    @Test
    @DisplayName("无效Token不应设置SecurityContext")
    void doFilterInternal_invalidToken_noAuthentication() throws ServletException, IOException {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.addHeader("Authorization", "Bearer invalid.token.string");
        MockHttpServletResponse response = new MockHttpServletResponse();

        jwtAuthFilter.doFilterInternal(request, response, filterChain);

        assertNull(SecurityContextHolder.getContext().getAuthentication());
        verify(filterChain).doFilter(request, response);
    }

    @Test
    @DisplayName("黑名单Token不应设置SecurityContext")
    void doFilterInternal_blacklistedToken_noAuthentication() throws ServletException, IOException {
        String token = jwtUtil.generateToken("usr_001", "testuser");
        String jti = jwtUtil.getTokenJti(token);
        blacklistedKeys.add(RedisKeyUtil.authBlacklistKey(jti));

        MockHttpServletRequest request = new MockHttpServletRequest();
        request.addHeader("Authorization", "Bearer " + token);
        MockHttpServletResponse response = new MockHttpServletResponse();

        jwtAuthFilter.doFilterInternal(request, response, filterChain);

        assertNull(SecurityContextHolder.getContext().getAuthentication());
        verify(filterChain).doFilter(request, response);
    }

    @Test
    @DisplayName("无Authorization头不应设置SecurityContext")
    void doFilterInternal_noAuthHeader_noAuthentication() throws ServletException, IOException {
        MockHttpServletRequest request = new MockHttpServletRequest();
        MockHttpServletResponse response = new MockHttpServletResponse();

        jwtAuthFilter.doFilterInternal(request, response, filterChain);

        assertNull(SecurityContextHolder.getContext().getAuthentication());
        verify(filterChain).doFilter(request, response);
    }

    @Test
    @DisplayName("非Bearer格式不应设置SecurityContext")
    void doFilterInternal_nonBearerFormat_noAuthentication() throws ServletException, IOException {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.addHeader("Authorization", "Basic dXNlcjpwYXNz");
        MockHttpServletResponse response = new MockHttpServletResponse();

        jwtAuthFilter.doFilterInternal(request, response, filterChain);

        assertNull(SecurityContextHolder.getContext().getAuthentication());
        verify(filterChain).doFilter(request, response);
    }
}
