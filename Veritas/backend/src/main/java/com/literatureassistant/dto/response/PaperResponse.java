package com.literatureassistant.dto.response;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.experimental.SuperBuilder;

import java.util.List;

@Data
@SuperBuilder
@NoArgsConstructor
@AllArgsConstructor
public class PaperResponse {

    @JsonProperty("paper_id")
    private String paperId;

    private String title;

    private List<String> authors;

    private Integer year;

    private String venue;

    private List<String> keywords;

    @JsonProperty("citation_count")
    private Integer citationCount;
}
