package com.literatureassistant.service;

import com.literatureassistant.dto.request.LoginRequest;
import com.literatureassistant.dto.request.RegisterRequest;
import com.literatureassistant.dto.request.UserUpdateRequest;
import com.literatureassistant.dto.response.LoginResponse;
import com.literatureassistant.dto.response.UserResponse;
import com.literatureassistant.entity.User;
import com.literatureassistant.exception.AuthenticationException;
import com.literatureassistant.exception.BusinessException;
import com.literatureassistant.exception.ResourceNotFoundException;
import com.literatureassistant.mapper.UserMapper;
import com.literatureassistant.repository.UserProfileRepository;
import com.literatureassistant.repository.UserRepository;
import com.literatureassistant.util.JwtUtil;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class UserServiceTest {

    @InjectMocks
    private UserService userService;

    @Mock
    private UserRepository userRepository;

    @Mock
    private UserProfileRepository userProfileRepository;

    @Mock
    private JwtUtil jwtUtil;

    @Mock
    private PasswordEncoder passwordEncoder;

    @Mock
    private UserMapper userMapper;

    @Mock
    private com.fasterxml.jackson.databind.ObjectMapper objectMapper;

    @Mock
    private org.springframework.data.redis.core.RedisTemplate<String, String> redisTemplate;

    private RegisterRequest registerRequest;
    private LoginRequest loginRequest;
    private User testUser;

    @BeforeEach
    void setUp() {
        registerRequest = RegisterRequest.builder()
                .username("testuser")
                .email("test@example.com")
                .password("password123")
                .build();

        loginRequest = LoginRequest.builder()
                .username("testuser")
                .password("password123")
                .build();

        testUser = User.builder()
                .userId("usr_test1234")
                .username("testuser")
                .email("test@example.com")
                .passwordHash("$2a$10$hashedpassword")
                .build();
    }

    @Test
    @DisplayName("register - 正常注册返回UserResponse，hasProfile为false")
    void register_normal_returnsUserResponseWithFalseHasProfile() {
        when(userRepository.existsByUsername("testuser")).thenReturn(false);
        when(userRepository.existsByEmail("test@example.com")).thenReturn(false);
        when(passwordEncoder.encode("password123")).thenReturn("$2a$10$hashedpassword");
        when(userRepository.save(any(User.class))).thenReturn(testUser);

        UserResponse expectedResponse = UserResponse.builder()
                .userId("usr_test1234")
                .username("testuser")
                .email("test@example.com")
                .hasProfile(false)
                .build();
        when(userMapper.toUserResponse(any(User.class), any(Boolean.class))).thenReturn(expectedResponse);

        UserResponse response = userService.register(registerRequest);

        assertThat(response).isNotNull();
        assertThat(response.getUserId()).startsWith("usr_");
        assertThat(response.getUsername()).isEqualTo("testuser");
        assertThat(response.isHasProfile()).isFalse();

        verify(userRepository).save(any(User.class));
        verify(userProfileRepository, never()).existsByUserId(anyString());
    }

    @Test
    @DisplayName("register - 用户名重复抛出BusinessException")
    void register_duplicateUsername_throwsBusinessException() {
        when(userRepository.existsByUsername("testuser")).thenReturn(true);

        assertThatThrownBy(() -> userService.register(registerRequest))
                .isInstanceOf(BusinessException.class)
                .hasMessageContaining("用户名已存在");
    }

    @Test
    @DisplayName("register - 邮箱重复抛出BusinessException")
    void register_duplicateEmail_throwsBusinessException() {
        when(userRepository.existsByUsername("testuser")).thenReturn(false);
        when(userRepository.existsByEmail("test@example.com")).thenReturn(true);

        assertThatThrownBy(() -> userService.register(registerRequest))
                .isInstanceOf(BusinessException.class)
                .hasMessageContaining("邮箱已被注册");
    }

    @Test
    @DisplayName("login - 正常登录返回LoginResponse")
    void login_normal_returnsLoginResponse() {
        when(userRepository.findByUsername("testuser")).thenReturn(Optional.of(testUser));
        when(passwordEncoder.matches("password123", "$2a$10$hashedpassword")).thenReturn(true);
        when(jwtUtil.generateToken("usr_test1234", "testuser")).thenReturn("jwt-token");
        when(userProfileRepository.existsByUserId("usr_test1234")).thenReturn(false);

        LoginResponse response = userService.login(loginRequest);

        assertThat(response).isNotNull();
        assertThat(response.getToken()).isEqualTo("jwt-token");
        assertThat(response.getUserId()).isEqualTo("usr_test1234");
        assertThat(response.getUsername()).isEqualTo("testuser");
        assertThat(response.isHasProfile()).isFalse();
    }

    @Test
    @DisplayName("login - 用户不存在抛出AuthenticationException")
    void login_userNotFound_throwsAuthenticationException() {
        when(userRepository.findByUsername("testuser")).thenReturn(Optional.empty());

        assertThatThrownBy(() -> userService.login(loginRequest))
                .isInstanceOf(AuthenticationException.class)
                .hasMessageContaining("用户名或密码错误");
    }

    @Test
    @DisplayName("login - 密码错误抛出AuthenticationException")
    void login_wrongPassword_throwsAuthenticationException() {
        when(userRepository.findByUsername("testuser")).thenReturn(Optional.of(testUser));
        when(passwordEncoder.matches("password123", "$2a$10$hashedpassword")).thenReturn(false);

        assertThatThrownBy(() -> userService.login(loginRequest))
                .isInstanceOf(AuthenticationException.class)
                .hasMessageContaining("用户名或密码错误");
    }

    @Test
    @DisplayName("getUserInfo - 用户不存在抛出ResourceNotFoundException")
    void getUserInfo_notFound_throwsResourceNotFoundException() {
        when(userRepository.findByUserId("usr_test1234")).thenReturn(Optional.empty());

        assertThatThrownBy(() -> userService.getUserInfo("usr_test1234"))
                .isInstanceOf(ResourceNotFoundException.class);
    }

    @Test
    @DisplayName("logout - 正常登出调用blacklistToken")
    void logout_normal_callsBlacklistToken() {
        when(jwtUtil.getTokenJti("token")).thenReturn("jti-123");
        when(jwtUtil.blacklistToken("token")).thenReturn(true);

        userService.logout("token");

        verify(jwtUtil).blacklistToken("token");
    }

    @Test
    @DisplayName("logout - jti为null直接返回")
    void logout_nullJti_returnsEarly() {
        when(jwtUtil.getTokenJti("token")).thenReturn(null);

        userService.logout("token");

        verify(jwtUtil, never()).blacklistToken(anyString());
    }

    @Test
    @DisplayName("logoutWithAuth - null token抛出BusinessException")
    void logoutWithAuth_nullToken_throwsBusinessException() {
        when(jwtUtil.extractBearerToken("Bearer invalid")).thenReturn(null);

        assertThatThrownBy(() -> userService.logoutWithAuth("Bearer invalid"))
                .isInstanceOf(BusinessException.class)
                .hasFieldOrPropertyWithValue("errorKey", "INVALID_AUTH_HEADER");
    }

    @Test
    @DisplayName("logoutWithAuth - 无效Token抛出BusinessException")
    void logoutWithAuth_invalidToken_throwsBusinessException() {
        when(jwtUtil.extractBearerToken("Bearer expired-token")).thenReturn("expired-token");
        when(jwtUtil.getUserIdFromToken("expired-token")).thenReturn(null);

        assertThatThrownBy(() -> userService.logoutWithAuth("Bearer expired-token"))
                .isInstanceOf(BusinessException.class)
                .hasFieldOrPropertyWithValue("errorKey", "INVALID_TOKEN");
    }

    @Test
    @DisplayName("updateUser - 正常更新返回UserResponse")
    void updateUser_normal_returnsUserResponse() {
        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken("usr_test1234", null, java.util.List.of()));

        UserUpdateRequest request = UserUpdateRequest.builder()
                .username("newusername")
                .build();

        when(userRepository.findByUserId("usr_test1234")).thenReturn(Optional.of(testUser));
        when(userRepository.existsByUsername("newusername")).thenReturn(false);
        when(userRepository.save(any(User.class))).thenReturn(testUser);
        when(userProfileRepository.existsByUserId("usr_test1234")).thenReturn(false);

        UserResponse expectedResponse = UserResponse.builder()
                .userId("usr_test1234")
                .username("newusername")
                .email("test@example.com")
                .hasProfile(false)
                .build();
        when(userMapper.toUserResponse(any(User.class), any(Boolean.class))).thenReturn(expectedResponse);

        UserResponse response = userService.updateUser("usr_test1234", request);

        assertThat(response).isNotNull();
        verify(userRepository).save(any(User.class));
    }

    @Test
    @DisplayName("updateUser - 用户名重复抛出BusinessException")
    void updateUser_duplicateUsername_throwsBusinessException() {
        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken("usr_test1234", null, java.util.List.of()));

        UserUpdateRequest request = UserUpdateRequest.builder()
                .username("duplicate")
                .build();

        when(userRepository.findByUserId("usr_test1234")).thenReturn(Optional.of(testUser));
        when(userRepository.existsByUsername("duplicate")).thenReturn(true);

        assertThatThrownBy(() -> userService.updateUser("usr_test1234", request))
                .isInstanceOf(BusinessException.class)
                .hasMessageContaining("用户名已存在");
    }
}
