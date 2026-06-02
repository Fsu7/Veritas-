package com.literatureassistant.dto.request;

import com.literatureassistant.enums.SessionStatus;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SessionStatusUpdateRequest {

    @NotNull(message = "状态不能为空")
    private SessionStatus status;
}
