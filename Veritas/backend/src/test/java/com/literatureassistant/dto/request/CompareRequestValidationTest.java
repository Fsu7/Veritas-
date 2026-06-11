package com.literatureassistant.dto.request;

import jakarta.validation.ConstraintViolation;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import jakarta.validation.ValidatorFactory;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * CompareRequest Bean Validation 单元测试（task25）。
 * <p>使用 jakarta.validation.Validator 触发约束验证，验证 paperIds size / topic 校验。
 *
 * @author XH-202630 Literature Assistant
 * @since 0.4
 */
class CompareRequestValidationTest {

    private static ValidatorFactory factory;
    private static Validator validator;

    @BeforeAll
    static void initValidator() {
        factory = Validation.buildDefaultValidatorFactory();
        validator = factory.getValidator();
    }

    @AfterAll
    static void closeValidator() {
        if (factory != null) {
            factory.close();
        }
    }

    @Test
    @DisplayName("paperIds 只有 1 个 → 校验失败")
    void paperIds_tooFew_fails() {
        CompareRequest req = CompareRequest.builder()
                .topic("对比")
                .paperIds(List.of("p1"))
                .build();
        Set<ConstraintViolation<CompareRequest>> violations = validator.validate(req);
        assertThat(violations).isNotEmpty();
        assertThat(violations).anyMatch(v -> v.getMessage().contains("论文数量必须在2-5之间"));
    }

    @Test
    @DisplayName("paperIds 有 6 个 → 校验失败")
    void paperIds_tooMany_fails() {
        CompareRequest req = CompareRequest.builder()
                .topic("对比")
                .paperIds(List.of("p1", "p2", "p3", "p4", "p5", "p6"))
                .build();
        Set<ConstraintViolation<CompareRequest>> violations = validator.validate(req);
        assertThat(violations).isNotEmpty();
        assertThat(violations).anyMatch(v -> v.getMessage().contains("论文数量必须在2-5之间"));
    }

    @Test
    @DisplayName("paperIds=null → 校验失败")
    void paperIds_null_fails() {
        CompareRequest req = CompareRequest.builder()
                .topic("对比")
                .paperIds(null)
                .build();
        Set<ConstraintViolation<CompareRequest>> violations = validator.validate(req);
        assertThat(violations).isNotEmpty();
    }

    @Test
    @DisplayName("topic 为空 → 校验失败")
    void topic_blank_fails() {
        CompareRequest req = CompareRequest.builder()
                .topic("")
                .paperIds(List.of("p1", "p2"))
                .build();
        Set<ConstraintViolation<CompareRequest>> violations = validator.validate(req);
        assertThat(violations).isNotEmpty();
        assertThat(violations).anyMatch(v -> v.getMessage().contains("研究主题不能为空"));
    }

    @Test
    @DisplayName("topic 超 500 字符 → 校验失败")
    void topic_tooLong_fails() {
        String longTopic = "a".repeat(501);
        CompareRequest req = CompareRequest.builder()
                .topic(longTopic)
                .paperIds(List.of("p1", "p2"))
                .build();
        Set<ConstraintViolation<CompareRequest>> violations = validator.validate(req);
        assertThat(violations).isNotEmpty();
        assertThat(violations).anyMatch(v -> v.getMessage().contains("研究主题长度不能超过500"));
    }

    @Test
    @DisplayName("合法请求（2 篇论文 + topic）→ 校验通过")
    void validRequest_passes() {
        CompareRequest req = CompareRequest.builder()
                .topic("对比多Agent")
                .paperIds(List.of("p1", "p2"))
                .build();
        Set<ConstraintViolation<CompareRequest>> violations = validator.validate(req);
        assertThat(violations).isEmpty();
    }

    @Test
    @DisplayName("合法请求（5 篇论文 + sessionId）→ 校验通过")
    void validRequest_maxPaperIds_passes() {
        CompareRequest req = CompareRequest.builder()
                .topic("对比多Agent")
                .paperIds(List.of("p1", "p2", "p3", "p4", "p5"))
                .sessionId("ses_001")
                .build();
        Set<ConstraintViolation<CompareRequest>> violations = validator.validate(req);
        assertThat(violations).isEmpty();
    }

    @Test
    @DisplayName("多个校验错误聚合")
    void multipleViolations_aggregated() {
        CompareRequest req = CompareRequest.builder()
                .topic("")
                .paperIds(List.of("p1"))
                .build();
        Set<ConstraintViolation<CompareRequest>> violations = validator.validate(req);
        String messages = violations.stream()
                .map(ConstraintViolation::getMessage)
                .collect(Collectors.joining("|"));
        assertThat(messages).contains("研究主题不能为空");
        assertThat(messages).contains("论文数量必须在2-5之间");
    }
}
