package com.literatureassistant.dto.response;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ProfileResponse {

    @JsonProperty("user_id")
    private String userId;

    @JsonProperty("education_level")
    private String educationLevel;

    @JsonProperty("research_field")
    private String researchField;

    @JsonProperty("knowledge_level")
    private String knowledgeLevel;

    @JsonProperty("preferred_style")
    private String preferredStyle;

    @JsonProperty("updated_at")
    private LocalDateTime updatedAt;
}
