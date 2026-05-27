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
public class UserResponse {

    private String userId;
    private String username;
    private String email;
    private LocalDateTime createdAt;
    private boolean hasProfile;
}
