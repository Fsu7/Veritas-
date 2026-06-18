package com.literatureassistant.util;

import com.literatureassistant.dto.response.AnalysisResultDTO;
import lombok.extern.slf4j.Slf4j;
import org.apache.poi.xwpf.usermodel.ParagraphAlignment;
import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.apache.poi.xwpf.usermodel.XWPFParagraph;
import org.apache.poi.xwpf.usermodel.XWPFRun;
import org.springframework.stereotype.Component;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Map;

/**
 * Word 导出工具类。
 * <p>使用 Apache POI 5.2.3 将分析结果（Markdown report + citations）导出为 .docx。
 * <p>中文字体使用宋体（SimSun），POI 默认支持中文。
 * <p>页脚显示 "AI生成，仅供参考"。
 * <p>task38 新建。
 *
 * @author XH-202630 Literature Assistant
 * @since 0.5
 */
@Component
@Slf4j
public class WordExporter {

    private static final String FONT_NAME = "宋体";
    private static final String FOOTER_TEXT = "AI生成，仅供参考";
    private static final DateTimeFormatter FILE_NAME_FORMATTER = DateTimeFormatter.ofPattern("yyyyMMddHHmmss");

    /**
     * 导出 Word（.docx）。
     *
     * @param analysisId 分析任务 ID（用于文件名）
     * @param result     分析结果 DTO（含 report 和 citations）
     * @return Word 字节数组
     */
    public byte[] export(String analysisId, AnalysisResultDTO result) throws IOException {
        try (XWPFDocument doc = new XWPFDocument();
             ByteArrayOutputStream baos = new ByteArrayOutputStream()) {

            // 渲染 Markdown
            renderMarkdown(doc, result.getReport());

            // 渲染 citations
            renderCitations(doc, result.getCitations());

            // 页脚
            addFooter(doc);

            doc.write(baos);
            return baos.toByteArray();
        }
    }

    /**
     * 渲染 Markdown 为 Word 段落。
     * <p>支持：#/##/### 标题、段落、- 无序列表、``` 代码块。
     */
    private void renderMarkdown(XWPFDocument doc, String markdown) {
        if (markdown == null || markdown.isBlank()) {
            return;
        }
        String[] lines = markdown.split("\n", -1);
        boolean inCodeBlock = false;

        for (String line : lines) {
            // 代码块切换
            if (line.trim().startsWith("```")) {
                inCodeBlock = !inCodeBlock;
                continue;
            }
            if (inCodeBlock) {
                XWPFParagraph p = doc.createParagraph();
                p.setAlignment(ParagraphAlignment.LEFT);
                XWPFRun run = p.createRun();
                run.setFontFamily(FONT_NAME);
                run.setFontSize(9);
                run.setText(line.isEmpty() ? " " : line);
                // 代码块背景色（浅灰）
                run.getCTR().getRPr().addNewShd().setFill("F0F0F0");
                continue;
            }

            // 标题
            if (line.startsWith("### ")) {
                addHeading(doc, line.substring(4), 13);
                continue;
            }
            if (line.startsWith("## ")) {
                addHeading(doc, line.substring(3), 15);
                continue;
            }
            if (line.startsWith("# ")) {
                addHeading(doc, line.substring(2), 18);
                continue;
            }
            // 无序列表
            if (line.trim().startsWith("- ")) {
                XWPFParagraph p = doc.createParagraph();
                p.setIndentationLeft(360); // 0.25 inch
                XWPFRun run = p.createRun();
                run.setFontFamily(FONT_NAME);
                run.setFontSize(11);
                run.setText("• " + line.trim().substring(2));
                continue;
            }
            // 空行
            if (line.isBlank()) {
                doc.createParagraph();
                continue;
            }
            // 普通段落
            XWPFParagraph p = doc.createParagraph();
            XWPFRun run = p.createRun();
            run.setFontFamily(FONT_NAME);
            run.setFontSize(11);
            run.setText(line);
        }
    }

    /**
     * 添加标题段落。
     */
    private void addHeading(XWPFDocument doc, String text, int fontSize) {
        XWPFParagraph p = doc.createParagraph();
        XWPFRun run = p.createRun();
        run.setFontFamily(FONT_NAME);
        run.setFontSize(fontSize);
        run.setBold(true);
        run.setText(text);
    }

    /**
     * 渲染 citations 为引用列表。
     * <p>每条渲染为 "[index] citation_text"。空 citations 不渲染该 section。
     */
    private void renderCitations(XWPFDocument doc, List<Map<String, Object>> citations) {
        if (citations == null || citations.isEmpty()) {
            return;
        }
        addHeading(doc, "参考文献", 14);
        for (Map<String, Object> c : citations) {
            Object idx = c.get("index");
            Object citation = c.get("citation");
            String line = "[" + (idx != null ? idx : "") + "] " + (citation != null ? citation : "");
            XWPFParagraph p = doc.createParagraph();
            XWPFRun run = p.createRun();
            run.setFontFamily(FONT_NAME);
            run.setFontSize(10);
            run.setText(line);
        }
    }

    /**
     * 添加页脚 "AI生成，仅供参考"。
     */
    private void addFooter(XWPFDocument doc) {
        org.apache.poi.xwpf.usermodel.XWPFFooter footer =
                doc.createFooter(org.apache.poi.wp.usermodel.HeaderFooterType.DEFAULT);
        XWPFParagraph p = footer.getParagraphArray(0) != null
                ? footer.getParagraphArray(0) : footer.createParagraph();
        p.setAlignment(ParagraphAlignment.CENTER);
        XWPFRun run = p.createRun();
        run.setFontFamily(FONT_NAME);
        run.setFontSize(8);
        run.setItalic(true);
        run.setText(FOOTER_TEXT);
    }

    /**
     * 生成文件名：analysis_{analysisId}_{yyyyMMddHHmmss}.docx
     */
    public String generateFileName(String analysisId) {
        return "analysis_" + analysisId + "_" + LocalDateTime.now().format(FILE_NAME_FORMATTER) + ".docx";
    }
}
