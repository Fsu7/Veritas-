package com.literatureassistant.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.literatureassistant.dto.request.LoginRequest;
import com.literatureassistant.dto.request.RegisterRequest;
import com.literatureassistant.dto.request.UserUpdateRequest;
import com.literatureassistant.dto.response.LoginResponse;
import com.literatureassistant.dto.response.UserResponse;
import com.literatureassistant.exception.BusinessException;
import com.literatureassistant.exception.GlobalExceptionHandler;
import com.literatureassistant.service.UserService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.validation.beanvalidation.LocalValidatorFactoryBean;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@ExtendWith(MockitoExtension.class)
class UserControllerTest {

    @InjectMocks
    private UserController userController;

    @Mock
    private UserService userService;

    private MockMvc mockMvc;

    private ObjectMapper objectMapper = new ObjectMapper();

    @BeforeEach
    void setUp() {
        mockMvc = MockMvcBuilders.standaloneSetup(userController)
                .setControllerAdvice(new GlobalExceptionHandler())
                .setValidator(new LocalValidatorFactoryBean())
                .build();
    }

    @Test
    @DisplayName("POST /api/users/register - 正常注册返回201和UserResponse")
    void register_success() throws Exception {
        UserResponse userResponse = UserResponse.builder()
                .userId("usr_test1234")
                .username("testuser")
                .email("test@example.com")
                .hasProfile(false)
                .build();

        when(userService.register(any(RegisterRequest.class))).thenReturn(userResponse);

        RegisterRequest request = RegisterRequest.builder()
                .username("testuser")
                .email("test@example.com")
                .password("password123")
                .build();

        mockMvc.perform(post("/api/users/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.message").value("success"))
                .andExpect(jsonPath("$.data.user_id").value("usr_test1234"))
                .andExpect(jsonPath("$.data.username").value("testuser"))
                .andExpect(jsonPath("$.data.email").value("test@example.com"))
                .andExpect(jsonPath("$.data.has_profile").value(false));
    }

    @Test
    @DisplayName("POST /api/users/register - 参数校验失败(空用户名)返回400")
    void register_validationFail_emptyUsername() throws Exception {
        RegisterRequest request = RegisterRequest.builder()
                .email("test@example.com")
                .password("password123")
                .build();

        mockMvc.perform(post("/api/users/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value(400));
    }

    @Test
    @DisplayName("POST /api/users/login - 正常登录返回200和LoginResponse")
    void login_success() throws Exception {
        LoginResponse loginResponse = LoginResponse.builder()
                .token("mock-jwt-token")
                .userId("usr_test1234")
                .username("testuser")
                .hasProfile(false)
                .build();

        when(userService.login(any(LoginRequest.class))).thenReturn(loginResponse);

        LoginRequest request = LoginRequest.builder()
                .username("testuser")
                .password("password123")
                .build();

        mockMvc.perform(post("/api/users/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.message").value("success"))
                .andExpect(jsonPath("$.data.token").value("mock-jwt-token"))
                .andExpect(jsonPath("$.data.user_id").value("usr_test1234"))
                .andExpect(jsonPath("$.data.username").value("testuser"))
                .andExpect(jsonPath("$.data.has_profile").value(false));
    }

    @Test
    @DisplayName("POST /api/users/login - 参数校验失败(空密码)返回400")
    void login_validationFail_emptyPassword() throws Exception {
        LoginRequest request = LoginRequest.builder()
                .username("testuser")
                .build();

        mockMvc.perform(post("/api/users/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value(400));
    }

    @Test
    @DisplayName("GET /api/users/{userId} - 正常查询返回200和UserResponse")
    void getUserInfo_success() throws Exception {
        UserResponse userResponse = UserResponse.builder()
                .userId("usr_test1234")
                .username("testuser")
                .email("test@example.com")
                .hasProfile(false)
                .build();

        when(userService.getUserInfo("usr_test1234")).thenReturn(userResponse);

        mockMvc.perform(get("/api/users/usr_test1234"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.message").value("success"))
                .andExpect(jsonPath("$.data.user_id").value("usr_test1234"))
                .andExpect(jsonPath("$.data.username").value("testuser"))
                .andExpect(jsonPath("$.data.email").value("test@example.com"))
                .andExpect(jsonPath("$.data.has_profile").value(false));
    }

    @Test
    @DisplayName("PUT /api/users/{userId} - 正常更新返回200和UserResponse")
    void updateUser_success() throws Exception {
        UserResponse userResponse = UserResponse.builder()
                .userId("usr_test1234")
                .username("newusername")
                .email("new@example.com")
                .hasProfile(false)
                .build();

        when(userService.updateUser(any(String.class), any(UserUpdateRequest.class))).thenReturn(userResponse);

        UserUpdateRequest request = UserUpdateRequest.builder()
                .username("newusername")
                .email("new@example.com")
                .build();

        mockMvc.perform(put("/api/users/usr_test1234")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.user_id").value("usr_test1234"))
                .andExpect(jsonPath("$.data.username").value("newusername"));
    }

    @Test
    @DisplayName("POST /api/users/logout - 正常退出返回200")
    void logout_success() throws Exception {
        doNothing().when(userService).logoutWithAuth("Bearer mock-jwt-token");

        mockMvc.perform(post("/api/users/logout")
                        .header("Authorization", "Bearer mock-jwt-token"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.message").value("success"));
    }

    @Test
    @DisplayName("POST /api/users/logout - 无效Token返回401")
    void logout_invalidToken_returns401() throws Exception {
        doThrow(new BusinessException(401, "无效或已过期的Token", "INVALID_TOKEN"))
                .when(userService).logoutWithAuth(any(String.class));

        mockMvc.perform(post("/api/users/logout")
                        .header("Authorization", "Bearer invalid-token"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value(401));
    }
}
