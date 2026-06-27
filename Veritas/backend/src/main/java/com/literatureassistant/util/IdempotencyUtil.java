package com.literatureassistant.util;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.time.Duration;

/**
 * 幂等性工具，基于 Redis SETNX 实现请求去重。
 * P1-15 修复: 防止分析接口重复提交导致重复创建资源和重复 AI 调用。
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class IdempotencyUtil {

    private final StringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper;

    private static final Duration DEFAULT_TTL = Duration.ofMinutes(5);

    /**
     * 尝试获取幂等锁。
     * @param key 幂等键
     * @return true 表示首次请求，可继续执行；false 表示重复请求
     */
    public boolean tryAcquire(String key) {
        return tryAcquire(key, DEFAULT_TTL);
    }

    /**
     * 尝试获取幂等锁。
     * @param key 幂等键
     * @param ttl 锁过期时间
     * @return true 表示首次请求；false 表示重复请求
     */
    public boolean tryAcquire(String key, Duration ttl) {
        Boolean acquired = redisTemplate.opsForValue()
                .setIfAbsent("idempotency:" + key, "1", ttl);
        return Boolean.TRUE.equals(acquired);
    }

    /**
     * 存储结果，供重复请求返回
     */
    public void storeResult(String key, Object result) {
        storeResult(key, result, DEFAULT_TTL);
    }

    /**
     * 存储结果，供重复请求返回
     */
    public void storeResult(String key, Object result, Duration ttl) {
        try {
            String json = objectMapper.writeValueAsString(result);
            redisTemplate.opsForValue()
                    .set("idempotency:result:" + key, json, ttl);
        } catch (JsonProcessingException e) {
            log.warn("Failed to store idempotency result: key={}", key, e);
        }
    }

    /**
     * 获取已存储的结果 JSON
     */
    public String getStoredResult(String key) {
        return redisTemplate.opsForValue().get("idempotency:result:" + key);
    }

    /**
     * 释放幂等锁（在业务执行失败时调用，允许重试）
     */
    public void release(String key) {
        redisTemplate.delete("idempotency:" + key);
        redisTemplate.delete("idempotency:result:" + key);
    }
}
