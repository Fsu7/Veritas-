package com.literatureassistant.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.literatureassistant.dto.request.LoginRequest;
import com.literatureassistant.dto.request.ProfileUpdateRequest;
import com.literatureassistant.dto.request.RegisterRequest;
import com.literatureassistant.dto.request.UserUpdateRequest;
import com.literatureassistant.dto.response.LoginResponse;
import com.literatureassistant.dto.response.ProfileResponse;
import com.literatureassistant.dto.response.UserResponse;
import com.literatureassistant.entity.User;
import com.literatureassistant.entity.UserProfile;
import com.literatureassistant.exception.AuthenticationException;
import com.literatureassistant.exception.BusinessException;
import com.literatureassistant.exception.ResourceNotFoundException;
import com.literatureassistant.mapper.UserMapper;
import com.literatureassistant.repository.UserProfileRepository;
import com.literatureassistant.repository.UserRepository;
import com.literatureassistant.util.JwtUtil;
import com.literatureassistant.util.RedisKeyUtil;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Duration;
import java.util.UUID;

@Service
@Slf4j
@RequiredArgsConstructor
public class UserService {

    private final UserRepository userRepository;
    private final UserProfileRepository userProfileRepository;
    private final JwtUtil jwtUtil;
    private final PasswordEncoder passwordEncoder;
    private final RedisTemplate<String, String> redisTemplate;
    private final ObjectMapper objectMapper;
    private final UserMapper userMapper;

    @Transactional
    public UserResponse register(RegisterRequest request) {
        if (userRepository.existsByUsername(request.getUsername())) {
            throw new BusinessException(409, "用户名已存在", "USERNAME_DUPLICATE");
        }
        if (userRepository.existsByEmail(request.getEmail())) {
            throw new BusinessException(409, "邮箱已被注册", "EMAIL_DUPLICATE");
        }

        String encodedPassword = passwordEncoder.encode(request.getPassword());
        String userId = "usr_" + UUID.randomUUID().toString().replace("-", "").substring(0, 8);

        User user = User.builder()
                .userId(userId)
                .username(request.getUsername())
                .email(request.getEmail())
                .passwordHash(encodedPassword)
                .build();

        userRepository.save(user);

        log.info("User registered: userId={}, username={}", userId, user.getUsername());

        return userMapper.toUserResponse(user, false);
    }

    @Transactional(readOnly = true)
    public LoginResponse login(LoginRequest request) {
        User user = userRepository.findByUsername(request.getUsername())
                .orElseThrow(() -> new AuthenticationException("用户名或密码错误"));

        if (!passwordEncoder.matches(request.getPassword(), user.getPasswordHash())) {
            throw new AuthenticationException("用户名或密码错误");
        }

        String token = jwtUtil.generateToken(user.getUserId(), user.getUsername());
        boolean hasProfile = userProfileRepository.existsByUserId(user.getUserId());

        log.info("User logged in: userId={}, username={}", user.getUserId(), user.getUsername());

        return LoginResponse.builder()
                .token(token)
                .userId(user.getUserId())
                .username(user.getUsername())
                .hasProfile(hasProfile)
                .build();
    }

    @Cacheable(value = "userInfo", key = "#userId")
    public UserResponse getUserInfo(String userId) {
        User user = userRepository.findByUserId(userId)
                .orElseThrow(() -> new ResourceNotFoundException("User", userId));

        boolean hasProfile = userProfileRepository.existsByUserId(userId);

        return userMapper.toUserResponse(user, hasProfile);
    }

    @Transactional
    @CacheEvict(value = "userInfo", key = "#userId")
    public UserResponse updateUser(String userId, UserUpdateRequest request) {
        validateDataIsolation(userId);

        User user = userRepository.findByUserId(userId)
                .orElseThrow(() -> new ResourceNotFoundException("User", userId));

        if (request.getUsername() != null && !request.getUsername().equals(user.getUsername())) {
            if (userRepository.existsByUsername(request.getUsername())) {
                throw new BusinessException(409, "用户名已存在", "USERNAME_DUPLICATE");
            }
            user.setUsername(request.getUsername());
        }
        if (request.getEmail() != null && !request.getEmail().equals(user.getEmail())) {
            if (userRepository.existsByEmail(request.getEmail())) {
                throw new BusinessException(409, "邮箱已被注册", "EMAIL_DUPLICATE");
            }
            user.setEmail(request.getEmail());
        }

        userRepository.save(user);

        boolean hasProfile = userProfileRepository.existsByUserId(userId);

        log.info("User updated: userId={}", userId);

        return userMapper.toUserResponse(user, hasProfile);
    }

