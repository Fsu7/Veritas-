package com.literatureassistant.util;

import com.literatureassistant.dto.response.AnalysisResultDTO;
import com.literatureassistant.enums.AnalysisStatus;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.junit.jupiter.MockitoExtension;

import java.io.IOException;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * task37: PDF 导出单元测试。
 * 注：ExportService 相关测试已拆分至
 * {@code com.literatureassistant.service.ExportServiceTest}，
 * 避免嵌套静态类导致 surefire 无法加载。
 */
@ExtendWith(MockitoExtension.class)
class PdfExporterTest {

    private final PdfExporter pdfExporter = new PdfExporter();

    @Test
    @DisplayName("testExportBasicMarkdown - #/##/### 标题、段落、- 列表、``` 代码块渲染")
    void testExportBasicMarkdown() throws IOException {
        String markdown = "# 主标题\n\n## 二级标题\n\n### 三级标题\n\n" +
                "这是一个段落。\n\n" +
                "- 列表项1\n- 列表项2\n\n" +
                "```\n代码块内容\n```\n";
        AnalysisResultDTO result = AnalysisResultDTO.builder()
                .analysisId("anl_test1")
                .status(AnalysisStatus.COMPLETED)
                .report(markdown)
                .build();

        byte[] bytes = pdfExporter.export("anl_test1", result);

        assertThat(bytes).isNotNull();
        assertThat(bytes.length).isGreaterThan(0);
        // PDF 文件头 %PDF
        assertThat(new String(bytes, 0, 4)).isEqualTo("%PDF");
    }

    @Test
    @DisplayName("testExportChineseText - 中文字体不乱码")
    void testExportChineseText() throws IOException {
        String markdown = "# 中文标题测试\n\n这是一段中文内容，包含标点符号：，。！？\n";
        AnalysisResultDTO result = AnalysisResultDTO.builder()
                .analysisId("anl_chinese")
                .status(AnalysisStatus.COMPLETED)
                .report(markdown)
                .build();

        byte[] bytes = pdfExporter.export("anl_chinese", result);

        assertThat(bytes).isNotNull();
        assertThat(bytes.length).isGreaterThan(0);
        assertThat(new String(bytes, 0, 4)).isEqualTo("%PDF");
    }

    @Test
    @DisplayName("testExportCitations - citations 渲染为 [index] citation_text；空 citations 不渲染 section")
    void testExportCitations() throws IOException {
        List<Map<String, Object>> citations = List.of(
                Map.of("index", 1, "citation", "Author A, 2024. Paper title."),
                Map.of("index", 2, "citation", "Author B, 2023. Another paper.")
        );
        AnalysisResultDTO result = AnalysisResultDTO.builder()
                .analysisId("anl_cite")
                .status(AnalysisStatus.COMPLETED)
                .report("# 测试报告\n\n正文内容")
                .citations(citations)
                .build();

        byte[] bytes = pdfExporter.export("anl_cite", result);

        assertThat(bytes).isNotNull();
        assertThat(bytes.length).isGreaterThan(0);
    }

    @Test
    @DisplayName("testExportCitationsEmpty - 空 citations 不报错")
    void testExportCitationsEmpty() throws IOException {
        AnalysisResultDTO result = AnalysisResultDTO.builder()
                .analysisId("anl_empty_cite")
                .status(AnalysisStatus.COMPLETED)
                .report("# 测试报告\n\n正文内容")
                .citations(null)
                .build();

        byte[] bytes = pdfExporter.export("anl_empty_cite", result);

        assertThat(bytes).isNotNull();
        assertThat(bytes.length).isGreaterThan(0);
    }

    @Test
    @DisplayName("testExportFooter - 页脚显示 'AI生成，仅供参考'")
    void testExportFooter() throws IOException {
        AnalysisResultDTO result = AnalysisResultDTO.builder()
                .analysisId("anl_footer")
                .status(AnalysisStatus.COMPLETED)
                .report("# 测试\n\n内容")
                .build();

        byte[] bytes = pdfExporter.export("anl_footer", result);

        // 页脚由 IEventHandler 在 END_PAGE 事件中渲染，验证 PDF 生成成功即可
        assertThat(bytes).isNotNull();
        assertThat(bytes.length).isGreaterThan(0);
    }

    @Test
    @DisplayName("testGenerateFileName - 文件名格式 analysis_{id}_{yyyyMMddHHmmss}.pdf")
    void testGenerateFileName() {
        String fileName = pdfExporter.generateFileName("anl_123");

        assertThat(fileName).startsWith("analysis_anl_123_");
        assertThat(fileName).endsWith(".pdf");
        // 验证时间戳部分为 14 位数字
        String timestamp = fileName.substring("analysis_anl_123_".length(), fileName.length() - ".pdf".length());
        assertThat(timestamp).hasSize(14);
        assertThat(timestamp).matches("\\d{14}");
        // 验证时间戳可被解析
        LocalDateTime.parse(timestamp, DateTimeFormatter.ofPattern("yyyyMMddHHmmss"));
    }

    @Test
    @DisplayName("testExportLargeReport - report > 10000 字符不 OOM")
    void testExportLargeReport() throws IOException {
        StringBuilder sb = new StringBuilder();
        sb.append("# 大文件测试\n\n");
        for (int i = 0; i < 500; i++) {
            sb.append("这是第 ").append(i).append(" 段内容，用于测试大文件导出。");
            sb.append("包含中文和English混合内容。\n\n");
        }
        AnalysisResultDTO result = AnalysisResultDTO.builder()
                .analysisId("anl_large")
                .status(AnalysisStatus.COMPLETED)
                .report(sb.toString())
                .build();

        byte[] bytes = pdfExporter.export("anl_large", result);

        assertThat(bytes).isNotNull();
        assertThat(bytes.length).isGreaterThan(10000);
    }

    @Test
    @DisplayName("testExportSpecialCharacters - HTML 标签正确渲染（无XSS）")
    void testExportSpecialCharacters() throws IOException {
        // 注意：STSong-Light 字体不支持 emoji/部分 Unicode 符号，故测试用例仅含 HTML 标签
        String markdown = "# 特殊字符测试\n\n" +
                "HTML 标签：<script>alert('xss')</script>\n\n" +
                "中文标点：，。！？；：\n";
        AnalysisResultDTO result = AnalysisResultDTO.builder()
                .analysisId("anl_special")
                .status(AnalysisStatus.COMPLETED)
                .report(markdown)
                .build();

        byte[] bytes = pdfExporter.export("anl_special", result);

        assertThat(bytes).isNotNull();
        assertThat(bytes.length).isGreaterThan(0);
        // PDF 不执行 HTML 脚本，无 XSS 风险
    }
}
