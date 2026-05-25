package com.literatureassistant.exception;

import org.junit.jupiter.api.Test;

import java.io.IOException;

import static org.junit.jupiter.api.Assertions.*;

class BusinessExceptionTest {

    @Test
    void constructorWithCodeAndMessage() {
        BusinessException ex = new BusinessException(400, "参数错误");
        assertEquals(400, ex.getCode());
        assertEquals("参数错误", ex.getMessage());
        assertEquals("", ex.getErrorKey());
        assertNull(ex.getCause());
    }

    @Test
    void constructorWithCodeMessageAndErrorKey() {
        BusinessException ex = new BusinessException(409, "用户名已存在", "USERNAME_DUPLICATE");
        assertEquals(409, ex.getCode());
        assertEquals("用户名已存在", ex.getMessage());
        assertEquals("USERNAME_DUPLICATE", ex.getErrorKey());
        assertNull(ex.getCause());
    }

    @Test
    void constructorWithCodeMessageAndCause() {
        IOException cause = new IOException("Connection refused");
        BusinessException ex = new BusinessException(500, "服务调用失败", cause);
        assertEquals(500, ex.getCode());
        assertEquals("服务调用失败", ex.getMessage());
        assertEquals("", ex.getErrorKey());
        assertNotNull(ex.getCause());
        assertSame(cause, ex.getCause());
    }

    @Test
    void constructorWithAllParams() {
        RuntimeException cause = new RuntimeException("root cause");
        BusinessException ex = new BusinessException(503, "服务不可用", cause, "SERVICE_DOWN");
        assertEquals(503, ex.getCode());
        assertEquals("服务不可用", ex.getMessage());
        assertEquals("SERVICE_DOWN", ex.getErrorKey());
        assertSame(cause, ex.getCause());
    }

    @Test
    void isRuntimeException() {
        BusinessException ex = new BusinessException(400, "test");
        assertTrue(ex instanceof RuntimeException);
    }

    @Test
    void defaultErrorKeyIsEmptyString() {
        BusinessException ex1 = new BusinessException(400, "msg");
        BusinessException ex2 = new BusinessException(400, "msg", new RuntimeException());
        assertEquals("", ex1.getErrorKey());
        assertEquals("", ex2.getErrorKey());
    }
}