    public void logoutWithAuth(String authHeader) {
        String rawToken = jwtUtil.extractBearerToken(authHeader);
        if (rawToken == null) {
            throw new BusinessException(401, "无效的Authorization头", "INVALID_AUTH_HEADER");
        }
        String tokenUserId = jwtUtil.getUserIdFromToken(rawToken);
        if (tokenUserId == null) {
            throw new BusinessException(401, "无效或已过期的Token", "INVALID_TOKEN");
        }
        validateDataIsolation(tokenUserId);
        logout(rawToken);
    }

    public void logout(String token) {
        String jti = jwtUtil.getTokenJti(token);
        if (jti == null) {
            return;
        }

        jwtUtil.blacklistToken(token);

        log.info("User logged out: jti={}", jti);
    }

    @Cacheable(value = "userProfile", key = "#userId", unless = "#result == null")
    public ProfileResponse getProfile(String userId) {
        validateDataIsolation(userId);

        UserProfile profile = userProfileRepository.findByUserId(userId)
                .orElseThrow(() -> new ResourceNotFoundException("UserProfile", userId));

        return userMapper.toProfileResponse(profile);
    }

    @Transactional
    @CacheEvict(value = {"userProfile", "userProfileJson", "userInfo"}, key = "#userId")
    public ProfileResponse createProfile(String userId, ProfileUpdateRequest request) {
        validateDataIsolation(userId);

        userRepository.findByUserId(userId)
                .orElseThrow(() -> new ResourceNotFoundException("User", userId));

        if (userProfileRepository.existsByUserId(userId)) {
            throw new BusinessException(409, "用户画像已存在", "PROFILE_ALREADY_EXISTS");
        }

        UserProfile entity = UserProfile.builder()
                .userId(userId)
                .educationLevel(request.getEducationLevel())
                .researchField(request.getResearchField())
                .knowledgeLevel(request.getKnowledgeLevel())
                .preferredStyle(request.getPreferredStyle())
                .build();

        userProfileRepository.save(entity);

        ProfileResponse response = userMapper.toProfileResponse(entity);
        syncProfileToRedis(userId, response);

        log.info("Profile created: userId={}", userId);

        return response;
    }

    @Transactional
    @CacheEvict(value = {"userProfile", "userProfileJson", "userInfo"}, key = "#userId")
    public ProfileResponse updateProfile(String userId, ProfileUpdateRequest request) {
        validateDataIsolation(userId);

        UserProfile entity = userProfileRepository.findByUserId(userId)
                .orElseThrow(() -> new ResourceNotFoundException("UserProfile", userId));

        entity.setEducationLevel(request.getEducationLevel());
        entity.setResearchField(request.getResearchField());
        entity.setKnowledgeLevel(request.getKnowledgeLevel());
        entity.setPreferredStyle(request.getPreferredStyle());

        userProfileRepository.save(entity);

        ProfileResponse response = userMapper.toProfileResponse(entity);
        syncProfileToRedis(userId, response);

        log.info("Profile updated: userId={}", userId);

        return response;
    }

    private void validateDataIsolation(String userId) {
        String currentUserId = getCurrentUserId();
        if (currentUserId == null) {
            throw new AuthenticationException("未认证，请先登录");
        }
        if (!currentUserId.equals(userId)) {
            throw new BusinessException(403, "无权限访问他人数据", "FORBIDDEN_ACCESS");
        }
    }

    private String getCurrentUserId() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication != null && authentication.getPrincipal() instanceof String principal) {
            return principal;
        }
        return null;
    }

    private void syncProfileToRedis(String userId, ProfileResponse profile) {
        try {
            String json = objectMapper.writeValueAsString(profile);
            String key = RedisKeyUtil.userProfileKey(userId);
            redisTemplate.opsForValue().set(key, json, Duration.ofHours(1));
        } catch (Exception e) {
            log.warn("Failed to sync profile to Redis: userId={}, error={}", userId, e.getMessage());
        }
    }
}
