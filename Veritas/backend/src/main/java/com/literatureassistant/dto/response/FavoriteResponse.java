package com.literatureassistant.dto.response;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.time.LocalDateTime;
import java.util.List;

/**
 * 论文收藏响应 DTO。
 * <p>含收藏记录信息 + 论文详情（title/authors/year/venue/citationCount）。
 * <p>task36 新建。
 *
 * @author XH-202630 Literature Assistant
 * @since 0.5
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class FavoriteResponse implements Serializable {

    private static final long serialVersionUID = 1L;

    private Long favoriteId;

    @JsonProperty("paper_id")
    private String paperId;

    private String title;

    private List<String> authors;

    private Integer year;

    private String venue;

    @JsonProperty("citation_count")
    private Integer citationCount;

    @JsonProperty("created_at")
    private LocalDateTime createdAt;
}
