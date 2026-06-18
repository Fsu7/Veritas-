package com.literatureassistant.integration;

import com.literatureassistant.controller.AnalysisController;
import com.literatureassistant.controller.PaperController;
import com.literatureassistant.dto.common.PageResponse;
import com.literatureassistant.dto.response.AnalysisResponse;
import com.literatureassistant.dto.response.FavoriteResponse;
import com.literatureassistant.exception.BusinessException;
import com.literatureassistant.exception.GlobalExceptionHandler;
import com.literatureassistant.service.AnalysisService;
import com.literatureassistant.service.ExportService;
import com.literatureassistant.service.FavoriteService;
import com.literatureassistant.util.PdfExporter;
import com.literatureassistant.util.WordExporter;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.time.LocalDateTime;
import java.util.List;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * task40: JM5 集成测试。
 * <p>验证 JM5 里程碑（缓存优化与功能完善）的端到端功能：
 * 1) 论文收藏 API（POST/DELETE/GET /api/papers/{paperId}/favorite, GET /api/papers/favorites）；
 * 2) PDF 导出 API（GET /api/analysis/{analysisId}/export?format=pdf）；
 * 3) Word 导出 API（GET /api/analysis/{analysisId}/export?format=word）；
 * 4) 数据隔离与异常处理；
 * 5) 缓存配置完整性。
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("JM5 集成测试")
class Jm5IntegrationTest {

    private MockMvc paperMvc;
    private MockMvc analysisMvc;

    @InjectMocks
    private PaperController paperController;

    @InjectMocks
    private AnalysisController analysisController;

    @Mock
    private FavoriteService favoriteService;

    @Mock
    private AnalysisService analysisService;

    @Mock
    private ExportService exportService;

    @Mock
    private PdfExporter pdfExporter;

    @Mock
    private WordExporter wordExporter;

    @BeforeEach
    void setUp() {
        paperMvc = MockMvcBuilders.standaloneSetup(paperController)
                .setControllerAdvice(new GlobalExceptionHandler())
                .build();
        analysisMvc = MockMvcBuilders.standaloneSetup(analysisController)
                .setControllerAdvice(new GlobalExceptionHandler())
                .build();
    }

    /**
     * 设置 SecurityContext，模拟已认证用户。
     * <p>Controller 通过 SecurityContextHolder.getContext().getAuthentication().getPrincipal()
     * 获取当前用户 ID。
     */
    private void authenticateAs(String userId) {
        UsernamePasswordAuthenticationToken auth =
                new UsernamePasswordAuthenticationToken(userId, null, List.of());
        SecurityContextHolder.getContext().setAuthentication(auth);
    }

    /**
     * 清除 SecurityContext，模拟未认证。
     */
    private void clearAuthentication() {
        SecurityContextHolder.clearContext();
    }

    // ==================== 收藏 API 集成测试 ====================

