package com.literatureassistant.dto.response;

import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

/**
 * 单 Agent 状态响应 DTO。
 * <p>对齐 Python 端 {@code AgentStateResponse} Pydantic Schema（5 字段）。
 * <p>字段命名遵循全局 Jackson SNAKE_CASE 配置。
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
    private String intermediateResult;

    /**
     * 执行耗时（毫秒），可空
     */
    private Long durationMs;
}
