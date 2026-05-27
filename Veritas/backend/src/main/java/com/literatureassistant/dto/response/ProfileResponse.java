package com.literatureassistant.dto.response;

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

    private String userId;
    private String educationLevel;
    private String researchField;
    private String knowledgeLevel;
    private String preferredStyle;
    private LocalDateTime updatedAt;
}
