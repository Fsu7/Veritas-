package com.literatureassistant.service;

import com.literatureassistant.dto.response.AnalysisResponse;
import com.literatureassistant.dto.response.AnalysisResultDTO;
import com.literatureassistant.enums.AnalysisStatus;
import com.literatureassistant.exception.BusinessException;
import com.literatureassistant.util.PdfExporter;
import com.literatureassistant.util.WordExporter;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.io.IOException;

/**
 * 导出编排服务。
 * <p>负责分析结果导出的编排：校验 → 查询分析结果 → 调用对应导出工具 → 返回 byte[]。
 * <p>task37 新建（PDF 导出）；task38 扩展 Word 导出 + 统一 export 入口。
 *
 * @author XH-202630 Literature Assistant
 * @since 0.5
 */
@Service
@Slf4j
@RequiredArgsConstructor
public class ExportService {

    private final AnalysisService analysisService;
    private final PdfExporter pdfExporter;
    private final WordExporter wordExporter;

    /**
     * 统一导出入口（task38）。
     * <p>根据 format 路由到 PDF/Word 导出工具。
     *
     * @param userId     当前用户 ID（来自 JWT）
     * @param analysisId 分析任务 ID
     * @param format     导出格式：pdf / word（大小写不敏感）
     * @return 导出文件字节数组
     */
    public byte[] export(String userId, String analysisId, String format) {
        if (format == null) {
            throw new BusinessException(400, "导出格式不能为空", "INVALID_FORMAT");
        }
        String normalized = format.trim().toLowerCase();
        return switch (normalized) {
            case "pdf" -> exportPdf(userId, analysisId);
            case "word", "docx" -> exportWord(userId, analysisId);
            default -> throw new BusinessException(400, "不支持的导出格式: " + format, "UNSUPPORTED_FORMAT");
        };
    }

    /**
     * PDF 导出编排。
     * <p>1) 调 analysisService.getAnalysisResult（含数据隔离校验）；
     * 2) 校验 status == COMPLETED；3) 校验 report 非空；4) 调 PdfExporter。
     *
     * @param userId     当前用户 ID（来自 JWT）
     * @param analysisId 分析任务 ID
     * @return PDF 字节数组
     */
    public byte[] exportPdf(String userId, String analysisId) {
        AnalysisResultDTO result = getValidatedResult(userId, analysisId);
        try {
            return pdfExporter.export(analysisId, result);
        } catch (IOException e) {
            log.error("PDF export failed: analysisId={}", analysisId, e);
            throw new BusinessException(500, "PDF导出失败", "EXPORT_FAILED");
        }
    }

    /**
     * Word 导出编排（task38）。
     * <p>1) 调 analysisService.getAnalysisResult（含数据隔离校验）；
     * 2) 校验 status == COMPLETED；3) 校验 report 非空；4) 调 WordExporter。
     *
     * @param userId     当前用户 ID（来自 JWT）
     * @param analysisId 分析任务 ID
     * @return Word 字节数组
     */
    public byte[] exportWord(String userId, String analysisId) {
        AnalysisResultDTO result = getValidatedResult(userId, analysisId);
        try {
            return wordExporter.export(analysisId, result);
        } catch (IOException e) {
            log.error("Word export failed: analysisId={}", analysisId, e);
            throw new BusinessException(500, "Word导出失败", "EXPORT_FAILED");
        }
    }

    /**
     * 内部方法：获取并校验分析结果。
     * <p>数据隔离由 analysisService.getAnalysisResult 内部保证；
     * 状态校验：status == COMPLETED；report 非空校验。
     */
    private AnalysisResultDTO getValidatedResult(String userId, String analysisId) {
        AnalysisResponse resp = analysisService.getAnalysisResult(userId, analysisId);
        AnalysisResultDTO result = resp.getResult();
        if (result == null || result.getStatus() != AnalysisStatus.COMPLETED) {
            throw new BusinessException(400, "分析未完成，无法导出", "ANALYSIS_NOT_COMPLETED");
        }
        if (result.getReport() == null || result.getReport().isBlank()) {
            throw new BusinessException(400, "分析报告为空", "EMPTY_REPORT");
        }
        return result;
    }
}
