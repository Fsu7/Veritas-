package com.literatureassistant.controller;

import com.literatureassistant.dto.common.ApiResponse;
import com.literatureassistant.dto.common.PageResponse;
import com.literatureassistant.dto.request.SessionCreateRequest;
import com.literatureassistant.dto.request.SessionStatusUpdateRequest;
import com.literatureassistant.dto.response.SessionDetailResponse;
import com.literatureassistant.dto.response.SessionResponse;
import com.literatureassistant.service.SessionService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@Slf4j
@RestController
@RequestMapping("/api/sessions")
@RequiredArgsConstructor
public class SessionController {

    private final SessionService sessionService;

    @PostMapping
    public ResponseEntity<ApiResponse<SessionResponse>> createSession(
            @Valid @RequestBody SessionCreateRequest request) {
        String userId = extractCurrentUserId();
        log.info("REST createSession: userId={}, topic={}", userId, request.getTopic());
        SessionResponse response = sessionService.createSession(userId, request);
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.success(response));
    }

    @GetMapping
    public ApiResponse<PageResponse<SessionResponse>> listSessions(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size) {
        String userId = extractCurrentUserId();
        log.info("REST listSessions: userId={}, page={}, size={}", userId, page, size);
        PageResponse<SessionResponse> response = sessionService.listSessions(userId, page, size);
        return ApiResponse.success(response);
    }

    @GetMapping("/{sessionId}")
    public ApiResponse<SessionDetailResponse> getSessionDetail(@PathVariable String sessionId) {
        String userId = extractCurrentUserId();
        log.info("REST getSessionDetail: userId={}, sessionId={}", userId, sessionId);
        // 修复 B-004: @Cacheable 命中时 Service 方法体不执行，数据隔离校验必须上移到 Controller。
        // validateSessionAccess 会查 DB 校验 sessionId 归属，缓存命中时仍执行（安全代价）。
        sessionService.validateSessionAccess(userId, sessionId);
        SessionDetailResponse response = sessionService.getSessionDetail(sessionId);
        return ApiResponse.success(response);
    }

    @PutMapping("/{sessionId}/status")
    public ApiResponse<Void> updateStatus(
            @PathVariable String sessionId,
            @Valid @RequestBody SessionStatusUpdateRequest request) {
        log.info("REST updateStatus: sessionId={}, targetStatus={}", sessionId, request.getStatus());
        sessionService.updateStatus(sessionId, request.getStatus());
        return ApiResponse.success(null);
    }

    @DeleteMapping("/{sessionId}")
    public ApiResponse<Void> deleteSession(@PathVariable String sessionId) {
        log.info("REST deleteSession: sessionId={}", sessionId);
        sessionService.deleteSession(sessionId);
        return ApiResponse.success(null);
    }

    private String extractCurrentUserId() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication != null && authentication.getPrincipal() instanceof String principal) {
            return principal;
        }
        return null;
    }
}
