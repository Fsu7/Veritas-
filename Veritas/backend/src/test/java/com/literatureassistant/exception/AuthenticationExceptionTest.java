package com.literatureassistant.exception;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class AuthenticationExceptionTest {

    @Test
    void codeIs401() {
        AuthenticationException ex = new AuthenticationException("Token已过期");
        assertEquals(401, ex.getCode());
    }

    @Test
    void errorKeyIsAuthenticationFailed() {
        AuthenticationException ex = new AuthenticationException("Token已过期");
        assertEquals("AUTHENTICATION_FAILED", ex.getErrorKey());
    }

    @Test
    void messageIsPassedCorrectly() {
        AuthenticationException ex = new AuthenticationException("Token已过期");
        assertEquals("Token已过期", ex.getMessage());
    }

    @Test
    void isBusinessException() {
        AuthenticationException ex = new AuthenticationException("test");
        assertTrue(ex instanceof BusinessException);
    }

    @Test
    void differentMessages() {
        AuthenticationException ex1 = new AuthenticationException("Token已过期");
        AuthenticationException ex2 = new AuthenticationException("认证失败");
        assertEquals("Token已过期", ex1.getMessage());
        assertEquals("认证失败", ex2.getMessage());
        assertEquals(401, ex1.getCode());
        assertEquals(401, ex2.getCode());
    }
}
