package com.literatureassistant.util;

import com.itextpdf.io.font.PdfEncodings;
import com.itextpdf.kernel.events.Event;
import com.itextpdf.kernel.events.IEventHandler;
import com.itextpdf.kernel.events.PdfDocumentEvent;
import com.itextpdf.kernel.font.PdfFont;
import com.itextpdf.kernel.font.PdfFontFactory;
import com.itextpdf.kernel.geom.PageSize;
import com.itextpdf.kernel.pdf.PdfDocument;
import com.itextpdf.kernel.pdf.PdfWriter;
import com.itextpdf.kernel.pdf.canvas.PdfCanvas;
import com.itextpdf.layout.Document;
import com.itextpdf.layout.element.ListItem;
import com.itextpdf.layout.element.Paragraph;
import com.literatureassistant.dto.response.AnalysisResultDTO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Map;

/**
 * PDF 导出工具类。
 * <p>使用 iText 7 将分析结果（Markdown report + citations）导出为 PDF。
 * <p>中文字体使用 font-asian 包的 STSong-Light + UniGB-UCS2-H 编码。
 * <p>页脚显示 "AI生成，仅供参考"。
 * <p>task37 新建。
 *
 * @author XH-202630 Literature Assistant
 * @since 0.5
 */
@Component
@Slf4j
public class PdfExporter {

    private static final String FONT_NAME = "STSong-Light";
    private static final String FONT_ENCODING = "UniGB-UCS2-H";
    private static final String FOOTER_TEXT = "AI生成，仅供参考";
    private static final DateTimeFormatter FILE_NAME_FORMATTER = DateTimeFormatter.ofPattern("yyyyMMddHHmmss");

    /**
     * 导出 PDF。
     *
     * @param analysisId 分析任务 ID（用于文件名）
     * @param result     分析结果 DTO（含 report 和 citations）
     * @return PDF 字节数组
     */
    public byte[] export(String analysisId, AnalysisResultDTO result) throws IOException {
        try (ByteArrayOutputStream baos = new ByteArrayOutputStream()) {
            PdfWriter writer = new PdfWriter(baos);
            PdfDocument pdf = new PdfDocument(writer);
            Document document = new Document(pdf, PageSize.A4);

            // 中文字体（font-asian 包的 STSong-Light + UniGB-UCS2-H 编码）
            PdfFont font = resolveChineseFont();
            document.setFont(font);

            // 页脚事件
            pdf.addEventHandler(PdfDocumentEvent.END_PAGE, new FooterEventHandler(font));

            // 渲染 Markdown
            renderMarkdown(document, result.getReport(), font);

            // 渲染 citations
            renderCitations(document, result.getCitations());

            document.close();
            return baos.toByteArray();
        }
    }

    /**
     * 解析中文字体：优先 STSong-Light，失败时 fallback Helvetica。
     */
    private PdfFont resolveChineseFont() {
        try {
            return PdfFontFactory.createFont(FONT_NAME, FONT_ENCODING);
        } catch (Exception e) {
            log.warn("Failed to load STSong-Light font, fallback to Helvetica: {}", e.getMessage());
            try {
                return PdfFontFactory.createFont();
            } catch (IOException ex) {
                throw new RuntimeException("Failed to load default font", ex);
            }
        }
    }

    /**
     * 渲染 Markdown 为 PDF 元素。
     * <p>支持：#/##/### 标题、段落、- 无序列表、``` 代码块。
     *
     * @param font 中文字体（用于代码块等场景的字体回退）
     */
    private void renderMarkdown(Document document, String markdown, PdfFont font) {
        if (markdown == null || markdown.isBlank()) {
            return;
        }
        String[] lines = markdown.split("\n", -1);
        boolean inCodeBlock = false;
        com.itextpdf.layout.element.List currentList = null;

        for (String line : lines) {
            // 代码块切换
            if (line.trim().startsWith("```")) {
                if (inCodeBlock) {
                    inCodeBlock = false;
                    continue;
                } else {
                    inCodeBlock = true;
                    continue;
                }
            }
            if (inCodeBlock) {
                Paragraph code = new Paragraph(line.isEmpty() ? " " : line)
                        .setFont(font)
                        .setFontSize(9)
                        .setMarginLeft(20)
                        .setBackgroundColor(new com.itextpdf.kernel.colors.DeviceRgb(240, 240, 240));
                document.add(code);
                continue;
            }

            // 标题
            if (line.startsWith("### ")) {
                if (currentList != null) {
                    document.add(currentList);
                    currentList = null;
                }
                document.add(new Paragraph(line.substring(4)).setBold().setFontSize(13));
                continue;
            }
            if (line.startsWith("## ")) {
                if (currentList != null) {
                    document.add(currentList);
                    currentList = null;
                }
                document.add(new Paragraph(line.substring(3)).setBold().setFontSize(15));
                continue;
            }
            if (line.startsWith("# ")) {
                if (currentList != null) {
                    document.add(currentList);
                    currentList = null;
                }
                document.add(new Paragraph(line.substring(2)).setBold().setFontSize(18));
                continue;
            }
            // 无序列表
            if (line.trim().startsWith("- ")) {
                if (currentList == null) {
                    currentList = new com.itextpdf.layout.element.List();
                }
                currentList.add(new ListItem(line.trim().substring(2)));
                continue;
            }
            // 空行
            if (line.isBlank()) {
                if (currentList != null) {
                    document.add(currentList);
                    currentList = null;
                }
                continue;
            }
            // 普通段落
            if (currentList != null) {
                document.add(currentList);
                currentList = null;
            }
            document.add(new Paragraph(line));
        }
        if (currentList != null) {
            document.add(currentList);
        }
    }

    /**
     * 渲染 citations 为引用列表。
     * <p>每条渲染为 "[index] citation_text"。空 citations 不渲染该 section。
     */
    private void renderCitations(Document document, List<Map<String, Object>> citations) {
        if (citations == null || citations.isEmpty()) {
            return;
        }
        document.add(new Paragraph("参考文献").setBold().setFontSize(14).setMarginTop(20));
        for (Map<String, Object> c : citations) {
            Object idx = c.get("index");
            Object citation = c.get("citation");
            String line = "[" + (idx != null ? idx : "") + "] " + (citation != null ? citation : "");
            document.add(new Paragraph(line).setFontSize(10));
        }
    }

    /**
     * 生成文件名：analysis_{analysisId}_{yyyyMMddHHmmss}.pdf
     */
    public String generateFileName(String analysisId) {
        return "analysis_" + analysisId + "_" + LocalDateTime.now().format(FILE_NAME_FORMATTER) + ".pdf";
    }

    /**
     * 页脚事件处理器：每页页脚居中显示 "AI生成，仅供参考"。
     */
    private static class FooterEventHandler implements IEventHandler {
        private final PdfFont font;

        FooterEventHandler(PdfFont font) {
            this.font = font;
        }

        @Override
        public void handleEvent(Event event) {
            PdfDocumentEvent docEvent = (PdfDocumentEvent) event;
            PdfDocument pdf = docEvent.getDocument();
            PdfCanvas canvas = new PdfCanvas(docEvent.getPage());
            PageSize pageSize = pdf.getDefaultPageSize();
            float x = pageSize.getWidth() / 2;
            float y = 20;
            canvas.saveState()
                    .setFillColor(com.itextpdf.kernel.colors.ColorConstants.GRAY)
                    .beginText()
                    .setFontAndSize(font, 8)
                    .moveText(x - 60, y)
                    .showText(FOOTER_TEXT)
                    .endText()
                    .restoreState();
            canvas.release();
        }
    }
}
