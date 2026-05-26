package com.literatureassistant.dto.request;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.literatureassistant.enums.EducationLevel;
import com.literatureassistant.enums.KnowledgeLevel;
import com.literatureassistant.enums.PreferredStyle;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ProfileUpdateRequest {

    @NotNull(message = "学历层次不能为空")
    @JsonProperty("education_level")
    private EducationLevel educationLevel;

    @NotBlank(message = "研究方向不能为空")
    @JsonProperty("research_field")
    private String researchField;

    @NotNull(message = "知识水平不能为空")
    @JsonProperty("knowledge_level")
    private KnowledgeLevel knowledgeLevel;

    @NotNull(message = "偏好风格不能为空")
    @JsonProperty("preferred_style")
    private PreferredStyle preferredStyle;
}
