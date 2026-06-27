package com.literatureassistant.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.literatureassistant.dto.response.AnalysisResultDTO;
import com.literatureassistant.dto.response.AnalysisTaskResponse;
import com.literatureassistant.entity.AnalysisResult;
import com.literatureassistant.enums.AnalysisStatus;
import com.literatureassistant.enums.AnalysisType;
import com.literatureassistant.exception.BusinessException;
import com.literatureassistant.exception.ResourceNotFoundException;
import com.literatureassistant.repository.AnalysisResultRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;

/**
 * 分析任务事务服务（task24 重构产物）。
 * <p>提取自 AnalysisService 的 {@code @Transactional} 方法：savePending / completeAnalysis。
 * 消除原 {@code @Autowired @Lazy self} 自注入反模式，通过 Spring 代理保证事务生效。
 * <p>事务边界：仅覆盖 DB 写入；AI 调用（agentClientService.analyzePaper）由 AnalysisService 编排层调用，
 * 显式无 @Transactional，避免 30s 长事务。
 *
 * @author XH-202630 Literature Assistant
 * @since 0.4
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class AnalysisTransactionService {

    private final AnalysisResultRepository analysisResultRepository;
    private final ObjectMapper objectMapper;

    /**
     * 保存 AnalysisResult(PENDING) 记录 — 短事务。
     */
    @Transactional
    public AnalysisResult savePending(String analysisId, String sessionId, AnalysisType type) {
        AnalysisResult entity = AnalysisResult.builder()
                .analysisId(analysisId)
                .sessionId(sessionId)
                .type(type)
                .status(AnalysisStatus.PENDING)
                .result("{}")
                .build();
        return analysisResultRepository.save(entity);
    }

    /**
     * 更新 AnalysisResult 状态 + 持久化 result JSON — 短事务。
     * <p>降级响应（{@code result.degraded == true}）映射为 COMPLETED（不是 FAILED，因为请求本身成功完成）。
     */
    @Transactional
    public AnalysisTaskResponse completeAnalysis(Long id, AnalysisResultDTO result) {
        AnalysisResult entity = analysisResultRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("AnalysisResult", String.valueOf(id)));
        AnalysisStatus newStatus = (result != null && Boolean.TRUE.equals(result.getDegraded()))
                ? AnalysisStatus.COMPLETED
                : mapStatus(result);
        entity.setStatus(newStatus);
        entity.setResult(serializeResult(result));
        try {
            AnalysisResult saved = analysisResultRepository.save(entity);

            String message = buildMessage(result);
            return AnalysisTaskResponse.builder()
                    .analysisId(saved.getAnalysisId())
                    .status(saved.getStatus())
                    .message(message)
                    .createdAt(saved.getCreatedAt() != null ? saved.getCreatedAt() : LocalDateTime.now())
                    .build();
        } catch (org.springframework.orm.ObjectOptimisticLockingFailureException e) {
            log.warn("Optimistic lock conflict on AnalysisResult id={}", id);
            throw new BusinessException(409, "分析结果正在被并发更新，请重试", "CONFLICT");
        }
    }

    private AnalysisStatus mapStatus(AnalysisResultDTO result) {
        if (result == null || result.getStatus() == null) {
            return AnalysisStatus.FAILED;
        }
        return switch (result.getStatus()) {
            case COMPLETED -> AnalysisStatus.COMPLETED;
            case PROCESSING -> AnalysisStatus.PROCESSING;
            case FAILED -> AnalysisStatus.FAILED;
            default -> result.getStatus();
        };
    }

    private String serializeResult(AnalysisResultDTO result) {
        try {
            return objectMapper.writeValueAsString(result);
        } catch (JsonProcessingException e) {
            log.warn("result 序列化失败: {}", e.getMessage());
            return "{}";
        }
    }

    private String buildMessage(AnalysisResultDTO result) {
        if (result == null) {
            return "分析失败：响应为空";
        }
        if (Boolean.TRUE.equals(result.getDegraded())) {
            return "分析完成（降级）：" + result.getDegradedReason();
        }
        return switch (result.getStatus()) {
            case COMPLETED -> "分析完成";
            case PROCESSING -> "分析进行中";
            case FAILED -> "分析失败：" + (result.getDegradedReason() != null ? result.getDegradedReason() : "未知错误");
            default -> "分析状态：" + result.getStatus();
        };
    }
}
