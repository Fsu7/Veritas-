package com.literatureassistant.dto.response;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class PaperResponseTest {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Test
    @DisplayName("serialize - 输出snake_case字段 (paper_id, citation_count)")
    void serialize_outputsSnakeCaseFields() throws Exception {
        PaperResponse response = PaperResponse.builder()
                .paperId("arxiv_2024_001")
                .title("Multi-Agent Systems: A Survey")
                .authors(List.of("Wang, L.", "Chen, X."))
                .year(2024)
                .venue("AAAI")
                .keywords(List.of("multi-agent", "survey"))
                .citationCount(1200)
                .build();

        String json = objectMapper.writeValueAsString(response);

        assertThat(json).contains("\"paper_id\":\"arxiv_2024_001\"");
        assertThat(json).contains("\"citation_count\":1200");
        assertThat(json).contains("\"title\":\"Multi-Agent Systems: A Survey\"");
        assertThat(json).contains("\"year\":2024");
        assertThat(json).contains("\"venue\":\"AAAI\"");
        assertThat(json).contains("\"authors\":[\"Wang, L.\",\"Chen, X.\"]");
        assertThat(json).contains("\"keywords\":[\"multi-agent\",\"survey\"]");
    }

    @Test
    @DisplayName("deserialize - snake_case JSON正确映射到DTO")
    void deserialize_snakeCaseJson_mapsCorrectly() throws Exception {
        String json = "{\"paper_id\":\"arxiv_2024_001\",\"title\":\"Test\",\"authors\":[\"A\"],"
                + "\"year\":2024,\"venue\":\"NeurIPS\",\"keywords\":[\"k\"],\"citation_count\":100}";

        PaperResponse response = objectMapper.readValue(json, PaperResponse.class);

        assertThat(response.getPaperId()).isEqualTo("arxiv_2024_001");
        assertThat(response.getTitle()).isEqualTo("Test");
        assertThat(response.getAuthors()).containsExactly("A");
        assertThat(response.getYear()).isEqualTo(2024);
        assertThat(response.getVenue()).isEqualTo("NeurIPS");
        assertThat(response.getKeywords()).containsExactly("k");
        assertThat(response.getCitationCount()).isEqualTo(100);
    }

    @Test
    @DisplayName("PaperDetailResponse serialize - abstract字段而非abstractText")
    void detailSerialize_usesAbstractNotAbstractText() throws Exception {
        PaperDetailResponse response = PaperDetailResponse.builder()
                .paperId("arxiv_2024_002")
                .title("Test")
                .authors(List.of())
                .year(2024)
                .venue("ACL")
                .keywords(List.of())
                .citationCount(50)
                .abstractText("This paper proposes...")
                .pdfUrl("https://arxiv.org/pdf/2401.001")
                .build();

        String json = objectMapper.writeValueAsString(response);

        assertThat(json).contains("\"abstract\":\"This paper proposes...\"");
        assertThat(json).contains("\"pdf_url\":\"https://arxiv.org/pdf/2401.001\"");
        assertThat(json).doesNotContain("abstractText");
    }

    @Test
    @DisplayName("PaperDetailResponse deserialize - abstract字段映射到abstractText")
    void detailDeserialize_abstractMapsToAbstractText() throws Exception {
        String json = "{\"paper_id\":\"p1\",\"abstract\":\"abs\",\"pdf_url\":\"url\"}";

        PaperDetailResponse response = objectMapper.readValue(json, PaperDetailResponse.class);

        assertThat(response.getAbstractText()).isEqualTo("abs");
        assertThat(response.getPdfUrl()).isEqualTo("url");
    }
}
