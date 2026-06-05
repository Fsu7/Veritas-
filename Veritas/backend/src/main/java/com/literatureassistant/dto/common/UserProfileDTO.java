package com.literatureassistant.dto.common;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
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
 * <p>Python 端 model_dump(by_alias=True) 输出 camelCase, 用 {@link JsonProperty} 覆盖全局 SNAKE_CASE。
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
    @JsonProperty("educationLevel")
    private EducationLevel educationLevel;

    /**
     * 研究方向（如 NLP / CV / RL / 多模态），可空
     */
    @JsonProperty("researchField")
    private String researchField;

    /**
     * 知识水平：beginner / intermediate / advanced / expert
     */
    @JsonProperty("knowledgeLevel")
    private KnowledgeLevel knowledgeLevel;

    /**
     * 偏好风格：simple / balanced / technical
     */
    @JsonProperty("preferredStyle")
    private PreferredStyle preferredStyle;
}
