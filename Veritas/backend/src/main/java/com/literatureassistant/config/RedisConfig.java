package com.literatureassistant.config;

import com.fasterxml.jackson.annotation.JsonTypeInfo;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.databind.jsontype.BasicPolymorphicTypeValidator;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.springframework.cache.annotation.EnableCaching;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.cache.RedisCacheConfiguration;
import org.springframework.data.redis.cache.RedisCacheManager;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.serializer.GenericJackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.RedisSerializationContext;
import org.springframework.data.redis.serializer.StringRedisSerializer;

import java.time.Duration;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ThreadLocalRandom;

@Configuration
@EnableCaching
public class RedisConfig {

    private static final double TTL_JITTER_RATIO = 0.1;

    @Bean
    public GenericJackson2JsonRedisSerializer jsonRedisSerializer() {
        ObjectMapper om = new ObjectMapper();
        om.registerModule(new JavaTimeModule());
        om.disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
        om.activateDefaultTyping(
                BasicPolymorphicTypeValidator.builder()
                        .allowIfSubType("com.literatureassistant.")
                        .allowIfSubType("java.util.")
                        .allowIfSubType("java.time.")
                        .allowIfSubType("java.lang.")
                        .build(),
                ObjectMapper.DefaultTyping.NON_FINAL,
                JsonTypeInfo.As.PROPERTY);
        return new GenericJackson2JsonRedisSerializer(om);
    }

    @Bean
    public RedisCacheManager cacheManager(RedisConnectionFactory factory,
                                          GenericJackson2JsonRedisSerializer jsonRedisSerializer) {
        // Task 12.3: 缓存穿透防护策略
        // Spring Data Redis 默认允许缓存 null 值（DEFAULT_CACHE_NULL_VALUES=true），
        // 当 Service 层的 @Cacheable 方法不使用 unless="#result == null" 时，
        // Spring Cache 会将 null 结果以内部 null marker 写入 Redis（TTL 同缓存空间配置），
        // 避免不存在的 key 反复击穿到 DB。
        // 注意：现有 @Cacheable 方法（getPaperDetail/getAnalysisResult/listFavorites）
        // 仍保留 unless="#result == null"（按既有测试 CachePenetrationAvalancheTest 约定，
        // 这些方法不缓存 null）；如需为特定查询启用穿透防护，新建 @Cacheable 方法时
        // 去掉 unless 即可，本配置已为其做好准备。
        RedisCacheConfiguration defaultConfig = RedisCacheConfiguration.defaultCacheConfig()
                .entryTtl(Duration.ofMinutes(30))
                .serializeKeysWith(RedisSerializationContext.SerializationPair
                        .fromSerializer(new StringRedisSerializer()))
                .serializeValuesWith(RedisSerializationContext.SerializationPair
                        .fromSerializer(jsonRedisSerializer));

        Map<String, RedisCacheConfiguration> cacheConfigurations = new HashMap<>();
        // 用户相关：TTL=1h（54min~66min with ±10% jitter）
        cacheConfigurations.put("userProfile", defaultConfig.entryTtl(applyJitter(Duration.ofHours(1))));
        // task32: 补齐 userProfileJson 缓存空间配置（修复 @CacheEvict 引用未配置缓存名的 Bug）
        // userProfileJson 用于 syncProfileToRedis 写入的画像 JSON，供 Python AI 服务跨语言读取
        cacheConfigurations.put("userProfileJson", defaultConfig.entryTtl(applyJitter(Duration.ofHours(1))));
        cacheConfigurations.put("userInfo", defaultConfig.entryTtl(applyJitter(Duration.ofHours(1))));
        // 论文相关：TTL=30min / 10min
        cacheConfigurations.put("paperDetail", defaultConfig.entryTtl(applyJitter(Duration.ofMinutes(30))));
        cacheConfigurations.put("paperSearch", defaultConfig.entryTtl(applyJitter(Duration.ofMinutes(10))));
        // task33: 论文列表缓存（与 paperSearch 一致 TTL=10min）
        cacheConfigurations.put("paperList", defaultConfig.entryTtl(applyJitter(Duration.ofMinutes(10))));
        // 分析结果：TTL=30min
        cacheConfigurations.put("analysisResult", defaultConfig.entryTtl(applyJitter(Duration.ofMinutes(30))));
        // 会话状态：TTL=2h
        cacheConfigurations.put("sessionState", defaultConfig.entryTtl(applyJitter(Duration.ofHours(2))));
        // task34: 会话列表缓存（与 paperSearch 一致 TTL=10min）
        cacheConfigurations.put("sessionList", defaultConfig.entryTtl(applyJitter(Duration.ofMinutes(10))));
        // task36: 收藏列表缓存（TTL=10min）
        cacheConfigurations.put("favoriteList", defaultConfig.entryTtl(applyJitter(Duration.ofMinutes(10))));

        return RedisCacheManager.builder(factory)
                .cacheDefaults(defaultConfig)
                .withInitialCacheConfigurations(cacheConfigurations)
                .build();
    }

    @Bean
    public RedisTemplate<String, String> redisTemplate(RedisConnectionFactory factory) {
        RedisTemplate<String, String> template = new RedisTemplate<>();
        template.setConnectionFactory(factory);
        template.setKeySerializer(new StringRedisSerializer());
        template.setValueSerializer(new StringRedisSerializer());
        template.setHashKeySerializer(new StringRedisSerializer());
        template.setHashValueSerializer(new StringRedisSerializer());
        return template;
    }

    private Duration applyJitter(Duration baseTtl) {
        long baseSeconds = baseTtl.getSeconds();
        long jitterSeconds = (long) (baseSeconds * TTL_JITTER_RATIO);
        long randomOffset = ThreadLocalRandom.current().nextLong(-jitterSeconds, jitterSeconds + 1);
        return Duration.ofSeconds(Math.max(1, baseSeconds + randomOffset));
    }
}
