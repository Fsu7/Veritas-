package com.literatureassistant.dto.request;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class UserUpdateRequest {

    @Size(min = 3, max = 50, message = "用户名长度3-50")
    private String username;

    @Email(message = "邮箱格式不正确")
    private String email;
}
