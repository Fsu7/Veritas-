package com.literatureassistant.dto.common;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class PageResponseTest {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Test
    @DisplayName("fromPage(Page) 正确提取分页元数据")
    void testFromPageDirectConversion() {
        List<String> content = Arrays.asList("item1", "item2", "item3");
        Page<String> page = new PageImpl<>(content, PageRequest.of(0, 10), 25L);

        PageResponse<String> response = PageResponse.fromPage(page);

        assertEquals(content, response.getItems());
        assertEquals(25L, response.getTotal());
        assertEquals(1, response.getPage());
        assertEquals(10, response.getSize());
        assertEquals(3, response.getTotalPages());
    }

    @Test
    @DisplayName("fromPage(Page, List) 使用转换后的items列表")
    void testFromPageWithConvertedItems() {
        List<String> originalItems = Arrays.asList("1", "2", "3");
        List<Integer> convertedItems = Arrays.asList(100, 200, 300);
        Page<String> page = new PageImpl<>(originalItems, PageRequest.of(0, 10), 25L);

        PageResponse<Integer> response = PageResponse.fromPage(page, convertedItems);

        assertEquals(convertedItems, response.getItems());
        assertEquals(25L, response.getTotal());
        assertEquals(1, response.getPage());
        assertEquals(10, response.getSize());
        assertEquals(3, response.getTotalPages());
    }

    @Test
    @DisplayName("Spring Data Page(pageNumber=0) 转换为 PageResponse.page=1")
    void testPageIsOneBased() {
        List<String> content = Collections.singletonList("item");
        Page<String> page0 = new PageImpl<>(content, PageRequest.of(0, 10), 15L);
        Page<String> page1 = new PageImpl<>(content, PageRequest.of(1, 10), 15L);

        PageResponse<String> response0 = PageResponse.fromPage(page0);
        PageResponse<String> response1 = PageResponse.fromPage(page1);

        assertEquals(1, response0.getPage());
        assertEquals(2, response1.getPage());
    }

    @Test
    @DisplayName("空页处理")
    void testEmptyPage() {
        Page<String> emptyPage = new PageImpl<>(Collections.emptyList(), PageRequest.of(0, 10), 0L);

        PageResponse<String> response = PageResponse.fromPage(emptyPage);

        assertTrue(response.getItems().isEmpty());
        assertEquals(0L, response.getTotal());
        assertEquals(1, response.getPage());
        assertEquals(10, response.getSize());
        assertEquals(0, response.getTotalPages());
    }

    @Test
    @DisplayName("totalPages JSON序列化为total_pages")
    void testTotalPagesJsonSerialization() throws Exception {
        List<String> content = Arrays.asList("a", "b");
        Page<String> page = new PageImpl<>(content, PageRequest.of(0, 10), 25L);
        PageResponse<String> response = PageResponse.fromPage(page);

        String json = objectMapper.writeValueAsString(response);

        assertTrue(json.contains("\"total_pages\""));
        assertFalse(json.contains("\"totalPages\""));
    }

    @Test
    @DisplayName("Builder模式正常工作")
    void testBuilderPattern() {
        PageResponse<String> response = PageResponse.<String>builder()
                .items(Arrays.asList("a", "b"))
                .total(100L)
                .page(3)
                .size(20)
                .totalPages(5)
                .build();

        assertEquals(2, response.getItems().size());
        assertEquals(100L, response.getTotal());
        assertEquals(3, response.getPage());
        assertEquals(20, response.getSize());
        assertEquals(5, response.getTotalPages());
    }
}
