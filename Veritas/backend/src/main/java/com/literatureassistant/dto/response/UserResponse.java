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
public class UserResponse {

    @JsonProperty("user_id")
    private String userId;
    private String username;
    private String email;
    private LocalDateTime createdAt;

    @JsonProperty("has_profile")
    private boolean hasProfile;
}
