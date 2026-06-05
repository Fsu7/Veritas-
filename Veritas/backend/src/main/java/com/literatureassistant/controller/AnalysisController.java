package com.literatureassistant.controller;

import com.literatureassistant.dto.common.AgentRequest;
import com.literatureassistant.dto.common.ApiResponse;
import com.literatureassistant.dto.request.PaperAnalysisRequest;
import com.literatureassistant.dto.response.AgentSseEvent;
import com.literatureassistant.dto.response.AnalysisResponse;
import com.literatureassistant.dto.response.AnalysisStatusResponse;
import com.literatureassistant.dto.response.AnalysisTaskResponse;
import com.literatureassistant.exception.AuthenticationException;
import com.literatureassistant.service.AgentClientService;
import com.literatureassistant.service.AnalysisService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Flux;

/**
 * 分析服务 Controller。
 * <p>暴露 POST /api/analysis/paper 端点 + GET /api/analysis/{id} 状态/结果端点
 *  + GET /api/analysis/{id}/agent-stream SSE 端点（JM4 前置实现）。
 *
 * @author XH-202630 Literature Assistant
 * @since 0.3
 */
@Slf4j
@RestController
@RequestMapping("/api/analysis")
@RequiredArgsConstructor
public class AnalysisController {

    private final AnalysisService analysisService;
    private final AgentClientService agentClientService;

    /**
     * 论文分析入口（POST /api/analysis/paper）。
     * <p>JWT 鉴权 → 参数校验 → AnalysisService.analyzePaper。
     */
    @PostMapping("/paper")
    public ResponseEntity<ApiResponse<AnalysisTaskResponse>> analyzePaper(
            @Valid @RequestBody PaperAnalysisRequest request,
            @AuthenticationPrincipal String userId) {
        String currentUserId = userId != null ? userId : extractCurrentUserId();
        if (currentUserId == null || currentUserId.isBlank()) {
            throw new AuthenticationException("未认证，请先登录");
        }
        log.info("REST analyzePaper: userId={}, paperId={}, topic={}",
                currentUserId, request.getPaperId(),
                request.getTopic() != null && request.getTopic().length() > 50
                        ? request.getTopic().substring(0, 50) + "..."
                        : request.getTopic());
        AnalysisTaskResponse response = analysisService.analyzePaper(currentUserId, request);
        return ResponseEntity.status(HttpStatus.ACCEPTED).body(ApiResponse.success(response));
    }

    private String extractCurrentUserId() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication != null && authentication.getPrincipal() instanceof String principal) {
            return principal;
        }
        return null;
    }

    /**
     * 查询分析结果（GET /api/analysis/{analysisId}）。
     */
    @GetMapping("/{analysisId}")
    public ResponseEntity<ApiResponse<AnalysisResponse>> getAnalysisResult(
            @PathVariable String analysisId,
            @AuthenticationPrincipal String userId) {
        String currentUserId = userId != null ? userId : extractCurrentUserId();
        if (currentUserId == null || currentUserId.isBlank()) {
            throw new AuthenticationException("未认证，请先登录");
        }
        log.info("REST getAnalysisResult: userId={}, analysisId={}", currentUserId, analysisId);
        AnalysisResponse response = analysisService.getAnalysisResult(currentUserId, analysisId);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    /**
     * 查询分析状态（GET /api/analysis/{analysisId}/status）。
     */
    @GetMapping("/{analysisId}/status")
    public ResponseEntity<ApiResponse<AnalysisStatusResponse>> getAnalysisStatus(
            @PathVariable String analysisId,
            @AuthenticationPrincipal String userId) {
        String currentUserId = userId != null ? userId : extractCurrentUserId();
        if (currentUserId == null || currentUserId.isBlank()) {
            throw new AuthenticationException("未认证，请先登录");
        }
        log.info("REST getAnalysisStatus: userId={}, analysisId={}", currentUserId, analysisId);
        AnalysisStatusResponse response = analysisService.getAnalysisStatus(currentUserId, analysisId);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

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

        return agentClientService.generateReportStream(agentRequest, lastEventId)
                .map(event -> toServerSentEvent(event));
    }

    /**
     * 将内部 AgentSseEvent 转换为 Spring 框架 ServerSentEvent 推送给前端。
     */
    private ServerSentEvent<Object> toServerSentEvent(AgentSseEvent event) {
        ServerSentEvent.Builder<Object> builder = ServerSentEvent.builder();
        if (event.getId() != null) {
            builder.id(String.valueOf(event.getId()));
        }
        if (event.getEvent() != null) {
            builder.event(event.getEvent());
        }
        // data 字段透传给前端（camelCase JSON）
        builder.data(event.getData() != null ? event.getData() : new java.util.HashMap<>());
        return builder.build();
    }
}
