package com.literatureassistant.dto.response;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

/**
 * 论文搜索结果 DTO，对齐 Python 端 {@code SearchResultItem} Pydantic Schema（6 字段）。
 * <p>{@code abstract} 是 Java 关键字，字段命名为 {@code abstractText}，通过 {@link JsonProperty} 映射为 JSON 字段 {@code abstract}。
 * <p>其它字段命名遵循全局 Jackson SNAKE_CASE 配置。
 *
 * @author XH-202630 Literature Assistant
 * @since 0.3
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class PaperSearchResultDTO implements Serializable {

    private static final long serialVersionUID = 1L;

    private String paperId;
    private String title;

    @JsonProperty("abstract")
    private String abstractText;

    private Double score;
    private Integer year;
    private String venue;
}
