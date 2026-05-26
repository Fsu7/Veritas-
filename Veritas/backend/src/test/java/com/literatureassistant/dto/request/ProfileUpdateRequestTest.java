package com.literatureassistant.dto.request;

import com.literatureassistant.enums.EducationLevel;
import com.literatureassistant.enums.KnowledgeLevel;
import com.literatureassistant.enums.PreferredStyle;
import jakarta.validation.ConstraintViolation;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import jakarta.validation.ValidatorFactory;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

class ProfileUpdateRequestTest {

    private static Validator validator;

    @BeforeAll
    static void setUp() {
        ValidatorFactory factory = Validation.buildDefaultValidatorFactory();
        validator = factory.getValidator();
    }

    @Test
    @DisplayName("正常请求应无校验错误")
    void validRequest_noViolations() {
        ProfileUpdateRequest request = ProfileUpdateRequest.builder()
                .educationLevel(EducationLevel.MASTER)
                .researchField("NLP")
                .knowledgeLevel(KnowledgeLevel.INTERMEDIATE)
                .preferredStyle(PreferredStyle.BALANCED)
                .build();

        Set<ConstraintViolation<ProfileUpdateRequest>> violations = validator.validate(request);
        assertTrue(violations.isEmpty());
    }

    @Test
    @DisplayName("educationLevel为null应校验失败")
    void nullEducationLevel_hasViolation() {
        ProfileUpdateRequest request = ProfileUpdateRequest.builder()
                .educationLevel(null)
                .researchField("NLP")
                .knowledgeLevel(KnowledgeLevel.INTERMEDIATE)
                .preferredStyle(PreferredStyle.BALANCED)
                .build();

        Set<ConstraintViolation<ProfileUpdateRequest>> violations = validator.validate(request);
        assertFalse(violations.isEmpty());
        assertTrue(violations.stream().anyMatch(v -> v.getMessage().contains("学历层次")));
    }

    @Test
    @DisplayName("researchField为空字符串应校验失败")
    void blankResearchField_hasViolation() {
        ProfileUpdateRequest request = ProfileUpdateRequest.builder()
                .educationLevel(EducationLevel.MASTER)
                .researchField("")
                .knowledgeLevel(KnowledgeLevel.INTERMEDIATE)
                .preferredStyle(PreferredStyle.BALANCED)
                .build();

        Set<ConstraintViolation<ProfileUpdateRequest>> violations = validator.validate(request);
        assertFalse(violations.isEmpty());
        assertTrue(violations.stream().anyMatch(v -> v.getMessage().contains("研究方向")));
    }

    @Test
    @DisplayName("knowledgeLevel为null应校验失败")
    void nullKnowledgeLevel_hasViolation() {
        ProfileUpdateRequest request = ProfileUpdateRequest.builder()
                .educationLevel(EducationLevel.MASTER)
                .researchField("NLP")
                .knowledgeLevel(null)
                .preferredStyle(PreferredStyle.BALANCED)
                .build();

        Set<ConstraintViolation<ProfileUpdateRequest>> violations = validator.validate(request);
        assertFalse(violations.isEmpty());
        assertTrue(violations.stream().anyMatch(v -> v.getMessage().contains("知识水平")));
    }

    @Test
    @DisplayName("preferredStyle为null应校验失败")
    void nullPreferredStyle_hasViolation() {
        ProfileUpdateRequest request = ProfileUpdateRequest.builder()
                .educationLevel(EducationLevel.MASTER)
                .researchField("NLP")
                .knowledgeLevel(KnowledgeLevel.INTERMEDIATE)
                .preferredStyle(null)
                .build();

        Set<ConstraintViolation<ProfileUpdateRequest>> violations = validator.validate(request);
        assertFalse(violations.isEmpty());
        assertTrue(violations.stream().anyMatch(v -> v.getMessage().contains("偏好风格")));
    }
}
