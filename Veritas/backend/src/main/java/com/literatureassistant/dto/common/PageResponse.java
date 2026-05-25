package com.literatureassistant.dto.common;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.domain.Page;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PageResponse<T> {

    private List<T> items;
    private long total;
    private int page;
    private int size;

    @JsonProperty("total_pages")
    private int totalPages;

    public static <T> PageResponse<T> fromPage(Page<T> page) {
        return PageResponse.<T>builder()
                .items(page.getContent())
                .total(page.getTotalElements())
                .page(page.getNumber() + 1)
                .size(page.getSize())
                .totalPages(page.getTotalPages())
                .build();
    }

    public static <T, R> PageResponse<R> fromPage(Page<T> page, List<R> items) {
        return PageResponse.<R>builder()
                .items(items)
                .total(page.getTotalElements())
                .page(page.getNumber() + 1)
                .size(page.getSize())
                .totalPages(page.getTotalPages())
                .build();
    }
}
