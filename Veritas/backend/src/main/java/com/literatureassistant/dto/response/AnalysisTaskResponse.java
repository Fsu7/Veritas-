package com.literatureassistant.dto.response;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.literatureassistant.enums.AnalysisStatus;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 分析任务创建响应 DTO。
 * <p>POST /api/analysis/paper 同步返回（不等待 AI 完成），前端后续轮询 GET /api/analysis/{id} 或订阅 SSE。
 *
 * @author XH-202630 Literature Assistant
 * @since 0.3
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class AnalysisTaskResponse {

    @JsonProperty("analysis_id")
    private String analysisId;

    private AnalysisStatus status;

    private String message;

    @JsonProperty("created_at")
    private LocalDateTime createdAt;
}
