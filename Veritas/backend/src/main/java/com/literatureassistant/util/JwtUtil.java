package com.literatureassistant.util;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.ExpiredJwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.MalformedJwtException;
import io.jsonwebtoken.UnsupportedJwtException;
import io.jsonwebtoken.security.Keys;
import io.jsonwebtoken.security.SecurityException;
import jakarta.annotation.PostConstruct;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Duration;
import java.util.Date;
import java.util.UUID;

@Component
@Slf4j
public class JwtUtil {

    private static final int MIN_SECRET_LENGTH = 32;
    private static final String TOKEN_TYPE_ACCESS = "access";

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
                .claim("token_type", TOKEN_TYPE_ACCESS)
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
            log.debug("JWT token已过期: {}", maskToken(token));
        } catch (MalformedJwtException e) {
            log.debug("JWT token格式错误: {}", maskToken(token));
        } catch (SecurityException e) {
            log.debug("JWT签名无效: {}", maskToken(token));
        } catch (UnsupportedJwtException e) {
            log.debug("不支持的JWT token: {}", maskToken(token));
        } catch (IllegalArgumentException e) {
            log.debug("JWT token为空");
        }
        return null;
    }

    public boolean validateToken(String token) {
        return parseToken(token) != null;
    }

    public boolean isTokenBlacklisted(String token) {
        String jti = getTokenJti(token);
        return isJtiBlacklisted(jti);
    }

    public boolean isJtiBlacklisted(String jti) {
        if (jti == null) {
            return true;
        }
        String hash = sha256(jti);
        String key = RedisKeyUtil.authBlacklistKey(hash);
        return Boolean.TRUE.equals(redisTemplate.hasKey(key));
    }

    public boolean blacklistToken(String token) {
        String jti = getTokenJti(token);
        if (jti == null) {
            return false;
        }

        long remainingTime = getTokenRemainingTime(token);
        if (remainingTime <= 0) {
            return false;
        }

        String hash = sha256(jti);
        String key = RedisKeyUtil.authBlacklistKey(hash);
        redisTemplate.opsForValue().set(key, "1", Duration.ofMillis(remainingTime));

        log.debug("Token加入黑名单: jtiHash={}, remainingTime={}ms", maskJti(hash), remainingTime);
        return true;
    }

    public String extractBearerToken(String authHeader) {
        if (authHeader != null && authHeader.startsWith("Bearer ")) {
            return authHeader.substring(7);
        }
        return null;
    }

    public boolean isTokenExpired(String token) {
        if (token == null || token.isEmpty()) {
            return true;
        }
        try {
            Claims claims = parseToken(token);
            if (claims == null) {
                return true;
            }
            return claims.getExpiration().before(new Date());
        } catch (Exception e) {
            return true;
        }
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

    private String sha256(String input) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(input.getBytes(StandardCharsets.UTF_8));
            StringBuilder hexString = new StringBuilder();
            for (byte b : hash) {
                String hex = Integer.toHexString(0xff & b);
                if (hex.length() == 1) {
                    hexString.append('0');
                }
                hexString.append(hex);
            }
            return hexString.toString();
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 algorithm not available", e);
        }
    }

    private String maskToken(String token) {
        if (token == null || token.isEmpty()) {
            return "";
        }
        return token.substring(0, Math.min(8, token.length())) + "...";
    }

    private String maskJti(String jti) {
        if (jti == null || jti.isEmpty()) {
            return "";
        }
        return jti.substring(0, Math.min(8, jti.length())) + "...";
    }
}
