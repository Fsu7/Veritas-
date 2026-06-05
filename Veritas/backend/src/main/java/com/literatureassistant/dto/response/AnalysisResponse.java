package com.literatureassistant.dto.response;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.literatureassistant.enums.AnalysisStatus;
import com.literatureassistant.enums.AnalysisType;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class AnalysisResponse implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("analysis_id")
    private String analysisId;

    @JsonProperty("session_id")
    private String sessionId;

    private AnalysisStatus status;

    private AnalysisType type;

    private AnalysisResultDTO result;

    @JsonProperty("created_at")
    private LocalDateTime createdAt;
}
