package com.literatureassistant.filter;

import com.literatureassistant.util.JwtUtil;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.impl.DefaultClaims;
import jakarta.servlet.FilterChain;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.core.context.SecurityContextHolder;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThatNoException;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class JwtAuthFilterTest {

    @InjectMocks
    private JwtAuthFilter jwtAuthFilter;

    @Mock
    private JwtUtil jwtUtil;

    @Mock
    private HttpServletRequest request;

    @Mock
    private HttpServletResponse response;

    @Mock
    private FilterChain filterChain;

    @BeforeEach
    void setUp() {
        SecurityContextHolder.clearContext();
    }

    @Test
    @DisplayName("doFilterInternal - 有效Token设置SecurityContext")
    void doFilterInternal_validToken_setsSecurityContext() throws Exception {
        when(request.getHeader("Authorization")).thenReturn("Bearer valid-token");

        Claims claims = new DefaultClaims(Map.of(
                "sub", "usr_test1234",
                "username", "testuser",
                "jti", "jti-uuid-123"
        ));
        when(jwtUtil.parseToken("valid-token")).thenReturn(claims);
        when(jwtUtil.isJtiBlacklisted("jti-uuid-123")).thenReturn(false);

        jwtAuthFilter.doFilterInternal(request, response, filterChain);

        verify(filterChain).doFilter(request, response);
    }

    @Test
    @DisplayName("doFilterInternal - 无Authorization头继续过滤链")
    void doFilterInternal_noAuthHeader_continuesFilterChain() throws Exception {
        when(request.getHeader("Authorization")).thenReturn(null);

        jwtAuthFilter.doFilterInternal(request, response, filterChain);

        verify(filterChain).doFilter(request, response);
    }

    @Test
    @DisplayName("doFilterInternal - 无效Token不设置SecurityContext")
    void doFilterInternal_invalidToken_doesNotSetSecurityContext() throws Exception {
        when(request.getHeader("Authorization")).thenReturn("Bearer invalid-token");
        when(jwtUtil.parseToken("invalid-token")).thenReturn(null);

        jwtAuthFilter.doFilterInternal(request, response, filterChain);

        verify(filterChain).doFilter(request, response);
    }

    @Test
    @DisplayName("doFilterInternal - 黑名单Token不设置SecurityContext")
    void doFilterInternal_blacklistedToken_doesNotSetSecurityContext() throws Exception {
        when(request.getHeader("Authorization")).thenReturn("Bearer blacklisted-token");

        Claims claims = new DefaultClaims(Map.of(
                "sub", "usr_test1234",
                "username", "testuser",
                "jti", "blacklisted-jti"
        ));
        when(jwtUtil.parseToken("blacklisted-token")).thenReturn(claims);
        when(jwtUtil.isJtiBlacklisted("blacklisted-jti")).thenReturn(true);

        jwtAuthFilter.doFilterInternal(request, response, filterChain);

        verify(filterChain).doFilter(request, response);
    }

    @Test
    @DisplayName("doFilterInternal - 白名单路径不需要Token")
    void doFilterInternal_whitelistPath_noTokenRequired() throws Exception {
        when(request.getHeader("Authorization")).thenReturn(null);
        when(request.getRequestURI()).thenReturn("/api/users/login");

        jwtAuthFilter.doFilterInternal(request, response, filterChain);

        verify(filterChain).doFilter(request, response);
    }
}
