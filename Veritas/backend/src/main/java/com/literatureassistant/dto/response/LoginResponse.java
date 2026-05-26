package com.literatureassistant.dto.response;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class LoginResponse {

    private String token;

    @JsonProperty("user_id")
    private String userId;

    private String username;

    @JsonProperty("has_profile")
    private boolean hasProfile;
}