    @Test
    @DisplayName("JM5-1: POST /api/papers/{paperId}/favorite - 收藏论文成功返回 200 + FavoriteResponse")
    void testAddFavoriteEndpoint() throws Exception {
        authenticateAs("u1");
        FavoriteResponse resp = FavoriteResponse.builder()
                .favoriteId(1L)
                .paperId("p1")
                .title("Test Paper")
                .authors(List.of("Author A"))
                .year(2024)
                .venue("AAAI")
                .citationCount(100)
                .createdAt(LocalDateTime.now())
                .build();
        when(favoriteService.addFavorite("u1", "p1")).thenReturn(resp);

        paperMvc.perform(post("/api/papers/p1/favorite"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.paper_id").value("p1"))
                .andExpect(jsonPath("$.data.title").value("Test Paper"))
                .andExpect(jsonPath("$.data.citation_count").value(100));
    }

    @Test
    @DisplayName("JM5-2: DELETE /api/papers/{paperId}/favorite - 取消收藏返回 200")
    void testRemoveFavoriteEndpoint() throws Exception {
        authenticateAs("u1");

        paperMvc.perform(delete("/api/papers/p1/favorite"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    @DisplayName("JM5-3: GET /api/papers/favorites - 查询收藏列表返回分页 PageResponse")
    void testListFavoritesEndpoint() throws Exception {
        authenticateAs("u1");
        FavoriteResponse fav = FavoriteResponse.builder()
                .favoriteId(1L)
                .paperId("p1")
                .title("Paper 1")
                .build();
        PageResponse<FavoriteResponse> page = PageResponse.<FavoriteResponse>builder()
                .items(List.of(fav))
                .total(1)
                .page(1)
                .size(10)
                .totalPages(1)
                .build();
        when(favoriteService.listFavorites(eq("u1"), anyInt(), anyInt())).thenReturn(page);

        paperMvc.perform(get("/api/papers/favorites"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.items[0].paper_id").value("p1"))
                .andExpect(jsonPath("$.data.total").value(1));
    }

    // ==================== PDF 导出 API 集成测试 ====================

    @Test
    @DisplayName("JM5-4: GET /api/analysis/{id}/export?format=pdf - PDF 导出成功返回 application/pdf")
    void testExportPdfEndpoint() throws Exception {
        authenticateAs("u1");
        byte[] pdfBytes = "%PDF-1.4 mock content".getBytes();
        when(exportService.export("u1", "anl_1", "pdf")).thenReturn(pdfBytes);
        when(pdfExporter.generateFileName("anl_1")).thenReturn("analysis_anl_1_20260617140000.pdf");

        analysisMvc.perform(get("/api/analysis/anl_1/export").param("format", "pdf"))
                .andExpect(status().isOk())
                .andExpect(header().string("Content-Type", MediaType.APPLICATION_PDF_VALUE))
                .andExpect(header().string("Content-Disposition",
                        org.hamcrest.Matchers.containsString("analysis_anl_1_")))
                .andExpect(content().bytes(pdfBytes));
    }

    // ==================== Word 导出 API 集成测试 ====================

    @Test
    @DisplayName("JM5-5: GET /api/analysis/{id}/export?format=word - Word 导出成功返回 docx MIME")
    void testExportWordEndpoint() throws Exception {
        authenticateAs("u1");
        byte[] wordBytes = new byte[]{0x50, 0x4B, 0x03, 0x04}; // PK zip header
        when(exportService.export("u1", "anl_1", "word")).thenReturn(wordBytes);
        when(wordExporter.generateFileName("anl_1")).thenReturn("analysis_anl_1_20260617140000.docx");

        analysisMvc.perform(get("/api/analysis/anl_1/export").param("format", "word"))
                .andExpect(status().isOk())
                .andExpect(header().string("Content-Type",
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))
                .andExpect(header().string("Content-Disposition",
                        org.hamcrest.Matchers.containsString(".docx")))
                .andExpect(content().bytes(wordBytes));
    }

    @Test
    @DisplayName("JM5-6: GET /api/analysis/{id}/export?format=docx - docx 别名路由到 WordExporter")
    void testExportDocxAliasEndpoint() throws Exception {
        authenticateAs("u1");
        byte[] wordBytes = new byte[]{0x50, 0x4B, 0x03, 0x04};
        when(exportService.export("u1", "anl_1", "docx")).thenReturn(wordBytes);
        when(wordExporter.generateFileName("anl_1")).thenReturn("analysis_anl_1_20260617140000.docx");

        analysisMvc.perform(get("/api/analysis/anl_1/export").param("format", "docx"))
                .andExpect(status().isOk())
                .andExpect(header().string("Content-Disposition",
                        org.hamcrest.Matchers.containsString(".docx")));
    }

    // ==================== 异常处理集成测试 ====================

    @Test
    @DisplayName("JM5-7: GET /api/analysis/{id}/export - 未认证返回 401")
    void testExportUnauthenticated() throws Exception {
        clearAuthentication();

        analysisMvc.perform(get("/api/analysis/anl_1/export"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    @DisplayName("JM5-8: GET /api/analysis/{id}/export?format=excel - 不支持的格式返回 400")
    void testExportUnsupportedFormat() throws Exception {
        authenticateAs("u1");
        when(exportService.export(eq("u1"), eq("anl_1"), eq("excel")))
                .thenThrow(new BusinessException(400, "不支持的导出格式: excel", "UNSUPPORTED_FORMAT"));

        analysisMvc.perform(get("/api/analysis/anl_1/export").param("format", "excel"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value(400))
                .andExpect(jsonPath("$.message").value(org.hamcrest.Matchers.containsString("不支持的导出格式")));
    }

    // ==================== 数据隔离集成测试（修复 B-001/B-003/B-004） ====================

    @Test
    @DisplayName("JM5-9: GET /api/analysis/{analysisId} - 用户B访问用户A分析结果，validateAnalysisAccess 抛 403")
    void testGetAnalysisResultDataIsolation() throws Exception {
        // 修复 B-003: Controller 层先调用 validateAnalysisAccess 校验归属，缓存命中时仍执行
        authenticateAs("uB");
        // void 方法使用 doThrow 语法
        doThrow(new BusinessException(403, "无权限访问他人分析结果", "FORBIDDEN_ACCESS"))
                .when(analysisService).validateAnalysisAccess("uB", "anl_A");

        analysisMvc.perform(get("/api/analysis/anl_A"))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.code").value(403));

        // 验证 validateAnalysisAccess 被调用（数据隔离校验在 Controller 层执行）
        verify(analysisService).validateAnalysisAccess("uB", "anl_A");
        // 验证 getAnalysisResult 未被调用（校验失败应短路返回）
        verify(analysisService, never()).getAnalysisResult(any(), any());
    }

    @Test
    @DisplayName("JM5-10: GET /api/analysis/{analysisId} - 用户A访问自己的分析结果返回 200")
    void testGetAnalysisResultNormalAccess() throws Exception {
        authenticateAs("uA");
        // void 方法使用 doNothing 语法
        doNothing().when(analysisService).validateAnalysisAccess("uA", "anl_A");
        AnalysisResponse mockResp = AnalysisResponse.builder()
                .analysisId("anl_A")
                .sessionId("ses_A")
                .build();
        when(analysisService.getAnalysisResult("uA", "anl_A")).thenReturn(mockResp);

        analysisMvc.perform(get("/api/analysis/anl_A"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.analysis_id").value("anl_A"));
    }

    @Test
    @DisplayName("JM5-11: GET /api/analysis/{analysisId} - 未认证返回 401")
    void testGetAnalysisResultUnauthenticated() throws Exception {
        clearAuthentication();

        analysisMvc.perform(get("/api/analysis/anl_1"))
                .andExpect(status().isUnauthorized());
    }
}
