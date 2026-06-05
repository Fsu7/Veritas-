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
import java.util.Map;

/**
 * Python → Java AnalyzeResponse 响应体。
 * <p>对齐 Python 端 {@code AnalyzeResponse} Pydantic Schema（7 字段）。
 * <p>Python 端 model_dump(by_alias=True) 输出 camelCase, 用 {@link JsonProperty} 覆盖全局 SNAKE_CASE。
 *
 * @author XH-202630 Literature Assistant
 * @since 0.3
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class AnalysisResultDTO implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * 分析任务 ID
     */
    @JsonProperty("analysisId")
    private String analysisId;

    /**
     * 任务状态枚举：processing / completed / failed / degraded
     */
    private AnalysisStatus status;

    /**
     * 综述报告 markdown，可空
     */
    private String report;

    /**
     * 引用列表，元素为 {@code {index, paper_id, citation}}，可空
     */
    private List<Map<String, Object>> citations;

    /**
     * 各 Agent 执行状态，可空
     */
    @JsonProperty("agentStates")
    private List<AgentStateResponse> agentStates;

    /**
     * 是否降级，可空
     */
    private Boolean degraded;

    /**
     * 降级原因，可空
     */
    @JsonProperty("degradedReason")
    private String degradedReason;

    /**
     * 降级响应静态工厂。
     * <p>当 AI 服务不可用且无缓存可用时，返回一个表示降级的 DTO。
     *
     * @param analysisId 分析任务 ID
     * @param reason     降级原因
     * @return 降级 DTO
     */
    public static AnalysisResultDTO degraded(String analysisId, String reason) {
        return AnalysisResultDTO.builder()
                .analysisId(analysisId)
                .status(AnalysisStatus.FAILED)
                .degraded(true)
                .degradedReason(reason)
                .build();
    }
}
