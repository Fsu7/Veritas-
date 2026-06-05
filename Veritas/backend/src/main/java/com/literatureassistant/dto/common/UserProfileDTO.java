package com.literatureassistant.dto.common;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.literatureassistant.enums.EducationLevel;
import com.literatureassistant.enums.KnowledgeLevel;
import com.literatureassistant.enums.PreferredStyle;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

/**
 * 嵌入 AgentRequest 的用户画像 DTO。
 * <p>对齐 Python 端 {@code UserProfile} Pydantic Schema（4 字段）。
 * <p>枚举字段直接用 Java 端枚举，由 Jackson 自动映射 {@code dbValue} 字符串。
 *
 * @author XH-202630 Literature Assistant
 * @since 0.3
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class UserProfileDTO implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * 学历层次：undergraduate / master / phd / faculty
     */
    private EducationLevel educationLevel;

    /**
     * 研究方向（如 NLP / CV / RL / 多模态），可空
     */
    private String researchField;

    /**
     * 知识水平：beginner / intermediate / advanced / expert
     */
    private KnowledgeLevel knowledgeLevel;

    /**
     * 偏好风格：simple / balanced / technical
     */
    private PreferredStyle preferredStyle;
}
