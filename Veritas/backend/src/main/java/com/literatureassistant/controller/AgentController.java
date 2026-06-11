package com.literatureassistant.controller;

import com.literatureassistant.dto.common.AgentRequest;
import com.literatureassistant.dto.response.AgentSseEvent;
import com.literatureassistant.exception.AuthenticationException;
import com.literatureassistant.service.AgentClientService;
import com.literatureassistant.service.AnalysisService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.MediaType;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Flux;

import java.time.Instant;
import java.util.HashMap;
import java.util.Map;

/**
 * Agent SSE 控制器（task28 + task29）。
 * <p>JM4 主路径：SSE 流式转发 + 事件格式标准化 + Agent 状态查询。
 * <p>数据隔离：仅 analysisId 所有者可订阅 SSE 流；其他用户 403。
 *
 * @author XH-202630 Literature Assistant
 * @since 0.4
 */
@Slf4j
@RestController
@RequestMapping("/api/analysis")
@RequiredArgsConstructor
public class AgentController {

    private final AnalysisService analysisService;
    private final AgentClientService agentClientService;

    /**
     * SSE 实时推送 Agent 执行状态（GET /api/analysis/{analysisId}/agent-stream）。
     * <p>JM4 主路径：Java→Python SSE 转发层，客户端可通过 EventSource 订阅。
     * <p>支持 Last-Event-ID Header 断线重连。
     * <p>数据隔离：仅 analysisId 所有者可订阅；其他用户 403。
     *
     * @param analysisId  分析任务 ID
     * @param lastEventId SSE Last-Event-ID Header（断线重连时由客户端透传，可空）
     * @param userId      JWT 注入的 userId
     * @return SSE 事件流
     */
    @GetMapping(value = "/{analysisId}/agent-stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<ServerSentEvent<Object>> agentStream(
            @PathVariable String analysisId,
            @RequestHeader(value = "Last-Event-ID", required = false) String lastEventId,
            @AuthenticationPrincipal String userId) {
        String currentUserId = userId != null ? userId : extractCurrentUserId();
        if (currentUserId == null || currentUserId.isBlank()) {
            throw new AuthenticationException("未认证，请先登录");
        }
        log.info("REST agentStream SSE: userId={}, analysisId={}, lastEventId={}",
                currentUserId, analysisId, lastEventId);

        // 数据隔离校验：防止用户 A 订阅用户 B 的 analysisId
        analysisService.validateAnalysisAccess(currentUserId, analysisId);

        // 构造 AgentRequest，触发 Python 端 SSE 流
        AgentRequest agentRequest = AgentRequest.builder()
                .analysisId(analysisId)
                .userId(currentUserId)
                .build();

        return agentClientService.generateReportStreamWithHeartbeat(agentRequest, lastEventId)
                .map(this::toStandardizedSseEvent);
    }

    /**
     * 将内部 AgentSseEvent 转换为标准化 SSE 事件（task29）。
     * <p>7 种事件类型的 data 字段统一为结构化 JSON，timestamp 为 ISO8601 格式。
     * <ul>
     *   <li>agent_started → {agentName, analysisId, timestamp}</li>
     *   <li>agent_state_update → {agentName, status, progress, intermediateResult, durationMs}</li>
     *   <li>agent_completed → {agentName, analysisId, result, timestamp}</li>
     *   <li>agent_failed → {agentName, error, timestamp}</li>
     *   <li>analysis_completed → {analysisId, status, report, citations}</li>
     *   <li>error → {type, message}</li>
     *   <li>ping → {timestamp}</li>
     * </ul>
     */
    private ServerSentEvent<Object> toStandardizedSseEvent(AgentSseEvent event) {
        ServerSentEvent.Builder<Object> builder = ServerSentEvent.builder();
        if (event.getId() != null) {
            builder.id(String.valueOf(event.getId()));
        }
        String eventType = event.getEvent();
        if (eventType != null) {
            builder.event(eventType);
        }
        // 标准化 data：为每种事件类型补全 timestamp 字段
        Map<String, Object> data = event.getData() != null
                ? new HashMap<>(event.getData())
                : new HashMap<>();

        // 为各事件类型补全标准字段
        if (eventType != null) {
            switch (eventType) {
                case "agent_started":
                case "agent_completed":
                case "agent_failed":
                    if (!data.containsKey("timestamp")) {
                        data.put("timestamp", Instant.now().toString());
                    }
                    break;
                case "analysis_completed":
                    data.putIfAbsent("status", "completed");
                    break;
                case "error":
                    data.putIfAbsent("type", "internal");
                    break;
                case "ping":
                    data.putIfAbsent("timestamp", Instant.now().toString());
                    break;
                default:
                    break;
            }
        }
        builder.data(data);
        return builder.build();
    }

    private String extractCurrentUserId() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication != null && authentication.getPrincipal() instanceof String principal) {
            return principal;
        }
        return null;
    }
}
