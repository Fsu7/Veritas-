package com.literatureassistant.dto.response;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.Map;

/**
 * Java SSE 事件 DTO。
 * <p>对接 Python 端 /api/agent/analyze/stream 推送的事件结构。
 * <p>7 种事件类型：{@code agent_started} / {@code agent_state_update} / {@code agent_completed}
 *  / {@code agent_failed} / {@code analysis_completed} / {@code error} / {@code ping}。
 *
 * @author XH-202630 Literature Assistant
 * @since 0.4
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class AgentSseEvent implements Serializable {

    private static final long serialVersionUID = 1L;

    /** SSE event id（单调递增） */
    @JsonProperty("id")
    private Long id;

    /** 事件类型 */
    @JsonProperty("event")
    private String event;

    /** 事件数据（camelCase JSON） */
    @JsonProperty("data")
    private Map<String, Object> data;
}
