package com.literatureassistant.cache;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.Cursor;
import org.springframework.data.redis.core.RedisCallback;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.ScanOptions;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

/**
 * P2-1: 缓存精准失效工具。
 * <p>替代 @CacheEvict(allEntries=true) 的全空间清空，改为按前缀精准删除指定用户的分页缓存。
 * <p>使用 SCAN 命令避免 KEYS 阻塞 Redis；删除操作分批执行，避免单次 DEL 大量 key 造成阻塞。
 * <p>缓存清除失败不影响业务流程，TTL 最终会过期保证最终一致性。
 *
 * @author XH-202630 Literature Assistant
 * @since 0.6
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class CacheEvictionHelper {

    private static final long SCAN_COUNT = 100L;
    private static final int DELETE_BATCH_SIZE = 100;

    private final RedisTemplate<String, String> redisTemplate;

    /**
     * 按前缀精准删除缓存。
     * <p>注意：Spring Cache 默认 Key 格式为 {cacheName}::{key}，
     * 所传入的 pattern 应为 {cacheName}::{业务前缀}*。
     *
     * @param pattern Redis Key 匹配模式（如 "sessionList::session:list:userId:*"）
     */
    public void evictByPattern(String pattern) {
        try {
            ScanOptions options = ScanOptions.scanOptions()
                    .count(SCAN_COUNT)
                    .match(pattern)
                    .build();

            redisTemplate.execute((RedisCallback<Void>) connection -> {
                java.util.List<byte[]> batch = new java.util.ArrayList<>(DELETE_BATCH_SIZE);
                try (Cursor<byte[]> cursor = connection.scan(options)) {
                    while (cursor.hasNext()) {
                        batch.add(cursor.next());
                        if (batch.size() >= DELETE_BATCH_SIZE) {
                            connection.del(batch.toArray(new byte[0][]));
                            log.debug("Evicted batch of {} keys for pattern: {}", batch.size(), pattern);
                            batch.clear();
                        }
                    }
                }
                if (!batch.isEmpty()) {
                    connection.del(batch.toArray(new byte[0][]));
                    log.debug("Evicted final batch of {} keys for pattern: {}", batch.size(), pattern);
                }
                return null;
            });
            log.info("Cache eviction completed for pattern: {}", pattern);
        } catch (Exception e) {
            log.warn("Cache eviction failed for pattern {}: {}", pattern, e.getMessage());
            // 缓存清除失败不影响业务流程，TTL 最终会过期
        }
    }

    /**
     * 在当前事务提交后执行缓存清除（Cache-Aside 写后删模式）。
     * <p>若当前无事务上下文（如单元测试），则直接同步执行。
     * <p>设计理由：在事务提交前清缓存可能导致其他请求读到未提交的旧数据并回填缓存，
     * 造成缓存与 DB 不一致。afterCommit 回调确保只在事务成功提交后清缓存。
     *
     * @param pattern Redis Key 匹配模式
     */
    public void evictByPatternAfterCommit(String pattern) {
        if (TransactionSynchronizationManager.isSynchronizationActive()) {
            TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
                @Override
                public void afterCommit() {
                    evictByPattern(pattern);
                }
            });
        } else {
            // 无事务上下文，直接清除
            evictByPattern(pattern);
        }
    }
}
