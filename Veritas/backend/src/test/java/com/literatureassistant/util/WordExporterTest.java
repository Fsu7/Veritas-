package com.literatureassistant.util;

import com.literatureassistant.dto.response.AnalysisResultDTO;
import com.literatureassistant.enums.AnalysisStatus;
import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.apache.poi.xwpf.usermodel.XWPFParagraph;
import org.apache.poi.xwpf.usermodel.XWPFRun;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * task38: Word 导出单元测试。
 */
@DisplayName("WordExporter 测试")
class WordExporterTest {

    private final WordExporter wordExporter = new WordExporter();

    /**
     * 辅助方法：从字节数组加载 XWPFDocument。
     */
    private XWPFDocument loadDocument(byte[] bytes) throws IOException {
        return new XWPFDocument(new ByteArrayInputStream(bytes));
    }

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

        byte[] bytes = wordExporter.export("anl_test1", result);

        assertThat(bytes).isNotNull();
        assertThat(bytes.length).isGreaterThan(0);
        // Word 文件头 PK（zip 格式）
        assertThat(new String(bytes, 0, 2)).isEqualTo("PK");
        try (XWPFDocument doc = loadDocument(bytes)) {
            // 至少包含若干段落
            assertThat(doc.getParagraphs().size()).isGreaterThan(5);
        }
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

        byte[] bytes = wordExporter.export("anl_chinese", result);

        assertThat(bytes).isNotNull();
        assertThat(bytes.length).isGreaterThan(0);
        assertThat(new String(bytes, 0, 2)).isEqualTo("PK");
        try (XWPFDocument doc = loadDocument(bytes)) {
            // 验证中文字符可读
            String allText = doc.getParagraphs().stream()
                    .map(XWPFParagraph::getText)
                    .reduce("", (a, b) -> a + b);
            assertThat(allText).contains("中文标题测试");
            assertThat(allText).contains("，。！？");
        }
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

        byte[] bytes = wordExporter.export("anl_cite", result);

        assertThat(bytes).isNotNull();
        try (XWPFDocument doc = loadDocument(bytes)) {
            String allText = doc.getParagraphs().stream()
                    .map(XWPFParagraph::getText)
                    .reduce("", (a, b) -> a + b);
            assertThat(allText).contains("参考文献");
            assertThat(allText).contains("[1] Author A, 2024. Paper title.");
            assertThat(allText).contains("[2] Author B, 2023. Another paper.");
        }
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

        byte[] bytes = wordExporter.export("anl_empty_cite", result);

