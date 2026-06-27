package com.literatureassistant.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.literatureassistant.dto.common.ApiResponse;
import com.literatureassistant.dto.request.CompareRequest;
import com.literatureassistant.dto.request.PaperAnalysisRequest;
import com.literatureassistant.dto.request.ReportRequest;
import com.literatureassistant.dto.response.AnalysisResponse;
import com.literatureassistant.dto.response.AnalysisStatusResponse;
import com.literatureassistant.dto.response.AnalysisTaskResponse;
import com.literatureassistant.exception.AuthenticationException;
import com.literatureassistant.exception.BusinessException;
import com.literatureassistant.service.AnalysisService;
import com.literatureassistant.service.ExportService;
import com.literatureassistant.util.IdempotencyUtil;
import com.literatureassistant.util.PdfExporter;
import com.literatureassistant.util.WordExporter;
import org.apache.commons.codec.digest.DigestUtils;
import org.springframework.web.bind.annotation.RequestHeader;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

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
    private final ExportService exportService;
    private final PdfExporter pdfExporter;
    private final WordExporter wordExporter;
    private final IdempotencyUtil idempotencyUtil;
    private final ObjectMapper objectMapper;

    /**
     * 论文分析入口（POST /api/analysis/paper）。
     * <p>JWT 鉴权 → 参数校验 → AnalysisService.analyzePaper。
     */
    @PostMapping("/paper")
    public ResponseEntity<ApiResponse<AnalysisTaskResponse>> analyzePaper(
            @Valid @RequestBody PaperAnalysisRequest request,
            @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey,
            @AuthenticationPrincipal String userId) {
        String currentUserId = userId != null ? userId : extractCurrentUserId();
        if (currentUserId == null || currentUserId.isBlank()) {
            throw new AuthenticationException("未认证，请先登录");
        }
        // P1-15 修复: 幂等性检查，防止重复提交
        String effectiveKey = idempotencyKey != null ? idempotencyKey
                : DigestUtils.md5Hex(currentUserId + ":" + request.getPaperId() + ":" + request.getTopic());
        if (!idempotencyUtil.tryAcquire(effectiveKey)) {
            String cached = idempotencyUtil.getStoredResult(effectiveKey);
            if (cached != null) {
                try {
                    AnalysisTaskResponse cachedResponse = objectMapper.readValue(cached, AnalysisTaskResponse.class);
                    return ResponseEntity.status(HttpStatus.ACCEPTED).body(ApiResponse.success(cachedResponse));
                } catch (Exception e) {
                    // 反序列化失败,放行请求
                }
            }
            throw new BusinessException(409, "相同的分析请求正在处理中，请稍后重试", "IDEMPOTENT_IN_PROGRESS");
        }
        log.info("REST analyzePaper: userId={}, paperId={}, topic={}",
                currentUserId, request.getPaperId(),
                request.getTopic() != null && request.getTopic().length() > 50
                        ? request.getTopic().substring(0, 50) + "..."
                        : request.getTopic());
        AnalysisTaskResponse response;
        try {
            response = analysisService.analyzePaper(currentUserId, request);
        } catch (Exception e) {
            idempotencyUtil.release(effectiveKey);
            throw e;
        }
        idempotencyUtil.storeResult(effectiveKey, response);
        return ResponseEntity.status(HttpStatus.ACCEPTED).body(ApiResponse.success(response));
    }

    /**
     * 对比分析入口（POST /api/analysis/compare，task25）。
     * <p>JWT 鉴权 → 参数校验（@Valid） → AnalysisService.comparePapers。
     * <p>数据隔离：sessionId 对应 Session.userId 必须等于 currentUserId。
     */
    @PostMapping("/compare")
    public ResponseEntity<ApiResponse<AnalysisTaskResponse>> comparePapers(
            @Valid @RequestBody CompareRequest request,
            @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey,
            @AuthenticationPrincipal String userId) {
        String currentUserId = userId != null ? userId : extractCurrentUserId();
        if (currentUserId == null || currentUserId.isBlank()) {
            throw new AuthenticationException("未认证，请先登录");
        }
        // P1-15 修复: 幂等性检查，使用排序后的 paperIds 保证顺序无关性
        List<String> sortedPaperIds = new ArrayList<>(request.getPaperIds());
        Collections.sort(sortedPaperIds);
        String effectiveKey = idempotencyKey != null ? idempotencyKey
                : DigestUtils.md5Hex(currentUserId + ":" + String.join(",", sortedPaperIds) + ":" + request.getTopic());
        if (!idempotencyUtil.tryAcquire(effectiveKey)) {
            String cached = idempotencyUtil.getStoredResult(effectiveKey);
            if (cached != null) {
                try {
                    AnalysisTaskResponse cachedResponse = objectMapper.readValue(cached, AnalysisTaskResponse.class);
                    return ResponseEntity.status(HttpStatus.ACCEPTED).body(ApiResponse.success(cachedResponse));
                } catch (Exception e) {
                    // 反序列化失败,放行请求
                }
            }
            throw new BusinessException(409, "相同的分析请求正在处理中，请稍后重试", "IDEMPOTENT_IN_PROGRESS");
        }
        log.info("REST comparePapers: userId={}, paperCount={}, topic={}",
                currentUserId, request.getPaperIds().size(),
                request.getTopic() != null && request.getTopic().length() > 50
                        ? request.getTopic().substring(0, 50) + "..."
                        : request.getTopic());
        AnalysisTaskResponse response;
        try {
            response = analysisService.comparePapers(currentUserId, request);
        } catch (Exception e) {
            idempotencyUtil.release(effectiveKey);
            throw e;
        }
        idempotencyUtil.storeResult(effectiveKey, response);
        return ResponseEntity.status(HttpStatus.ACCEPTED).body(ApiResponse.success(response));
    }

    /**
     * 综述生成入口（POST /api/analysis/report，task26）。
     * <p>JWT 鉴权 → 参数校验（@Valid） → AnalysisService.generateReport。
     * <p>数据隔离：sessionId 对应 Session.userId 必须等于 currentUserId。
     */
    @PostMapping("/report")
    public ResponseEntity<ApiResponse<AnalysisTaskResponse>> generateReport(
            @Valid @RequestBody ReportRequest request,
            @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey,
            @AuthenticationPrincipal String userId) {
        String currentUserId = userId != null ? userId : extractCurrentUserId();
        if (currentUserId == null || currentUserId.isBlank()) {
            throw new AuthenticationException("未认证，请先登录");
        }
        // P1-15 修复: 幂等性检查，使用排序后的 paperIds 保证顺序无关性
        List<String> sortedPaperIds = new ArrayList<>(request.getPaperIds());
        Collections.sort(sortedPaperIds);
        String effectiveKey = idempotencyKey != null ? idempotencyKey
                : DigestUtils.md5Hex(currentUserId + ":" + String.join(",", sortedPaperIds) + ":" + request.getTopic());
        if (!idempotencyUtil.tryAcquire(effectiveKey)) {
            String cached = idempotencyUtil.getStoredResult(effectiveKey);
            if (cached != null) {
                try {
                    AnalysisTaskResponse cachedResponse = objectMapper.readValue(cached, AnalysisTaskResponse.class);
                    return ResponseEntity.status(HttpStatus.ACCEPTED).body(ApiResponse.success(cachedResponse));
                } catch (Exception e) {
                    // 反序列化失败,放行请求
                }
            }
            throw new BusinessException(409, "相同的分析请求正在处理中，请稍后重试", "IDEMPOTENT_IN_PROGRESS");
        }
        log.info("REST generateReport: userId={}, paperCount={}, topic={}",
                currentUserId, request.getPaperIds().size(),
                request.getTopic() != null && request.getTopic().length() > 50
                        ? request.getTopic().substring(0, 50) + "..."
                        : request.getTopic());
        AnalysisTaskResponse response;
        try {
            response = analysisService.generateReport(currentUserId, request);
        } catch (Exception e) {
            idempotencyUtil.release(effectiveKey);
            throw e;
        }
        idempotencyUtil.storeResult(effectiveKey, response);
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
        // 修复 B-003: @Cacheable 命中时 Service 方法体不执行，数据隔离校验必须上移到 Controller。
        // validateAnalysisAccess 会查 DB 校验 analysisId 归属，缓存命中时仍执行（安全代价）。
        analysisService.validateAnalysisAccess(currentUserId, analysisId);
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
     * task37/task38: 导出分析结果（GET /api/analysis/{analysisId}/export）。
     * <p>JWT 鉴权 → ExportService.export（统一入口）→ 返回 PDF/Word 文件。
     * <p>数据隔离：analysisId 对应 Session.userId 必须等于 currentUserId。
     * <p>支持格式：pdf（默认）、word/docx。
     */
    @GetMapping("/{analysisId}/export")
    public ResponseEntity<byte[]> exportAnalysis(
            @PathVariable String analysisId,
            @RequestParam(defaultValue = "pdf") String format,
            @AuthenticationPrincipal String userId) {
        String currentUserId = userId != null ? userId : extractCurrentUserId();
        if (currentUserId == null || currentUserId.isBlank()) {
            throw new AuthenticationException("未认证，请先登录");
        }
        log.info("REST exportAnalysis: userId={}, analysisId={}, format={}", currentUserId, analysisId, format);
        // 修复 B-003 延伸: 导出前校验资源归属，防止 @Cacheable 缓存命中绕过数据隔离。
        // ExportService.getValidatedResult 调用的 getAnalysisResult 是 @Cacheable 方法，
        // 缓存命中时方法体不执行，内部校验会被绕过，因此校验必须上移到 Controller 层。
        analysisService.validateAnalysisAccess(currentUserId, analysisId);
        byte[] bytes = exportService.export(currentUserId, analysisId, format);
        String normalized = format.trim().toLowerCase();
        String fileName;
        String contentType;
        if ("word".equals(normalized) || "docx".equals(normalized)) {
            fileName = wordExporter.generateFileName(analysisId);
            contentType = "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
        } else {
            fileName = pdfExporter.generateFileName(analysisId);
            contentType = MediaType.APPLICATION_PDF_VALUE;
        }
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + fileName + "\"")
                .header(HttpHeaders.CONTENT_TYPE, contentType)
                .body(bytes);
    }

}
