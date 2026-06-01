package com.literatureassistant.service;

import com.literatureassistant.dto.common.PageResponse;
import com.literatureassistant.dto.response.PaperResponse;
import com.literatureassistant.entity.Paper;
import com.literatureassistant.exception.BusinessException;
import com.literatureassistant.mapper.PaperMapper;
import com.literatureassistant.repository.PaperRepository;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class PaperServiceSearchTest {

    @InjectMocks
    private PaperService paperService;

    @Mock
    private PaperRepository paperRepository;

    @Mock
    private PaperMapper paperMapper;

    @Test
    @DisplayName("searchPapers - 正常搜索返回PageResponse")
    void searchPapers_normal_returnsPageResponse() {
        Paper paper = Paper.builder().paperId("p1").title("Test").build();
        PaperResponse paperResponse = PaperResponse.builder().paperId("p1").build();
        Page<Paper> mockPage = new PageImpl<>(List.of(paper), PageRequest.of(0, 10), 1);

        when(paperRepository.searchByKeyword(
                anyString(), any(), any(), any(), anyString(), any(Pageable.class)))
                .thenReturn(mockPage);
        when(paperMapper.toResponse(paper)).thenReturn(paperResponse);

        PageResponse<PaperResponse> result = paperService.searchPapers(
                "agent", null, null, null, "relevance", 1, 10);

        assertThat(result).isNotNull();
        assertThat(result.getItems()).hasSize(1);
        assertThat(result.getItems().get(0).getPaperId()).isEqualTo("p1");
        assertThat(result.getTotal()).isEqualTo(1);
    }

    @Test
    @DisplayName("searchPapers - q为null抛IllegalArgumentException")
    void searchPapers_nullQ_throwsIllegalArgument() {
        assertThatThrownBy(() -> paperService.searchPapers(
                null, null, null, null, "relevance", 1, 10))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("搜索关键词不能为空");

        verify(paperRepository, never()).searchByKeyword(
                anyString(), any(), any(), any(), anyString(), any(Pageable.class));
    }

    @Test
    @DisplayName("searchPapers - q为空白字符串抛IllegalArgumentException")
    void searchPapers_blankQ_throwsIllegalArgument() {
        assertThatThrownBy(() -> paperService.searchPapers(
                "   ", null, null, null, "relevance", 1, 10))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("搜索关键词不能为空");

        verify(paperRepository, never()).searchByKeyword(
                anyString(), any(), any(), any(), anyString(), any(Pageable.class));
    }

    @Test
    @DisplayName("searchPapers - yearFrom>yearTo抛BusinessException")
    void searchPapers_yearFromGreaterThanYearTo_throwsBusinessException() {
        assertThatThrownBy(() -> paperService.searchPapers(
                "agent", 2024, 2020, null, "relevance", 1, 10))
                .isInstanceOf(BusinessException.class)
                .hasMessageContaining("yearFrom不能大于yearTo");

        verify(paperRepository, never()).searchByKeyword(
                anyString(), any(), any(), any(), anyString(), any(Pageable.class));
    }

    @Test
    @DisplayName("searchPapers - sort非法值降级为relevance")
    void searchPapers_invalidSort_fallsBackToRelevance() {
        Page<Paper> mockPage = new PageImpl<>(List.of(), PageRequest.of(0, 10), 0);
        when(paperRepository.searchByKeyword(
                anyString(), any(), any(), any(), anyString(), any(Pageable.class)))
                .thenReturn(mockPage);

        paperService.searchPapers("agent", null, null, null, "invalid_sort", 1, 10);

        ArgumentCaptor<String> sortCaptor = ArgumentCaptor.forClass(String.class);
        verify(paperRepository).searchByKeyword(
                anyString(), any(), any(), any(), sortCaptor.capture(), any(Pageable.class));
        assertThat(sortCaptor.getValue()).isEqualTo("relevance");
    }

    @Test
    @DisplayName("searchPapers - page<1修正为1")
    void searchPapers_pageLessThanOne_clampsToOne() {
        Page<Paper> mockPage = new PageImpl<>(List.of(), PageRequest.of(0, 10), 0);
        when(paperRepository.searchByKeyword(
                anyString(), any(), any(), any(), anyString(), any(Pageable.class)))
                .thenReturn(mockPage);

        paperService.searchPapers("agent", null, null, null, "relevance", 0, 10);

        ArgumentCaptor<Pageable> pageableCaptor = ArgumentCaptor.forClass(Pageable.class);
        verify(paperRepository).searchByKeyword(
                anyString(), any(), any(), any(), anyString(), pageableCaptor.capture());
        assertThat(pageableCaptor.getValue().getPageNumber()).isEqualTo(0);
    }

    @Test
    @DisplayName("searchPapers - size>100限制为100")
    void searchPapers_sizeGreaterThanHundred_clampsToHundred() {
        Page<Paper> mockPage = new PageImpl<>(List.of(), PageRequest.of(0, 100), 0);
        when(paperRepository.searchByKeyword(
                anyString(), any(), any(), any(), anyString(), any(Pageable.class)))
                .thenReturn(mockPage);

        paperService.searchPapers("agent", null, null, null, "relevance", 1, 200);

        ArgumentCaptor<Pageable> pageableCaptor = ArgumentCaptor.forClass(Pageable.class);
        verify(paperRepository).searchByKeyword(
                anyString(), any(), any(), any(), anyString(), pageableCaptor.capture());
        assertThat(pageableCaptor.getValue().getPageSize()).isEqualTo(100);
    }

    @Test
    @DisplayName("searchPapers - 无结果返回空PageResponse而非null")
    void searchPapers_noResults_returnsEmptyPage() {
        Page<Paper> emptyPage = new PageImpl<>(List.of(), PageRequest.of(0, 10), 0);
        when(paperRepository.searchByKeyword(
                anyString(), any(), any(), any(), anyString(), any(Pageable.class)))
                .thenReturn(emptyPage);

        PageResponse<PaperResponse> result = paperService.searchPapers(
                "nonexistent_keyword_xyz", null, null, null, "relevance", 1, 10);

        assertThat(result).isNotNull();
        assertThat(result.getItems()).isEmpty();
        assertThat(result.getTotal()).isEqualTo(0);
        assertThat(result.getTotalPages()).isEqualTo(0);
    }

    @Test
    @DisplayName("searchPapers - 正确调用paperMapper.toResponse批量转换")
    void searchPapers_invokesMapperToResponse() {
        Paper p1 = Paper.builder().paperId("p1").build();
        Paper p2 = Paper.builder().paperId("p2").build();
        Page<Paper> mockPage = new PageImpl<>(List.of(p1, p2), PageRequest.of(0, 10), 2);
        when(paperRepository.searchByKeyword(
                anyString(), any(), any(), any(), anyString(), any(Pageable.class)))
                .thenReturn(mockPage);
        when(paperMapper.toResponse(any(Paper.class)))
                .thenReturn(PaperResponse.builder().build());

        paperService.searchPapers("agent", null, null, null, "relevance", 1, 10);

        verify(paperMapper, times(2)).toResponse(any(Paper.class));
    }
}
