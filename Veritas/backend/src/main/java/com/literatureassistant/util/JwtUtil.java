package com.literatureassistant.util;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.ExpiredJwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.MalformedJwtException;
import io.jsonwebtoken.UnsupportedJwtException;
import io.jsonwebtoken.security.Keys;
import io.jsonwebtoken.security.SecurityException;
import jakarta.annotation.PostConstruct;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;
import java.util.UUID;

@Component
public class JwtUtil {

    private static final Logger log = LoggerFactory.getLogger(JwtUtil.class);
    private static final int MIN_SECRET_LENGTH = 32;

    @Value("${jwt.secret}")
    private String secret;

    @Value("${jwt.expiration:86400000}")
    private long expiration;

    private final RedisTemplate<String, String> redisTemplate;

    public JwtUtil(RedisTemplate<String, String> redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    @PostConstruct
    void validateSecret() {
        if (secret == null || secret.getBytes(StandardCharsets.UTF_8).length < MIN_SECRET_LENGTH) {
            throw new IllegalStateException("JWT secret must be at least 32 characters");
        }
    }

    public String generateToken(String userId, String username) {
        Date now = new Date();
        Date expiryDate = new Date(now.getTime() + expiration);

        return Jwts.builder()
                .subject(userId)
                .claim("username", username)
                .id(UUID.randomUUID().toString())
                .issuedAt(now)
                .expiration(expiryDate)
                .signWith(getSigningKey(), Jwts.SIG.HS256)
                .compact();
    }

    public Claims parseToken(String token) {
        try {
            return Jwts.parser()
                    .verifyWith(getSigningKey())
                    .build()
                    .parseSignedClaims(token)
                    .getPayload();
        } catch (ExpiredJwtException e) {
            log.debug("JWT token expired: {}", maskToken(token));
        } catch (UnsupportedJwtException e) {
            log.debug("Unsupported JWT token: {}", maskToken(token));
        } catch (MalformedJwtException e) {
            log.debug("Malformed JWT token: {}", maskToken(token));
        } catch (SecurityException e) {
            log.debug("Invalid JWT signature: {}", maskToken(token));
        } catch (IllegalArgumentException e) {
            log.debug("JWT token is empty or null");
        }
        return null;
    }

    public boolean validateToken(String token) {
        return parseToken(token) != null;
    }

    public boolean isTokenBlacklisted(String token) {
        String jti = getTokenJti(token);
        if (jti == null) {
            return true;
        }
        String key = RedisKeyUtil.authBlacklistKey(jti);
        return Boolean.TRUE.equals(redisTemplate.hasKey(key));
    }

    public String getUserIdFromToken(String token) {
        Claims claims = parseToken(token);
        return claims != null ? claims.getSubject() : null;
    }

    public String getUsernameFromToken(String token) {
        Claims claims = parseToken(token);
        return claims != null ? claims.get("username", String.class) : null;
    }

    public String getTokenJti(String token) {
        Claims claims = parseToken(token);
        return claims != null ? claims.getId() : null;
    }

    public long getTokenRemainingTime(String token) {
        Claims claims = parseToken(token);
        if (claims == null) {
            return 0;
        }
        long expMs = claims.getExpiration().getTime();
        return Math.max(0, expMs - System.currentTimeMillis());
    }

    private SecretKey getSigningKey() {
        return Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
    }

    private String maskToken(String token) {
        if (token == null || token.isEmpty()) {
            return "";
        }
        return token.substring(0, Math.min(8, token.length())) + "...";
    }
}
