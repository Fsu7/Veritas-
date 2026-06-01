package com.literatureassistant.mapper;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.literatureassistant.dto.response.PaperDetailResponse;
import com.literatureassistant.dto.response.PaperResponse;
import com.literatureassistant.entity.Paper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.time.LocalDateTime;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class PaperMapperTest {

    private PaperMapper paperMapper;

    @BeforeEach
    void setUp() throws Exception {
        ObjectMapper objectMapper = new ObjectMapper();
        PaperMapperImpl impl = new PaperMapperImpl();
        java.lang.reflect.Field helperField = PaperMapperImpl.class.getDeclaredField("jsonStringListHelper");
        helperField.setAccessible(true);
        helperField.set(impl, new PaperMapper.JsonStringListHelper(objectMapper));
        paperMapper = impl;
    }

    @Test
    @DisplayName("toResponse - JSON字符串authors/keywords正确反序列化为List")
    void toResponse_jsonStringParsedToList() {
        Paper paper = Paper.builder()
                .id(1L)
                .paperId("arxiv_2024_001")
                .title("Multi-Agent Systems: A Survey")
                .authors("[\"Wang, L.\",\"Chen, X.\"]")
                .keywords("[\"multi-agent\",\"survey\"]")
                .year(2024)
                .venue("AAAI")
                .citationCount(1200)
                .build();

        PaperResponse response = paperMapper.toResponse(paper);

        assertThat(response).isNotNull();
        assertThat(response.getPaperId()).isEqualTo("arxiv_2024_001");
        assertThat(response.getTitle()).isEqualTo("Multi-Agent Systems: A Survey");
        assertThat(response.getAuthors()).containsExactly("Wang, L.", "Chen, X.");
        assertThat(response.getKeywords()).containsExactly("multi-agent", "survey");
        assertThat(response.getYear()).isEqualTo(2024);
        assertThat(response.getVenue()).isEqualTo("AAAI");
        assertThat(response.getCitationCount()).isEqualTo(1200);
    }

    @Test
    @DisplayName("toResponse - authors为null返回空列表")
    void toResponse_nullAuthors_returnsEmptyList() {
        Paper paper = Paper.builder()
                .paperId("p1")
                .title("Test")
                .authors(null)
                .keywords(null)
                .year(2024)
                .citationCount(0)
                .build();

        PaperResponse response = paperMapper.toResponse(paper);

        assertThat(response.getAuthors()).isEmpty();
        assertThat(response.getKeywords()).isEmpty();
    }

    @Test
    @DisplayName("toResponse - authors为空字符串返回空列表")
    void toResponse_emptyString_returnsEmptyList() {
        Paper paper = Paper.builder()
                .paperId("p1")
                .title("Test")
                .authors("")
                .keywords("   ")
                .year(2024)
                .citationCount(0)
                .build();

        PaperResponse response = paperMapper.toResponse(paper);

        assertThat(response.getAuthors()).isEmpty();
        assertThat(response.getKeywords()).isEmpty();
    }

    @Test
    @DisplayName("toResponse - 非法JSON字符串返回空列表且不抛异常")
    void toResponse_invalidJson_returnsEmptyList() {
        Paper paper = Paper.builder()
                .paperId("p1")
                .title("Test")
                .authors("not-a-valid-json{")
                .keywords("[unclosed")
                .year(2024)
                .citationCount(0)
                .build();

        PaperResponse response = paperMapper.toResponse(paper);

        assertThat(response.getAuthors()).isEmpty();
        assertThat(response.getKeywords()).isEmpty();
    }

    @Test
    @DisplayName("toDetailResponse - 正确映射abstract/pdfUrl/createdAt/updatedAt")
    void toDetailResponse_mapsAllDetailFields() {
        LocalDateTime now = LocalDateTime.of(2026, 5, 26, 10, 0, 0);
        Paper paper = Paper.builder()
                .id(1L)
                .paperId("arxiv_2024_001")
                .title("Multi-Agent Systems: A Survey")
                .authors("[\"Wang, L.\"]")
                .abstractText("This paper provides a comprehensive survey...")
                .year(2024)
                .venue("AAAI")
                .keywords("[\"multi-agent\"]")
                .citationCount(1200)
                .pdfUrl("https://arxiv.org/pdf/2401.001")
                .createdAt(now)
                .updatedAt(now)
                .build();

        PaperDetailResponse response = paperMapper.toDetailResponse(paper);

        assertThat(response).isNotNull();
        assertThat(response.getPaperId()).isEqualTo("arxiv_2024_001");
        assertThat(response.getTitle()).isEqualTo("Multi-Agent Systems: A Survey");
        assertThat(response.getAuthors()).containsExactly("Wang, L.");
        assertThat(response.getKeywords()).containsExactly("multi-agent");
        assertThat(response.getAbstractText()).isEqualTo("This paper provides a comprehensive survey...");
        assertThat(response.getPdfUrl()).isEqualTo("https://arxiv.org/pdf/2401.001");
        assertThat(response.getCreatedAt()).isEqualTo(now);
        assertThat(response.getUpdatedAt()).isEqualTo(now);
    }

    @Test
    @DisplayName("toDetailResponse - abstract为null时正确返回null")
    void toDetailResponse_nullAbstract_returnsNull() {
        Paper paper = Paper.builder()
                .paperId("p1")
                .title("Test")
                .authors(null)
                .keywords(null)
                .abstractText(null)
                .pdfUrl(null)
                .year(2024)
                .citationCount(0)
                .build();

        PaperDetailResponse response = paperMapper.toDetailResponse(paper);

        assertThat(response.getAbstractText()).isNull();
        assertThat(response.getPdfUrl()).isNull();
    }
}
