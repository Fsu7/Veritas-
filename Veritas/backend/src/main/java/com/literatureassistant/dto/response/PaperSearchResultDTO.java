package com.literatureassistant.dto.response;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

/**
 * Python 端搜索结果 DTO，对齐 Python 端 {@code SearchResultItem} Pydantic Schema（6 字段）。
 * <p>Python 端 model_dump(by_alias=True) 输出 camelCase (paperId/abstract/...),
 * 用 {@link JsonProperty} 显式标注覆盖全局 SNAKE_CASE。
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

    @JsonProperty("paperId")
    private String paperId;

    private String title;

    @JsonProperty("abstract")
    private String abstractText;

    private Double score;
    private Integer year;
    private String venue;
}
