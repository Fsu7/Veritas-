package com.literatureassistant.controller;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class HealthControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    @DisplayName("GET /health 返回200状态码和ApiResponse格式")
    void testHealthEndpointReturns200() throws Exception {
        mockMvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.message").value("success"))
                .andExpect(jsonPath("$.timestamp").isNumber());
    }

    @Test
    @DisplayName("GET /health 响应包含status/mysql/redis/timestamp字段")
    void testHealthEndpointContainsRequiredFields() throws Exception {
        mockMvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.status").exists())
                .andExpect(jsonPath("$.data.mysql").exists())
                .andExpect(jsonPath("$.data.redis").exists());
    }

    @Test
    @DisplayName("MySQL和Redis可用时status=UP")
    void testHealthEndpointStatusUpWhenServicesAvailable() throws Exception {
        mockMvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.status").value("UP"))
                .andExpect(jsonPath("$.data.mysql").value("UP"))
                .andExpect(jsonPath("$.data.redis").value("UP"));
    }
}
