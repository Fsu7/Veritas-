package com.literatureassistant.mapper;

import com.literatureassistant.dto.response.ProfileResponse;
import com.literatureassistant.dto.response.UserResponse;
import com.literatureassistant.entity.User;
import com.literatureassistant.entity.UserProfile;
import com.literatureassistant.enums.EducationLevel;
import com.literatureassistant.enums.KnowledgeLevel;
import com.literatureassistant.enums.PreferredStyle;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDateTime;

import static org.assertj.core.api.Assertions.assertThat;

@ExtendWith(MockitoExtension.class)
class UserMapperTest {

    private final UserMapper userMapper = new UserMapperImpl();

    @Test
    @DisplayName("toUserResponse - 正确映射User到UserResponse")
    void toUserResponse_normal_mapsCorrectly() {
        User user = User.builder()
                .userId("usr_test1234")
                .username("testuser")
                .email("test@example.com")
                .createdAt(LocalDateTime.of(2026, 5, 26, 10, 0, 0))
                .build();

        UserResponse response = userMapper.toUserResponse(user, true);

        assertThat(response).isNotNull();
        assertThat(response.getUserId()).isEqualTo("usr_test1234");
        assertThat(response.getUsername()).isEqualTo("testuser");
        assertThat(response.getEmail()).isEqualTo("test@example.com");
        assertThat(response.isHasProfile()).isTrue();
        assertThat(response.getCreatedAt()).isEqualTo(LocalDateTime.of(2026, 5, 26, 10, 0, 0));
    }

    @Test
    @DisplayName("toUserResponse - hasProfile为false时正确映射")
    void toUserResponse_hasProfileFalse_mapsCorrectly() {
        User user = User.builder()
                .userId("usr_test1234")
                .username("testuser")
                .email("test@example.com")
                .build();

        UserResponse response = userMapper.toUserResponse(user, false);

        assertThat(response.isHasProfile()).isFalse();
    }

    @Test
    @DisplayName("toProfileResponse - 正确映射UserProfile到ProfileResponse，枚举返回dbValue")
    void toProfileResponse_normal_mapsCorrectly() {
        UserProfile profile = UserProfile.builder()
                .userId("usr_test1234")
                .educationLevel(EducationLevel.MASTER)
                .researchField("NLP")
                .knowledgeLevel(KnowledgeLevel.INTERMEDIATE)
                .preferredStyle(PreferredStyle.BALANCED)
                .updatedAt(LocalDateTime.of(2026, 5, 26, 10, 0, 0))
                .build();

        ProfileResponse response = userMapper.toProfileResponse(profile);

        assertThat(response).isNotNull();
        assertThat(response.getUserId()).isEqualTo("usr_test1234");
        assertThat(response.getEducationLevel()).isEqualTo("master");
        assertThat(response.getResearchField()).isEqualTo("NLP");
        assertThat(response.getKnowledgeLevel()).isEqualTo("intermediate");
        assertThat(response.getPreferredStyle()).isEqualTo("balanced");
        assertThat(response.getUpdatedAt()).isEqualTo(LocalDateTime.of(2026, 5, 26, 10, 0, 0));
    }
}
