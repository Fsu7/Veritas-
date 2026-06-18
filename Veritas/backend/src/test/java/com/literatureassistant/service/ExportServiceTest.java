package com.literatureassistant.service;

import com.literatureassistant.dto.response.AnalysisResponse;
import com.literatureassistant.dto.response.AnalysisResultDTO;
import com.literatureassistant.enums.AnalysisStatus;
import com.literatureassistant.exception.BusinessException;
import com.literatureassistant.exception.ResourceNotFoundException;
import com.literatureassistant.util.PdfExporter;
import com.literatureassistant.util.WordExporter;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;

/**
 * task37/task38: ExportService 单元测试。
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("ExportService 测试")
class ExportServiceTest {

    @Mock
    private AnalysisService analysisService;

    @Mock
    private PdfExporter pdfExporter;

    @Mock
    private WordExporter wordExporter;

    @InjectMocks
    private ExportService exportService;

    @Test
    @DisplayName("testExportPdfNotCompleted - status != COMPLETED 抛 BusinessException(ANALYSIS_NOT_COMPLETED)")
    void testExportPdfNotCompleted() {
        AnalysisResultDTO result = AnalysisResultDTO.builder()
                .analysisId("anl_1")
                .status(AnalysisStatus.PROCESSING)
                .report("内容")
                .build();
        AnalysisResponse resp = AnalysisResponse.builder()
                .analysisId("anl_1").result(result).build();
        when(analysisService.getAnalysisResult("u1", "anl_1")).thenReturn(resp);

        assertThatThrownBy(() -> exportService.exportPdf("u1", "anl_1"))
                .isInstanceOf(BusinessException.class)
                .hasMessageContaining("分析未完成");
    }

    @Test
    @DisplayName("testExportPdfEmptyReport - 空 report 抛 BusinessException(EMPTY_REPORT)")
    void testExportPdfEmptyReport() {
        AnalysisResultDTO result = AnalysisResultDTO.builder()
                .analysisId("anl_1")
                .status(AnalysisStatus.COMPLETED)
                .report("")
                .build();
        AnalysisResponse resp = AnalysisResponse.builder()
                .analysisId("anl_1").result(result).build();
        when(analysisService.getAnalysisResult("u1", "anl_1")).thenReturn(resp);

        assertThatThrownBy(() -> exportService.exportPdf("u1", "anl_1"))
                .isInstanceOf(BusinessException.class)
                .hasMessageContaining("分析报告为空");
    }

    @Test
    @DisplayName("testExportPdfDataIsolation - 用户A无法导出用户B的分析结果")
    void testExportPdfDataIsolation() {
        when(analysisService.getAnalysisResult(eq("uA"), anyString()))
                .thenThrow(new ResourceNotFoundException("AnalysisResult", "anl_B"));

        assertThatThrownBy(() -> exportService.exportPdf("uA", "anl_B"))
                .isInstanceOf(ResourceNotFoundException.class);
    }

    @Test
    @DisplayName("testExportWordNotCompleted - status != COMPLETED 抛 BusinessException")
    void testExportWordNotCompleted() {
        AnalysisResultDTO result = AnalysisResultDTO.builder()
                .analysisId("anl_1")
                .status(AnalysisStatus.PROCESSING)
                .report("内容")
                .build();
        AnalysisResponse resp = AnalysisResponse.builder()
                .analysisId("anl_1").result(result).build();
        when(analysisService.getAnalysisResult("u1", "anl_1")).thenReturn(resp);

        assertThatThrownBy(() -> exportService.exportWord("u1", "anl_1"))
                .isInstanceOf(BusinessException.class)
                .hasMessageContaining("分析未完成");
    }

    @Test
    @DisplayName("testExportWordEmptyReport - 空 report 抛 BusinessException")
    void testExportWordEmptyReport() {
        AnalysisResultDTO result = AnalysisResultDTO.builder()
                .analysisId("anl_1")
                .status(AnalysisStatus.COMPLETED)
                .report("   ")
                .build();
        AnalysisResponse resp = AnalysisResponse.builder()
                .analysisId("anl_1").result(result).build();
        when(analysisService.getAnalysisResult("u1", "anl_1")).thenReturn(resp);

        assertThatThrownBy(() -> exportService.exportWord("u1", "anl_1"))
                .isInstanceOf(BusinessException.class)
                .hasMessageContaining("分析报告为空");
    }

    @Test
    @DisplayName("testExportWordDataIsolation - 用户A无法导出用户B的分析结果")
    void testExportWordDataIsolation() {
        when(analysisService.getAnalysisResult(eq("uA"), anyString()))
                .thenThrow(new ResourceNotFoundException("AnalysisResult", "anl_B"));

        assertThatThrownBy(() -> exportService.exportWord("uA", "anl_B"))
                .isInstanceOf(ResourceNotFoundException.class);
    }

    @Test
    @DisplayName("testExportUnifiedPdf - 统一入口 format=pdf 路由到 PdfExporter")
    void testExportUnifiedPdf() throws java.io.IOException {
        AnalysisResultDTO result = AnalysisResultDTO.builder()
                .analysisId("anl_1")
                .status(AnalysisStatus.COMPLETED)
                .report("# 内容")
                .build();
        AnalysisResponse resp = AnalysisResponse.builder()
                .analysisId("anl_1").result(result).build();
        when(analysisService.getAnalysisResult("u1", "anl_1")).thenReturn(resp);
        byte[] expected = new byte[]{1, 2, 3};
        when(pdfExporter.export("anl_1", result)).thenReturn(expected);

        byte[] actual = exportService.export("u1", "anl_1", "pdf");

        org.assertj.core.api.Assertions.assertThat(actual).isEqualTo(expected);
    }

    @Test
    @DisplayName("testExportUnifiedWord - 统一入口 format=word 路由到 WordExporter")
    void testExportUnifiedWord() throws java.io.IOException {
        AnalysisResultDTO result = AnalysisResultDTO.builder()
                .analysisId("anl_1")
                .status(AnalysisStatus.COMPLETED)
                .report("# 内容")
                .build();
        AnalysisResponse resp = AnalysisResponse.builder()
                .analysisId("anl_1").result(result).build();
        when(analysisService.getAnalysisResult("u1", "anl_1")).thenReturn(resp);
        byte[] expected = new byte[]{4, 5, 6};
        when(wordExporter.export("anl_1", result)).thenReturn(expected);

        byte[] actual = exportService.export("u1", "anl_1", "word");

        org.assertj.core.api.Assertions.assertThat(actual).isEqualTo(expected);
    }

    @Test
    @DisplayName("testExportUnifiedDocx - 统一入口 format=docx 路由到 WordExporter")
    void testExportUnifiedDocx() throws java.io.IOException {
        AnalysisResultDTO result = AnalysisResultDTO.builder()
                .analysisId("anl_1")
                .status(AnalysisStatus.COMPLETED)
                .report("# 内容")
                .build();
        AnalysisResponse resp = AnalysisResponse.builder()
                .analysisId("anl_1").result(result).build();
        when(analysisService.getAnalysisResult("u1", "anl_1")).thenReturn(resp);
        byte[] expected = new byte[]{7, 8, 9};
        when(wordExporter.export("anl_1", result)).thenReturn(expected);

        byte[] actual = exportService.export("u1", "anl_1", "docx");

        org.assertj.core.api.Assertions.assertThat(actual).isEqualTo(expected);
    }

    @Test
    @DisplayName("testExportUnifiedCaseInsensitive - format 大小写不敏感（PDF/pdf/Pdf 均路由 PDF）")
    void testExportUnifiedCaseInsensitive() throws java.io.IOException {
        AnalysisResultDTO result = AnalysisResultDTO.builder()
                .analysisId("anl_1")
                .status(AnalysisStatus.COMPLETED)
                .report("# 内容")
                .build();
        AnalysisResponse resp = AnalysisResponse.builder()
                .analysisId("anl_1").result(result).build();
        when(analysisService.getAnalysisResult("u1", "anl_1")).thenReturn(resp);
        byte[] expected = new byte[]{1};
        when(pdfExporter.export("anl_1", result)).thenReturn(expected);

        byte[] actual = exportService.export("u1", "anl_1", "PDF");

        org.assertj.core.api.Assertions.assertThat(actual).isEqualTo(expected);
    }

    @Test
    @DisplayName("testExportUnsupportedFormat - 不支持的格式抛 BusinessException(UNSUPPORTED_FORMAT)")
    void testExportUnsupportedFormat() {
        assertThatThrownBy(() -> exportService.export("u1", "anl_1", "excel"))
                .isInstanceOf(BusinessException.class)
                .hasMessageContaining("不支持的导出格式");
    }

    @Test
    @DisplayName("testExportNullFormat - format=null 抛 BusinessException(INVALID_FORMAT)")
    void testExportNullFormat() {
        assertThatThrownBy(() -> exportService.export("u1", "anl_1", null))
                .isInstanceOf(BusinessException.class)
                .hasMessageContaining("导出格式不能为空");
    }
}
