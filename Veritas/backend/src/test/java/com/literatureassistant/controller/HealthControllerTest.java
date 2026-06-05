package com.literatureassistant.controller;

import com.literatureassistant.dto.common.ApiResponse;
import com.literatureassistant.service.AgentClientService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.core.RedisCallback;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.Statement;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * HealthController 单元测试（task23 扩展 — 含 aiService 字段）。
 * <p>改用 Mockito standalone 测试，Mock DataSource / RedisTemplate / AgentClientService。
 *
 * @author XH-202630 Literature Assistant
 */
@ExtendWith(MockitoExtension.class)
class HealthControllerTest {

    @Mock
    private DataSource dataSource;

    @Mock
    private RedisTemplate<String, String> redisTemplate;

    @Mock
    private AgentClientService agentClientService;

    private MockMvc mockMvc;

    @BeforeEach
    void setUp() throws Exception {
        // Mock MySQL: UP
        Connection connection = org.mockito.Mockito.mock(Connection.class);
        Statement statement = org.mockito.Mockito.mock(Statement.class);
        ResultSet resultSet = org.mockito.Mockito.mock(ResultSet.class);
        when(dataSource.getConnection()).thenReturn(connection);
        when(connection.createStatement()).thenReturn(statement);
        when(statement.executeQuery("SELECT 1")).thenReturn(resultSet);
        when(resultSet.next()).thenReturn(true);

        // Mock Redis: PONG
        when(redisTemplate.execute(any(RedisCallback.class))).thenReturn("PONG");

        HealthController controller = new HealthController(dataSource, redisTemplate, agentClientService);
        mockMvc = MockMvcBuilders.standaloneSetup(controller).build();
    }

    @Test
    @DisplayName("GET /health 返回200 + ApiResponse 格式")
    void testHealthEndpointReturns200() throws Exception {
        when(agentClientService.isHealthy()).thenReturn(true);

        mockMvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.message").value("success"));
    }

    @Test
    @DisplayName("GET /health 响应包含 status/mysql/redis/aiService 字段")
    void testHealthEndpointContainsRequiredFields() throws Exception {
        when(agentClientService.isHealthy()).thenReturn(true);

        mockMvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.status").exists())
                .andExpect(jsonPath("$.data.mysql").exists())
                .andExpect(jsonPath("$.data.redis").exists())
                .andExpect(jsonPath("$.data.aiService").exists());
    }

    @Test
    @DisplayName("所有服务 UP 时 status=UP")
    void testHealthEndpointStatusUpWhenServicesAvailable() throws Exception {
        when(agentClientService.isHealthy()).thenReturn(true);

        mockMvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.status").value("UP"))
                .andExpect(jsonPath("$.data.mysql").value("UP"))
                .andExpect(jsonPath("$.data.redis").value("UP"))
                .andExpect(jsonPath("$.data.aiService").value("UP"));
    }

    @Test
    @DisplayName("AI 服务可用时 aiService=UP, 整体 status=UP")
    void healthController_includes_aiService_field() throws Exception {
        when(agentClientService.isHealthy()).thenReturn(true);

        mockMvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.aiService").value("UP"))
                .andExpect(jsonPath("$.data.status").value("UP"));
    }

    @Test
    @DisplayName("Python AI 服务不可用时 aiService=DOWN, 整体 status=DOWN")
    void healthController_python_down_returns_DOWN() throws Exception {
        when(agentClientService.isHealthy()).thenReturn(false);

        mockMvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.aiService").value("DOWN"))
                .andExpect(jsonPath("$.data.status").value("DOWN"));
    }
}
