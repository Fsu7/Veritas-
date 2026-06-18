package com.literatureassistant.service;

import com.literatureassistant.dto.request.ProfileUpdateRequest;
import com.literatureassistant.dto.response.ProfileResponse;
import com.literatureassistant.entity.User;
import com.literatureassistant.entity.UserProfile;
import com.literatureassistant.enums.EducationLevel;
import com.literatureassistant.enums.KnowledgeLevel;
import com.literatureassistant.enums.PreferredStyle;
import com.literatureassistant.exception.BusinessException;
import com.literatureassistant.exception.ResourceNotFoundException;
import com.literatureassistant.mapper.UserMapper;
import com.literatureassistant.repository.UserProfileRepository;
import com.literatureassistant.repository.UserRepository;
import com.literatureassistant.util.JwtUtil;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.ValueOperations;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class UserServiceProfileTest {

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
    private RedisTemplate<String, String> redisTemplate;

    @Mock
    private ValueOperations<String, String> valueOperations;

    private UserProfile testProfile;
    private ProfileUpdateRequest updateRequest;
    private ProfileResponse expectedResponse;

    @BeforeEach
    void setUp() {
        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken("usr_test1234", null, java.util.List.of()));

        testProfile = UserProfile.builder()
                .userId("usr_test1234")
                .educationLevel(EducationLevel.MASTER)
                .researchField("NLP")
                .knowledgeLevel(KnowledgeLevel.INTERMEDIATE)
                .preferredStyle(PreferredStyle.BALANCED)
                .build();

        updateRequest = ProfileUpdateRequest.builder()
                .educationLevel(EducationLevel.MASTER)
                .researchField("NLP")
                .knowledgeLevel(KnowledgeLevel.INTERMEDIATE)
                .preferredStyle(PreferredStyle.BALANCED)
                .build();

        expectedResponse = ProfileResponse.builder()
                .userId("usr_test1234")
                .educationLevel("master")
                .researchField("NLP")
                .knowledgeLevel("intermediate")
                .preferredStyle("balanced")
                .build();
    }

    @AfterEach
    void tearDown() {
        SecurityContextHolder.clearContext();
    }

    @Test
    @DisplayName("getProfile - 正常获取画像返回ProfileResponse")
    void getProfile_normal_returnsProfileResponse() {
        when(userProfileRepository.findByUserId("usr_test1234")).thenReturn(Optional.of(testProfile));
        when(userMapper.toProfileResponse(any(UserProfile.class))).thenReturn(expectedResponse);

        ProfileResponse response = userService.getProfile("usr_test1234");

        assertThat(response).isNotNull();
        assertThat(response.getUserId()).isEqualTo("usr_test1234");
        assertThat(response.getEducationLevel()).isEqualTo("master");
        assertThat(response.getResearchField()).isEqualTo("NLP");
    }

    @Test
    @DisplayName("getProfile - 画像不存在抛出ResourceNotFoundException")
    void getProfile_notFound_throwsResourceNotFoundException() {
        when(userProfileRepository.findByUserId("usr_test1234")).thenReturn(Optional.empty());

        assertThatThrownBy(() -> userService.getProfile("usr_test1234"))
                .isInstanceOf(ResourceNotFoundException.class);
    }

    // 修复 B-001: 数据隔离校验已上移到 UserController.validateUserIdMatch，
    // Service 层不再负责认证/越权校验。原 getProfile_notAuthenticated_throwsAuthenticationException
    // 和 getProfile_forbiddenAccess_throwsBusinessException 测试已删除，
    // 数据隔离测试由 UserControllerTest 和 Jm5IntegrationTest 覆盖。

    @Test
    @DisplayName("createProfile - 正常创建画像返回ProfileResponse")
    void createProfile_normal_returnsProfileResponse() {
        User testUser = User.builder().userId("usr_test1234").build();
        when(userRepository.findByUserId("usr_test1234")).thenReturn(Optional.of(testUser));
        when(userProfileRepository.existsByUserId("usr_test1234")).thenReturn(false);
        when(userProfileRepository.save(any(UserProfile.class))).thenReturn(testProfile);
        when(userMapper.toProfileResponse(any(UserProfile.class))).thenReturn(expectedResponse);
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);

        ProfileResponse response = userService.createProfile("usr_test1234", updateRequest);

        assertThat(response).isNotNull();
        assertThat(response.getUserId()).isEqualTo("usr_test1234");
        verify(userProfileRepository).save(any(UserProfile.class));
    }

    @Test
    @DisplayName("createProfile - 画像已存在抛出BusinessException")
    void createProfile_alreadyExists_throwsBusinessException() {
        User testUser = User.builder().userId("usr_test1234").build();
        when(userRepository.findByUserId("usr_test1234")).thenReturn(Optional.of(testUser));
        when(userProfileRepository.existsByUserId("usr_test1234")).thenReturn(true);

        assertThatThrownBy(() -> userService.createProfile("usr_test1234", updateRequest))
                .isInstanceOf(BusinessException.class)
                .hasMessageContaining("用户画像已存在");
    }

    @Test
    @DisplayName("updateProfile - 正常更新画像返回ProfileResponse")
    void updateProfile_normal_returnsProfileResponse() {
        when(userProfileRepository.findByUserId("usr_test1234")).thenReturn(Optional.of(testProfile));
        when(userProfileRepository.save(any(UserProfile.class))).thenReturn(testProfile);
        when(userMapper.toProfileResponse(any(UserProfile.class))).thenReturn(expectedResponse);
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);

        ProfileResponse response = userService.updateProfile("usr_test1234", updateRequest);

        assertThat(response).isNotNull();
        verify(userProfileRepository).save(any(UserProfile.class));
    }

    @Test
    @DisplayName("updateProfile - 画像不存在抛出ResourceNotFoundException")
    void updateProfile_notFound_throwsResourceNotFoundException() {
        when(userProfileRepository.findByUserId("usr_test1234")).thenReturn(Optional.empty());

        assertThatThrownBy(() -> userService.updateProfile("usr_test1234", updateRequest))
                .isInstanceOf(ResourceNotFoundException.class);
    }
}
