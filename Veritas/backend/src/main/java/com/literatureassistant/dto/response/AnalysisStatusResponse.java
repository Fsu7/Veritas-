package com.literatureassistant.dto.response;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.literatureassistant.enums.AnalysisStatus;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.List;

/**
 * 分析状态查询响应 DTO。
 * <p>GET /api/analysis/{analysisId}/status 返回体，聚合 AnalysisResult.status + 实时 Agent 状态。
 *
 * @author XH-202630 Literature Assistant
 * @since 0.3
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class AnalysisStatusResponse implements Serializable {

    private static final long serialVersionUID = 1L;

    @JsonProperty("analysis_id")
    private String analysisId;

    /**
     * AnalysisResult.status（DB 持久化状态）。
     */
    private AnalysisStatus status;

    /**
     * 整体进度 0.0-1.0，由 agentStates 中各 Agent 的 progress 字段算术平均计算。
     * 无 agentStates 时为 null。
     */
    private Double progress;

    /**
     * 当前正在执行的 Agent 名称。
     * status=processing 时取首个非 completed 的 agent；全部 completed 时为 null。
     */
    @JsonProperty("current_agent")
    private String currentAgent;

    /**
     * 所有 Agent 的实时状态列表（从 Redis Hash 读取，不缓存）。
     */
    @JsonProperty("agent_states")
    private List<AgentStateResponse> agentStates;
}
