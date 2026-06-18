package com.literatureassistant.controller;

import com.literatureassistant.dto.common.ApiResponse;
import com.literatureassistant.dto.request.LoginRequest;
import com.literatureassistant.dto.request.ProfileUpdateRequest;
import com.literatureassistant.dto.request.RegisterRequest;
import com.literatureassistant.dto.request.UserUpdateRequest;
import com.literatureassistant.dto.response.LoginResponse;
import com.literatureassistant.dto.response.ProfileResponse;
import com.literatureassistant.dto.response.UserResponse;
import com.literatureassistant.exception.AuthenticationException;
import com.literatureassistant.exception.BusinessException;
import com.literatureassistant.service.UserService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/users")
@RequiredArgsConstructor
@Slf4j
public class UserController {

    private final UserService userService;

    @PostMapping("/register")
    public ResponseEntity<ApiResponse<UserResponse>> register(@Valid @RequestBody RegisterRequest request) {
        UserResponse response = userService.register(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.success(response));
    }

    @PostMapping("/login")
    public ApiResponse<LoginResponse> login(@Valid @RequestBody LoginRequest request) {
        LoginResponse response = userService.login(request);
        return ApiResponse.success(response);
    }

    @GetMapping("/{userId}")
    public ApiResponse<UserResponse> getUserInfo(@PathVariable String userId) {
        // 修复 B-005: @Cacheable 命中时 Service 方法体不执行，数据隔离校验必须上移到 Controller
        validateUserIdMatch(userId);
        UserResponse response = userService.getUserInfo(userId);
        return ApiResponse.success(response);
    }

    @PutMapping("/{userId}")
    public ApiResponse<UserResponse> updateUser(@PathVariable String userId,
                                                 @Valid @RequestBody UserUpdateRequest request) {
        UserResponse response = userService.updateUser(userId, request);
        return ApiResponse.success(response);
    }

    @PostMapping("/logout")
    public ApiResponse<Void> logout(@RequestHeader("Authorization") String authHeader) {
        userService.logoutWithAuth(authHeader);
        return ApiResponse.success(null);
    }

    @GetMapping("/{userId}/profile")
    public ApiResponse<ProfileResponse> getProfile(@PathVariable String userId) {
        // 修复 B-001: @Cacheable 命中时 Service 方法体不执行，数据隔离校验必须上移到 Controller
        validateUserIdMatch(userId);
        ProfileResponse response = userService.getProfile(userId);
        return ApiResponse.success(response);
    }

    @PostMapping("/{userId}/profile")
    public ApiResponse<ProfileResponse> createProfile(@PathVariable String userId,
                                                       @Valid @RequestBody ProfileUpdateRequest request) {
        ProfileResponse response = userService.createProfile(userId, request);
        return ApiResponse.success(response);
    }

    @PutMapping("/{userId}/profile")
    public ApiResponse<ProfileResponse> updateProfile(@PathVariable String userId,
                                                       @Valid @RequestBody ProfileUpdateRequest request) {
        ProfileResponse response = userService.updateProfile(userId, request);
        return ApiResponse.success(response);
    }

    /**
     * 修复 B-001/B-005: 数据隔离校验。
     * <p>对于 @Cacheable 方法（getProfile/getUserInfo），缓存命中时 Service 方法体不执行，
     * 内部 validateDataIsolation 会被绕过。因此数据隔离校验必须上移到 Controller 层。
     * <p>对于 @CacheEvict 方法（updateUser/createProfile/updateProfile），缓存不命中，
     * Service 内部 validateDataIsolation 仍生效，无需在 Controller 重复校验。
     */
    private void validateUserIdMatch(String userId) {
        String currentUserId = extractCurrentUserId();
        if (currentUserId == null || currentUserId.isBlank()) {
            throw new AuthenticationException("未认证，请先登录");
        }
        if (!currentUserId.equals(userId)) {
            throw new BusinessException(403, "无权限访问他人数据", "FORBIDDEN_ACCESS");
        }
    }

    private String extractCurrentUserId() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication != null && authentication.getPrincipal() instanceof String principal) {
            return principal;
        }
        return null;
    }
}
