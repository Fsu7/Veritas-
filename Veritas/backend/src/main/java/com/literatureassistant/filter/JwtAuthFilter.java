package com.literatureassistant.filter;

import com.literatureassistant.util.JwtUtil;
import io.jsonwebtoken.Claims;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.slf4j.MDC;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.util.AntPathMatcher;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.List;

@Component
@Slf4j
@RequiredArgsConstructor
public class JwtAuthFilter extends OncePerRequestFilter {

    private static final String AUTHORIZATION_HEADER = "Authorization";
    private static final String BEARER_PREFIX = "Bearer ";
    private static final String MDC_USER_ID_KEY = "userId";
    private static final List<String> WHITELIST_PATHS = List.of(
            "/api/users/register",
            "/api/users/login",
            "/health",
            "/actuator/**",
            "/error"
    );

    private final JwtUtil jwtUtil;
    private final AntPathMatcher pathMatcher = new AntPathMatcher();

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        String uri = request.getRequestURI();
        return WHITELIST_PATHS.stream()
                .anyMatch(pattern -> pathMatcher.match(pattern, uri));
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request,
            HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {

        log.debug("处理请求: {}", request.getRequestURI());

        String authHeader = request.getHeader(AUTHORIZATION_HEADER);

        if (authHeader != null && authHeader.startsWith(BEARER_PREFIX)) {
            String token = authHeader.substring(BEARER_PREFIX.length());

            if (!token.isBlank()) {
                Claims claims = jwtUtil.parseToken(token);
                if (claims != null && !jwtUtil.isJtiBlacklisted(claims.getId())) {
                    String userId = claims.getSubject();
                    String username = claims.get("username", String.class);

                    UsernamePasswordAuthenticationToken authentication =
                            new UsernamePasswordAuthenticationToken(userId, null, List.of());
                    SecurityContextHolder.getContext().setAuthentication(authentication);
                    MDC.put(MDC_USER_ID_KEY, userId);

                    log.debug("JWT认证成功: userId={}, username={}", userId, username);
                }
            }
        }

        try {
            chain.doFilter(request, response);
        } finally {
            SecurityContextHolder.clearContext();
            MDC.remove(MDC_USER_ID_KEY);
        }
    }
}
