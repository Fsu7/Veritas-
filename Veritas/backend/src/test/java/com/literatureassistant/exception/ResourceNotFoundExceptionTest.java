package com.literatureassistant.exception;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class ResourceNotFoundExceptionTest {

    @Test
    void codeIs404() {
        ResourceNotFoundException ex = new ResourceNotFoundException("User", "usr_001");
        assertEquals(404, ex.getCode());
    }

    @Test
    void errorKeyIsResourceNotFound() {
        ResourceNotFoundException ex = new ResourceNotFoundException("User", "usr_001");
        assertEquals("RESOURCE_NOT_FOUND", ex.getErrorKey());
    }

    @Test
    void messageFormat() {
        ResourceNotFoundException ex = new ResourceNotFoundException("User", "usr_001");
        assertEquals("User not found: usr_001", ex.getMessage());
    }

    @Test
    void isBusinessException() {
        ResourceNotFoundException ex = new ResourceNotFoundException("Paper", "paper_001");
        assertTrue(ex instanceof BusinessException);
    }

    @Test
    void differentResourceTypes() {
        ResourceNotFoundException ex1 = new ResourceNotFoundException("User", "usr_001");
        ResourceNotFoundException ex2 = new ResourceNotFoundException("Paper", "paper_123");
        ResourceNotFoundException ex3 = new ResourceNotFoundException("Session", "sess_456");

        assertEquals("User not found: usr_001", ex1.getMessage());
        assertEquals("Paper not found: paper_123", ex2.getMessage());
        assertEquals("Session not found: sess_456", ex3.getMessage());
    }
}
