package com.literatureassistant.controller;

import com.literatureassistant.dto.common.PageResponse;
import com.literatureassistant.dto.response.PaperDetailResponse;
import com.literatureassistant.dto.response.PaperResponse;
import com.literatureassistant.exception.BusinessException;
import com.literatureassistant.exception.GlobalExceptionHandler;
import com.literatureassistant.exception.ResourceNotFoundException;
import com.literatureassistant.service.PaperService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.util.List;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@ExtendWith(MockitoExtension.class)
class PaperControllerTest {

    @InjectMocks
    private PaperController paperController;

    @Mock
    private PaperService paperService;

    private MockMvc mockMvc;

    @BeforeEach
    void setUp() {
        mockMvc = MockMvcBuilders.standaloneSetup(paperController)
                .setControllerAdvice(new GlobalExceptionHandler())
                .build();
    }

    @Test
    @DisplayName("GET /api/papers - 返回分页JSON，字段为snake_case")
    void listPapers_returnsPageJson() throws Exception {
        PaperResponse paperResponse = PaperResponse.builder()
                .paperId("arxiv_2024_001")
                .title("Multi-Agent Systems: A Survey")
                .authors(List.of("Wang, L."))
                .year(2024)
                .venue("AAAI")
                .keywords(List.of("multi-agent"))
                .citationCount(1200)
                .build();
        PageResponse<PaperResponse> pageResponse = PageResponse.<PaperResponse>builder()
                .items(List.of(paperResponse))
                .total(1)
                .page(1)
                .size(10)
                .totalPages(1)
                .build();

        when(paperService.listPapers(anyInt(), anyInt())).thenReturn(pageResponse);

        mockMvc.perform(get("/api/papers")
                        .param("page", "1")
                        .param("size", "10"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.message").value("success"))
                .andExpect(jsonPath("$.data.items[0].paper_id").value("arxiv_2024_001"))
                .andExpect(jsonPath("$.data.items[0].title").value("Multi-Agent Systems: A Survey"))
                .andExpect(jsonPath("$.data.items[0].citation_count").value(1200))
                .andExpect(jsonPath("$.data.items[0].year").value(2024))
                .andExpect(jsonPath("$.data.total").value(1))
                .andExpect(jsonPath("$.data.page").value(1))
                .andExpect(jsonPath("$.data.size").value(10))
                .andExpect(jsonPath("$.data.total_pages").value(1));
    }

    @Test
    @DisplayName("GET /api/papers - 默认page=1, size=10")
    void listPapers_defaultParams() throws Exception {
        when(paperService.listPapers(1, 10))
                .thenReturn(PageResponse.<PaperResponse>builder()
                        .items(List.of()).total(0).page(1).size(10).totalPages(0).build());

        mockMvc.perform(get("/api/papers"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    @DisplayName("GET /api/papers/{paperId} - 返回详情JSON")
    void getPaperDetail_returnsDetailJson() throws Exception {
        PaperDetailResponse detail = PaperDetailResponse.builder()
                .paperId("arxiv_2024_001")
                .title("Multi-Agent Systems: A Survey")
                .authors(List.of("Wang, L."))
                .year(2024)
                .venue("AAAI")
                .keywords(List.of("multi-agent"))
                .citationCount(1200)
                .abstractText("This paper provides a comprehensive survey...")
                .pdfUrl("https://arxiv.org/pdf/2401.001")
                .build();

        when(paperService.getPaperDetail("arxiv_2024_001")).thenReturn(detail);

        mockMvc.perform(get("/api/papers/arxiv_2024_001"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.paper_id").value("arxiv_2024_001"))
                .andExpect(jsonPath("$.data.abstract").value("This paper provides a comprehensive survey..."))
                .andExpect(jsonPath("$.data.pdf_url").value("https://arxiv.org/pdf/2401.001"))
                .andExpect(jsonPath("$.data.citation_count").value(1200));
    }

    @Test
    @DisplayName("GET /api/papers/{paperId} - 不存在返回404")
    void getPaperDetail_notFound_returns404() throws Exception {
        when(paperService.getPaperDetail("nonexistent"))
                .thenThrow(new ResourceNotFoundException("Paper", "nonexistent"));

        mockMvc.perform(get("/api/papers/nonexistent"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value(404))
                .andExpect(jsonPath("$.message").value("Paper not found: nonexistent"));
    }

    @Test
    @DisplayName("GET /api/papers/search - 正常搜索返回JSON")
    void searchPapers_returnsJson() throws Exception {
        PaperResponse paperResponse = PaperResponse.builder()
                .paperId("arxiv_2024_001")
                .title("Multi-Agent Systems")
                .authors(List.of("Wang, L."))
                .year(2024)
                .venue("AAAI")
                .keywords(List.of())
                .citationCount(100)
                .build();
        PageResponse<PaperResponse> pageResponse = PageResponse.<PaperResponse>builder()
                .items(List.of(paperResponse))
                .total(1)
                .page(1)
                .size(10)
                .totalPages(1)
                .build();

        when(paperService.searchPapers(
                anyString(), any(), any(), any(), anyString(), anyInt(), anyInt()))
                .thenReturn(pageResponse);

        mockMvc.perform(get("/api/papers/search")
                        .param("q", "agent")
                        .param("sort", "relevance")
                        .param("page", "1")
                        .param("size", "10"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.items[0].paper_id").value("arxiv_2024_001"))
                .andExpect(jsonPath("$.data.total").value(1));
    }

    @Test
    @DisplayName("GET /api/papers/search - 缺少q参数返回400")
    void searchPapers_missingQ_throws() throws Exception {
        mockMvc.perform(get("/api/papers/search"))
                .andExpect(status().isBadRequest());
    }

    @Test
    @DisplayName("GET /api/papers/search - q为空返回400")
    void searchPapers_emptyQ_returns400() throws Exception {
        when(paperService.searchPapers(
                anyString(), any(), any(), any(), anyString(), anyInt(), anyInt()))
                .thenThrow(new IllegalArgumentException("搜索关键词不能为空"));

        mockMvc.perform(get("/api/papers/search").param("q", "   "))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value(400))
                .andExpect(jsonPath("$.message").value("搜索关键词不能为空"));
    }

    @Test
    @DisplayName("GET /api/papers/search - yearFrom>yearTo返回400")
    void searchPapers_yearRangeInvalid_returns400() throws Exception {
        when(paperService.searchPapers(
                anyString(), any(), any(), any(), anyString(), anyInt(), anyInt()))
                .thenThrow(new BusinessException(400, "yearFrom不能大于yearTo", "INVALID_PARAMETER"));

        mockMvc.perform(get("/api/papers/search")
                        .param("q", "agent")
                        .param("yearFrom", "2024")
                        .param("yearTo", "2020"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value(400))
                .andExpect(jsonPath("$.message").value("yearFrom不能大于yearTo"));
    }
}
