package com.literatureassistant.dto.response;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

/**
 * 单 Agent 状态响应 DTO。
 * <p>对齐 Python 端 {@code AgentStateResponse} Pydantic Schema（5 字段）。
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
public class AgentStateResponse implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * Agent 名称（coordinator / retriever / analyzer / comparer / generator / reviewer）
     */
    @JsonProperty("agentName")
    private String agentName;

    /**
     * Agent 状态字符串（waiting / running / completed / failed）
     */
    private String status;

    /**
     * 执行进度 0.0-1.0，可空
     */
    private Double progress;

    /**
     * 中间结果摘要，可空
     */
    @JsonProperty("intermediateResult")
    private String intermediateResult;

    /**
     * 执行耗时（毫秒），可空
     */
    @JsonProperty("durationMs")
    private Long durationMs;
}
