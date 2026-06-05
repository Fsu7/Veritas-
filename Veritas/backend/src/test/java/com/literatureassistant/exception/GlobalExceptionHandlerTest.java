package com.literatureassistant.exception;

import com.literatureassistant.dto.common.ApiResponse;
import jakarta.validation.Valid;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.core.MethodParameter;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
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
        ResponseEntity<ApiResponse<Void>> response = handler.handleValidation(e);

        assertEquals(HttpStatus.BAD_REQUEST, response.getStatusCode());
        assertEquals(400, response.getBody().getCode());
        assertTrue(response.getBody().getMessage().contains("username: 用户名不能为空"));
        assertTrue(response.getBody().getMessage().contains("email: 邮箱格式不正确"));
        assertTrue(response.getBody().getMessage().contains(";"));
        assertNull(response.getBody().getData());
    }

    @Test
    void handleValidationSingleField() throws NoSuchMethodException {
        BeanPropertyBindingResult bindingResult = new BeanPropertyBindingResult(new Object(), "request");
        bindingResult.addError(new FieldError("request", "title", "标题不能为空"));

        MethodArgumentNotValidException e = createValidationException(bindingResult);
        ResponseEntity<ApiResponse<Void>> response = handler.handleValidation(e);

        assertEquals(HttpStatus.BAD_REQUEST, response.getStatusCode());
        assertEquals(400, response.getBody().getCode());
        assertEquals("title: 标题不能为空", response.getBody().getMessage());
    }

    @Test
    void handleAuth() {
        AuthenticationException e = new AuthenticationException("Token已过期");
        ResponseEntity<ApiResponse<Void>> response = handler.handleAuth(e);

        assertEquals(HttpStatus.UNAUTHORIZED, response.getStatusCode());
        assertEquals(401, response.getBody().getCode());
        assertEquals("Token已过期", response.getBody().getMessage());
        assertNull(response.getBody().getData());
    }

    @Test
    void handleNotFound() {
        ResourceNotFoundException e = new ResourceNotFoundException("User", "usr_001");
        ResponseEntity<ApiResponse<Void>> response = handler.handleNotFound(e);

        assertEquals(HttpStatus.NOT_FOUND, response.getStatusCode());
        assertEquals(404, response.getBody().getCode());
        assertEquals("User not found: usr_001", response.getBody().getMessage());
        assertNull(response.getBody().getData());
    }

    @Test
    void handleAIService() {
        AIServiceException e = new AIServiceException("Python服务内部错误", new IOException("Connection refused"));
        ResponseEntity<ApiResponse<Void>> response = handler.handleAIService(e);

        // 修复 S-002: AIServiceException 改为 502 Bad Gateway
        assertEquals(HttpStatus.BAD_GATEWAY, response.getStatusCode());
        assertEquals(502, response.getBody().getCode());
        assertEquals("AI服务暂时不可用，请稍后重试", response.getBody().getMessage());
        assertNull(response.getBody().getData());
    }

    @Test
    void handleAIServiceDoesNotExposeInternalDetails() {
        AIServiceException e = new AIServiceException("Python服务返回500: NullPointerException at com.xxx.Service", new RuntimeException("NPE"));
        ResponseEntity<ApiResponse<Void>> response = handler.handleAIService(e);

        // 修复 S-002: AIServiceException 改为 502 Bad Gateway
        assertEquals(HttpStatus.BAD_GATEWAY, response.getStatusCode());
        assertEquals(502, response.getBody().getCode());
        assertEquals("AI服务暂时不可用，请稍后重试", response.getBody().getMessage());
        assertFalse(response.getBody().getMessage().contains("Python"));
        assertFalse(response.getBody().getMessage().contains("NullPointerException"));
    }

    @Test
    void handleBusiness() {
        BusinessException e = new BusinessException(409, "用户名已存在", "USERNAME_DUPLICATE");
        ResponseEntity<ApiResponse<Void>> response = handler.handleBusiness(e);

        assertEquals(HttpStatus.CONFLICT, response.getStatusCode());
        assertEquals(409, response.getBody().getCode());
        assertEquals("用户名已存在", response.getBody().getMessage());
        assertNull(response.getBody().getData());
    }

    @Test
    void handleGeneral() {
        Exception e = new RuntimeException("Some unexpected error");
        ResponseEntity<ApiResponse<Void>> response = handler.handleGeneral(e);

        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, response.getStatusCode());
        assertEquals(500, response.getBody().getCode());
        assertEquals("服务器内部错误", response.getBody().getMessage());
        assertNull(response.getBody().getData());
    }

    @Test
    void handleGeneralDoesNotExposeInternalDetails() {
        Exception e = new NullPointerException("database password is xxx");
        ResponseEntity<ApiResponse<Void>> response = handler.handleGeneral(e);

        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, response.getStatusCode());
        assertEquals(500, response.getBody().getCode());
        assertEquals("服务器内部错误", response.getBody().getMessage());
        assertFalse(response.getBody().getMessage().contains("NullPointerException"));
        assertFalse(response.getBody().getMessage().contains("database"));
        assertFalse(response.getBody().getMessage().contains("password"));
    }

    @Test
    void handleBusinessWithDefaultCode() {
        BusinessException e = new BusinessException(400, "参数错误");
        ResponseEntity<ApiResponse<Void>> response = handler.handleBusiness(e);

        assertEquals(HttpStatus.BAD_REQUEST, response.getStatusCode());
        assertEquals(400, response.getBody().getCode());
        assertEquals("参数错误", response.getBody().getMessage());
    }
}
