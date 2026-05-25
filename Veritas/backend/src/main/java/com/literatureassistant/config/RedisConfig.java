package com.literatureassistant.config;

import com.fasterxml.jackson.databind.ObjectMapper;
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
    public RedisCacheManager cacheManager(RedisConnectionFactory factory) {
        RedisCacheConfiguration defaultConfig = RedisCacheConfiguration.defaultCacheConfig()
                .entryTtl(Duration.ofMinutes(30))
                .serializeKeysWith(RedisSerializationContext.SerializationPair
                        .fromSerializer(new StringRedisSerializer()))
                .serializeValuesWith(RedisSerializationContext.SerializationPair
                        .fromSerializer(new GenericJackson2JsonRedisSerializer()));

        Map<String, RedisCacheConfiguration> cacheConfigurations = new HashMap<>();
        cacheConfigurations.put("userProfile", defaultConfig.entryTtl(applyJitter(Duration.ofHours(1))));
        cacheConfigurations.put("userInfo", defaultConfig.entryTtl(applyJitter(Duration.ofHours(1))));
        cacheConfigurations.put("paperDetail", defaultConfig.entryTtl(applyJitter(Duration.ofMinutes(30))));
        cacheConfigurations.put("paperSearch", defaultConfig.entryTtl(applyJitter(Duration.ofMinutes(10))));
        cacheConfigurations.put("analysisResult", defaultConfig.entryTtl(applyJitter(Duration.ofMinutes(30))));
        cacheConfigurations.put("sessionState", defaultConfig.entryTtl(applyJitter(Duration.ofHours(2))));

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
