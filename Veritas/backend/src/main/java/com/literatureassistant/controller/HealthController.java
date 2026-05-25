package com.literatureassistant.controller;

import com.literatureassistant.dto.common.ApiResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisCallback;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.Statement;
import java.util.HashMap;
import java.util.Map;

@RestController
@Slf4j
public class HealthController {

    private final DataSource dataSource;
    private final RedisTemplate<String, String> redisTemplate;

    public HealthController(DataSource dataSource, RedisTemplate<String, String> redisTemplate) {
        this.dataSource = dataSource;
        this.redisTemplate = redisTemplate;
    }

    @GetMapping("/health")
    public ApiResponse<Map<String, Object>> health() {
        Map<String, Object> healthData = new HashMap<>();

        String mysqlStatus = checkMySQL();
        String redisStatus = checkRedis();

        String overallStatus = "UP".equals(mysqlStatus) && "UP".equals(redisStatus) ? "UP" : "DOWN";

        healthData.put("status", overallStatus);
        healthData.put("mysql", mysqlStatus);
        healthData.put("redis", redisStatus);

        return ApiResponse.success(healthData);
    }

    private String checkMySQL() {
        try (Connection connection = dataSource.getConnection();
             Statement statement = connection.createStatement();
             ResultSet resultSet = statement.executeQuery("SELECT 1")) {
            if (resultSet.next()) {
                return "UP";
            }
            return "DOWN";
        } catch (Exception e) {
            log.warn("MySQL health check failed: {}", e.getMessage());
            return "DOWN";
        }
    }

    private String checkRedis() {
        try {
            String result = redisTemplate.execute((RedisCallback<String>) connection -> {
                Object pong = connection.ping();
                return pong != null ? pong.toString() : null;
            });
            if ("PONG".equalsIgnoreCase(result)) {
                return "UP";
            }
            return "DOWN";
        } catch (Exception e) {
            log.warn("Redis health check failed: {}", e.getMessage());
            return "DOWN";
        }
    }
}
