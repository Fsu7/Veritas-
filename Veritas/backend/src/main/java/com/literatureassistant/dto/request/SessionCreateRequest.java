package com.literatureassistant.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SessionCreateRequest {

    @NotBlank(message = "研究主题不能为空")
    @Size(max = 500, message = "研究主题长度不能超过500")
    private String topic;

    // P2附录: 客户端幂等令牌，5分钟内相同 token 返回已有会话
    @Size(max = 100, message = "幂等令牌长度不能超过100")
    private String clientToken;
}
