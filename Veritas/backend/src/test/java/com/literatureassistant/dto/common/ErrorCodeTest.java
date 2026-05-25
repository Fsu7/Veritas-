package com.literatureassistant.dto.common;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class ErrorCodeTest {

    @Test
    @DisplayName("所有7个枚举值的code和message正确")
    void testAllErrorCodes() {
        assertEquals(200, ErrorCode.SUCCESS.getCode());
        assertEquals("success", ErrorCode.SUCCESS.getMessage());

        assertEquals(400, ErrorCode.BAD_REQUEST.getCode());
        assertEquals("请求参数错误", ErrorCode.BAD_REQUEST.getMessage());

        assertEquals(401, ErrorCode.UNAUTHORIZED.getCode());
        assertEquals("未认证，请先登录", ErrorCode.UNAUTHORIZED.getMessage());

        assertEquals(403, ErrorCode.FORBIDDEN.getCode());
        assertEquals("无权限访问", ErrorCode.FORBIDDEN.getMessage());

        assertEquals(404, ErrorCode.NOT_FOUND.getCode());
        assertEquals("资源不存在", ErrorCode.NOT_FOUND.getMessage());

        assertEquals(500, ErrorCode.INTERNAL_ERROR.getCode());
        assertEquals("服务器内部错误", ErrorCode.INTERNAL_ERROR.getMessage());

        assertEquals(503, ErrorCode.SERVICE_UNAVAILABLE.getCode());
        assertEquals("服务暂时不可用", ErrorCode.SERVICE_UNAVAILABLE.getMessage());
    }

    @Test
    @DisplayName("枚举值数量为7")
    void testErrorCodeCount() {
        assertEquals(7, ErrorCode.values().length);
    }

    @Test
    @DisplayName("特定code值验证")
    void testSpecificCodeValues() {
        assertEquals(400, ErrorCode.BAD_REQUEST.getCode());
        assertEquals(401, ErrorCode.UNAUTHORIZED.getCode());
        assertEquals(404, ErrorCode.NOT_FOUND.getCode());
        assertEquals(500, ErrorCode.INTERNAL_ERROR.getCode());
        assertEquals(503, ErrorCode.SERVICE_UNAVAILABLE.getCode());
    }

    @Test
    @DisplayName("特定message值验证")
    void testSpecificMessageValues() {
        assertEquals("未认证，请先登录", ErrorCode.UNAUTHORIZED.getMessage());
        assertEquals("无权限访问", ErrorCode.FORBIDDEN.getMessage());
        assertEquals("资源不存在", ErrorCode.NOT_FOUND.getMessage());
    }
}
