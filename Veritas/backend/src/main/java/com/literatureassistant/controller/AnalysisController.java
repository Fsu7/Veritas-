package com.literatureassistant.controller;

import com.literatureassistant.dto.common.ApiResponse;
import com.literatureassistant.dto.request.PaperAnalysisRequest;
import com.literatureassistant.dto.response.AnalysisResponse;
import com.literatureassistant.dto.response.AnalysisStatusResponse;
import com.literatureassistant.dto.response.AnalysisTaskResponse;
import com.literatureassistant.exception.AuthenticationException;
import com.literatureassistant.service.AnalysisService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 分析服务 Controller。
 * <p>暴露 POST /api/analysis/paper 端点。
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
}
