package com.literatureassistant.exception;

import com.literatureassistant.dto.common.ApiResponse;
import jakarta.validation.Valid;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.core.MethodParameter;
import org.springframework.validation.BeanPropertyBindingResult;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;

import java.io.IOException;
import java.lang.reflect.Method;

import static org.junit.jupiter.api.Assertions.*;

class GlobalExceptionHandlerTest {

    private GlobalExceptionHandler handler;

    @BeforeEach
    void setUp() {
        handler = new GlobalExceptionHandler();
    }

    @SuppressWarnings("unused")
    public void dummyMethod(@Valid String param) {}

    private MethodArgumentNotValidException createValidationException(BeanPropertyBindingResult bindingResult) throws NoSuchMethodException {
        Method method = GlobalExceptionHandlerTest.class.getMethod("dummyMethod", String.class);
        MethodParameter parameter = new MethodParameter(method, 0);
        return new MethodArgumentNotValidException(parameter, bindingResult);
    }

    @Test
    void handleValidation() throws NoSuchMethodException {
        BeanPropertyBindingResult bindingResult = new BeanPropertyBindingResult(new Object(), "request");
        bindingResult.addError(new FieldError("request", "username", "用户名不能为空"));
        bindingResult.addError(new FieldError("request", "email", "邮箱格式不正确"));

        MethodArgumentNotValidException e = createValidationException(bindingResult);
        ApiResponse<Void> response = handler.handleValidation(e);

        assertEquals(400, response.getCode());
        assertTrue(response.getMessage().contains("username: 用户名不能为空"));
        assertTrue(response.getMessage().contains("email: 邮箱格式不正确"));
        assertTrue(response.getMessage().contains(";"));
        assertNull(response.getData());
    }

    @Test
    void handleValidationSingleField() throws NoSuchMethodException {
        BeanPropertyBindingResult bindingResult = new BeanPropertyBindingResult(new Object(), "request");
        bindingResult.addError(new FieldError("request", "title", "标题不能为空"));

        MethodArgumentNotValidException e = createValidationException(bindingResult);
        ApiResponse<Void> response = handler.handleValidation(e);

        assertEquals(400, response.getCode());
        assertEquals("title: 标题不能为空", response.getMessage());
    }

    @Test
    void handleAuth() {
        AuthenticationException e = new AuthenticationException("Token已过期");
        ApiResponse<Void> response = handler.handleAuth(e);

        assertEquals(401, response.getCode());
        assertEquals("Token已过期", response.getMessage());
        assertNull(response.getData());
    }

    @Test
    void handleNotFound() {
        ResourceNotFoundException e = new ResourceNotFoundException("User", "usr_001");
        ApiResponse<Void> response = handler.handleNotFound(e);

        assertEquals(404, response.getCode());
        assertEquals("User not found: usr_001", response.getMessage());
        assertNull(response.getData());
    }

    @Test
    void handleAIService() {
        AIServiceException e = new AIServiceException("Python服务内部错误", new IOException("Connection refused"));
        ApiResponse<Void> response = handler.handleAIService(e);

        assertEquals(503, response.getCode());
        assertEquals("AI服务暂时不可用，请稍后重试", response.getMessage());
        assertNull(response.getData());
    }

    @Test
    void handleAIServiceDoesNotExposeInternalDetails() {
        AIServiceException e = new AIServiceException("Python服务返回500: NullPointerException at com.xxx.Service", new RuntimeException("NPE"));
        ApiResponse<Void> response = handler.handleAIService(e);

        assertEquals(503, response.getCode());
        assertEquals("AI服务暂时不可用，请稍后重试", response.getMessage());
        assertFalse(response.getMessage().contains("Python"));
        assertFalse(response.getMessage().contains("NullPointerException"));
    }

    @Test
    void handleBusiness() {
        BusinessException e = new BusinessException(409, "用户名已存在", "USERNAME_DUPLICATE");
        ApiResponse<Void> response = handler.handleBusiness(e);

        assertEquals(409, response.getCode());
        assertEquals("用户名已存在", response.getMessage());
        assertNull(response.getData());
    }

    @Test
    void handleGeneral() {
        Exception e = new RuntimeException("Some unexpected error");
        ApiResponse<Void> response = handler.handleGeneral(e);

        assertEquals(500, response.getCode());
        assertEquals("服务器内部错误", response.getMessage());
        assertNull(response.getData());
    }

    @Test
    void handleGeneralDoesNotExposeInternalDetails() {
        Exception e = new NullPointerException("database password is xxx");
        ApiResponse<Void> response = handler.handleGeneral(e);

        assertEquals(500, response.getCode());
        assertEquals("服务器内部错误", response.getMessage());
        assertFalse(response.getMessage().contains("NullPointerException"));
        assertFalse(response.getMessage().contains("database"));
        assertFalse(response.getMessage().contains("password"));
    }

    @Test
    void handleBusinessWithDefaultCode() {
        BusinessException e = new BusinessException(400, "参数错误");
        ApiResponse<Void> response = handler.handleBusiness(e);

        assertEquals(400, response.getCode());
        assertEquals("参数错误", response.getMessage());
    }
}
