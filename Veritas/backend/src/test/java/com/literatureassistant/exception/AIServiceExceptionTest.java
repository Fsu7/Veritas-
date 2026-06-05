package com.literatureassistant.exception;

import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.net.ConnectException;
import java.util.concurrent.TimeoutException;

import static org.junit.jupiter.api.Assertions.*;

class AIServiceExceptionTest {

    @Test
    void codeIs502() {
        AIServiceException ex = new AIServiceException("AI服务调用失败", new IOException("Connection refused"));
        assertEquals(502, ex.getCode());
    }

    @Test
    void errorKeyIsAiServiceError() {
        AIServiceException ex = new AIServiceException("AI服务调用失败", new IOException("Connection refused"));
        assertEquals("AI_SERVICE_ERROR", ex.getErrorKey());
    }

    @Test
    void causeIsPreserved() {
        IOException cause = new IOException("Connection refused");
        AIServiceException ex = new AIServiceException("AI服务调用失败", cause);
        assertSame(cause, ex.getCause());
        assertEquals("Connection refused", ex.getCause().getMessage());
    }

    @Test
    void isBusinessException() {
        AIServiceException ex = new AIServiceException("test", new RuntimeException());
        assertTrue(ex instanceof BusinessException);
    }

    @Test
    void differentCauseTypes() {
        AIServiceException ex1 = new AIServiceException("连接超时", new TimeoutException("30s elapsed"));
        AIServiceException ex2 = new AIServiceException("连接拒绝", new ConnectException("Connection refused"));

        assertEquals(502, ex1.getCode());
        assertEquals(502, ex2.getCode());
        assertInstanceOf(TimeoutException.class, ex1.getCause());
        assertInstanceOf(ConnectException.class, ex2.getCause());
    }

    @Test
    void messageIsPassedCorrectly() {
        AIServiceException ex = new AIServiceException("Python服务不可用", new RuntimeException("err"));
        assertEquals("Python服务不可用", ex.getMessage());
    }
}