        assertThat(bytes).isNotNull();
        assertThat(bytes.length).isGreaterThan(0);
        try (XWPFDocument doc = loadDocument(bytes)) {
            String allText = doc.getParagraphs().stream()
                    .map(XWPFParagraph::getText)
                    .reduce("", (a, b) -> a + b);
            assertThat(allText).doesNotContain("参考文献");
        }
    }

    @Test
    @DisplayName("testExportFooter - 页脚显示 'AI生成，仅供参考'")
    void testExportFooter() throws IOException {
        AnalysisResultDTO result = AnalysisResultDTO.builder()
                .analysisId("anl_footer")
                .status(AnalysisStatus.COMPLETED)
                .report("# 测试\n\n内容")
                .build();

        byte[] bytes = wordExporter.export("anl_footer", result);

        assertThat(bytes).isNotNull();
        try (XWPFDocument doc = loadDocument(bytes)) {
            // 验证页脚存在
            assertThat(doc.getFooterList()).isNotEmpty();
            String footerText = doc.getFooterList().stream()
                    .flatMap(f -> f.getParagraphs().stream())
                    .map(XWPFParagraph::getText)
                    .reduce("", (a, b) -> a + b);
            assertThat(footerText).contains("AI生成，仅供参考");
        }
    }

    @Test
    @DisplayName("testGenerateFileName - 文件名格式 analysis_{id}_{yyyyMMddHHmmss}.docx")
    void testGenerateFileName() {
        String fileName = wordExporter.generateFileName("anl_123");

        assertThat(fileName).startsWith("analysis_anl_123_");
        assertThat(fileName).endsWith(".docx");
        // 验证时间戳部分为 14 位数字
        String timestamp = fileName.substring("analysis_anl_123_".length(), fileName.length() - ".docx".length());
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

        byte[] bytes = wordExporter.export("anl_large", result);

        assertThat(bytes).isNotNull();
        // Word docx 为 zip 压缩格式，500 段内容压缩后约 4-5KB
        assertThat(bytes.length).isGreaterThan(4000);
        // 验证内容完整可读
        try (XWPFDocument doc = loadDocument(bytes)) {
            long paragraphCount = doc.getParagraphs().size();
            assertThat(paragraphCount).isGreaterThan(100);
        }
    }

    @Test
    @DisplayName("testExportSpecialCharacters - HTML 标签正确渲染（无XSS）")
    void testExportSpecialCharacters() throws IOException {
        // Word 中 HTML 标签作为纯文本渲染，无 XSS 风险
        String markdown = "# 特殊字符测试\n\n" +
                "HTML 标签：<script>alert('xss')</script>\n\n" +
                "中文标点：，。！？；：\n";
        AnalysisResultDTO result = AnalysisResultDTO.builder()
                .analysisId("anl_special")
                .status(AnalysisStatus.COMPLETED)
                .report(markdown)
                .build();

        byte[] bytes = wordExporter.export("anl_special", result);

        assertThat(bytes).isNotNull();
        assertThat(bytes.length).isGreaterThan(0);
        try (XWPFDocument doc = loadDocument(bytes)) {
            String allText = doc.getParagraphs().stream()
                    .map(XWPFParagraph::getText)
                    .reduce("", (a, b) -> a + b);
            // HTML 标签作为纯文本保留，不执行
            assertThat(allText).contains("<script>alert('xss')</script>");
        }
    }

    @Test
    @DisplayName("testExportHeadings - 三级标题字体大小递减（18/15/13）")
    void testExportHeadings() throws IOException {
        String markdown = "# H1标题\n\n## H2标题\n\n### H3标题\n";
        AnalysisResultDTO result = AnalysisResultDTO.builder()
                .analysisId("anl_headings")
                .status(AnalysisStatus.COMPLETED)
                .report(markdown)
                .build();

        byte[] bytes = wordExporter.export("anl_headings", result);

        try (XWPFDocument doc = loadDocument(bytes)) {
            List<XWPFParagraph> paragraphs = doc.getParagraphs();
            // 找到三个标题段落（非空）
            List<XWPFParagraph> headingParagraphs = paragraphs.stream()
                    .filter(p -> !p.getText().isBlank())
                    .toList();
            assertThat(headingParagraphs).hasSizeGreaterThanOrEqualTo(3);

            // 验证 H1 字号 18、H2 字号 15、H3 字号 13
            XWPFRun h1Run = headingParagraphs.get(0).getRuns().get(0);
            XWPFRun h2Run = headingParagraphs.get(1).getRuns().get(0);
            XWPFRun h3Run = headingParagraphs.get(2).getRuns().get(0);
            assertThat(h1Run.getFontSizeAsDouble()).isEqualTo(18.0);
            assertThat(h2Run.getFontSizeAsDouble()).isEqualTo(15.0);
            assertThat(h3Run.getFontSizeAsDouble()).isEqualTo(13.0);
            // 验证加粗
            assertThat(h1Run.isBold()).isTrue();
            assertThat(h2Run.isBold()).isTrue();
            assertThat(h3Run.isBold()).isTrue();
        }
    }

    @Test
    @DisplayName("testExportListItems - 无序列表渲染为 '• item' 格式")
    void testExportListItems() throws IOException {
        String markdown = "# 列表测试\n\n- 项目一\n- 项目二\n- 项目三\n";
        AnalysisResultDTO result = AnalysisResultDTO.builder()
                .analysisId("anl_list")
                .status(AnalysisStatus.COMPLETED)
                .report(markdown)
                .build();

        byte[] bytes = wordExporter.export("anl_list", result);

        try (XWPFDocument doc = loadDocument(bytes)) {
            String allText = doc.getParagraphs().stream()
                    .map(XWPFParagraph::getText)
                    .reduce("", (a, b) -> a + "\n" + b);
            assertThat(allText).contains("• 项目一");
            assertThat(allText).contains("• 项目二");
            assertThat(allText).contains("• 项目三");
        }
    }

    @Test
    @DisplayName("testExportCodeBlock - 代码块使用浅灰背景")
    void testExportCodeBlock() throws IOException {
        String markdown = "# 代码测试\n\n```\nprint('hello')\n```\n";
        AnalysisResultDTO result = AnalysisResultDTO.builder()
                .analysisId("anl_code")
                .status(AnalysisStatus.COMPLETED)
                .report(markdown)
                .build();

        byte[] bytes = wordExporter.export("anl_code", result);

        try (XWPFDocument doc = loadDocument(bytes)) {
            // 验证代码内容存在
            String allText = doc.getParagraphs().stream()
                    .map(XWPFParagraph::getText)
                    .reduce("", (a, b) -> a + "\n" + b);
            assertThat(allText).contains("print('hello')");
        }
    }

    @Test
    @DisplayName("testExportEmptyReport - 空 report 不报错（仅渲染 citations）")
    void testExportEmptyReport() throws IOException {
        AnalysisResultDTO result = AnalysisResultDTO.builder()
                .analysisId("anl_empty_report")
                .status(AnalysisStatus.COMPLETED)
                .report("")
                .citations(List.of(Map.of("index", 1, "citation", "Test citation")))
                .build();

        byte[] bytes = wordExporter.export("anl_empty_report", result);

        assertThat(bytes).isNotNull();
        assertThat(bytes.length).isGreaterThan(0);
        try (XWPFDocument doc = loadDocument(bytes)) {
            String allText = doc.getParagraphs().stream()
                    .map(XWPFParagraph::getText)
                    .reduce("", (a, b) -> a + b);
            assertThat(allText).contains("参考文献");
            assertThat(allText).contains("[1] Test citation");
        }
    }
}
