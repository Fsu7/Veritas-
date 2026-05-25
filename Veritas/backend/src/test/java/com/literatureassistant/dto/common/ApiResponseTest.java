package com.literatureassistant.dto.common;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class ApiResponseTest {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Test
    @DisplayName("success(data) 返回 code=200, message=success, data不为null")
    void testSuccessWithData() {
        ApiResponse<String> response = ApiResponse.success("test data");

        assertEquals(200, response.getCode());
        assertEquals("success", response.getMessage());
        assertEquals("test data", response.getData());
        assertTrue(response.getTimestamp() > 0);
    }

    @Test
    @DisplayName("success(null) 返回 code=200, data=null")
    void testSuccessWithNullData() {
        ApiResponse<Void> response = ApiResponse.success(null);

        assertEquals(200, response.getCode());
        assertEquals("success", response.getMessage());
        assertNull(response.getData());
    }

    @Test
    @DisplayName("error(code, message) 返回对应code和message, data=null")
    void testErrorWithCodeAndMessage() {
        ApiResponse<Void> response = ApiResponse.error(400, "参数错误");

        assertEquals(400, response.getCode());
        assertEquals("参数错误", response.getMessage());
        assertNull(response.getData());
        assertTrue(response.getTimestamp() > 0);
    }

    @Test
    @DisplayName("error(ErrorCode) 从枚举获取code和message")
    void testErrorWithErrorCode() {
        ApiResponse<Void> response = ApiResponse.error(ErrorCode.NOT_FOUND);

        assertEquals(404, response.getCode());
        assertEquals("资源不存在", response.getMessage());
        assertNull(response.getData());
    }

    @Test
    @DisplayName("error响应JSON中不包含data字段")
    void testErrorDataNullNotSerialized() throws Exception {
        ApiResponse<Void> response = ApiResponse.error(401, "未认证");
        String json = objectMapper.writeValueAsString(response);

        assertFalse(json.contains("\"data\""));
        assertTrue(json.contains("\"code\":401"));
        assertTrue(json.contains("\"message\":\"未认证\""));
        assertTrue(json.contains("\"timestamp\""));
    }

    @Test
    @DisplayName("success响应JSON中包含data字段")
    void testSuccessDataSerialized() throws Exception {
        ApiResponse<String> response = ApiResponse.success("hello");
        String json = objectMapper.writeValueAsString(response);

        assertTrue(json.contains("\"data\":\"hello\""));
        assertTrue(json.contains("\"code\":200"));
    }

    @Test
    @DisplayName("timestamp接近当前时间")
    void testTimestampIsCurrentTime() {
        long before = System.currentTimeMillis();
        ApiResponse<String> response = ApiResponse.success("test");
        long after = System.currentTimeMillis();

        assertTrue(response.getTimestamp() >= before);
        assertTrue(response.getTimestamp() <= after);
    }

    @Test
    @DisplayName("Builder模式正常工作")
    void testBuilderPattern() {
        ApiResponse<Integer> response = ApiResponse.<Integer>builder()
                .code(201)
                .message("created")
                .data(42)
                .timestamp(1000L)
                .build();

        assertEquals(201, response.getCode());
        assertEquals("created", response.getMessage());
        assertEquals(42, response.getData());
        assertEquals(1000L, response.getTimestamp());
    }
}
