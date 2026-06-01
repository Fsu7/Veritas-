package com.literatureassistant.service;

import com.literatureassistant.dto.common.PageResponse;
import com.literatureassistant.dto.response.PaperDetailResponse;
import com.literatureassistant.dto.response.PaperResponse;
import com.literatureassistant.entity.Paper;
import com.literatureassistant.exception.ResourceNotFoundException;
import com.literatureassistant.mapper.PaperMapper;
import com.literatureassistant.repository.PaperRepository;
import org.junit.jupiter.api.BeforeEach;
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
import org.springframework.data.domain.Sort;

import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class PaperServiceTest {

    @InjectMocks
    private PaperService paperService;

    @Mock
    private PaperRepository paperRepository;

    @Mock
    private PaperMapper paperMapper;

    private Paper samplePaper;

    @BeforeEach
    void setUp() {
        samplePaper = Paper.builder()
                .id(1L)
                .paperId("arxiv_2024_001")
                .title("Multi-Agent Systems: A Survey")
                .authors("[\"Wang, L.\"]")
                .keywords("[\"multi-agent\"]")
                .year(2024)
                .venue("AAAI")
                .citationCount(1200)
                .build();
    }

    @Test
    @DisplayName("listPapers - 正常返回分页结果，page从1开始转换为0")
    void listPapers_normal_returnsPageResponse() {
        Pageable expectedPageable = PageRequest.of(0, 10, Sort.by(Sort.Direction.DESC, "createdAt"));
        Page<Paper> mockPage = new PageImpl<>(List.of(samplePaper), expectedPageable, 1);
        PaperResponse mockResponse = PaperResponse.builder().paperId("arxiv_2024_001").build();

        when(paperRepository.findAll(any(Pageable.class))).thenReturn(mockPage);
        when(paperMapper.toResponse(samplePaper)).thenReturn(mockResponse);

        PageResponse<PaperResponse> result = paperService.listPapers(1, 10);

        assertThat(result).isNotNull();
        assertThat(result.getItems()).hasSize(1);
        assertThat(result.getItems().get(0).getPaperId()).isEqualTo("arxiv_2024_001");
        assertThat(result.getTotal()).isEqualTo(1);
        assertThat(result.getPage()).isEqualTo(1);
        assertThat(result.getSize()).isEqualTo(10);

        ArgumentCaptor<Pageable> pageableCaptor = ArgumentCaptor.forClass(Pageable.class);
        verify(paperRepository).findAll(pageableCaptor.capture());
        assertThat(pageableCaptor.getValue().getPageNumber()).isEqualTo(0);
        assertThat(pageableCaptor.getValue().getPageSize()).isEqualTo(10);
    }

    @Test
    @DisplayName("listPapers - page<1时修正为1")
    void listPapers_pageLessThanOne_clampsToOne() {
        when(paperRepository.findAll(any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(), PageRequest.of(0, 10), 0));

        PageResponse<PaperResponse> result = paperService.listPapers(0, 10);

        ArgumentCaptor<Pageable> pageableCaptor = ArgumentCaptor.forClass(Pageable.class);
        verify(paperRepository).findAll(pageableCaptor.capture());
        assertThat(pageableCaptor.getValue().getPageNumber()).isEqualTo(0);
        assertThat(result.getPage()).isEqualTo(1);
    }

    @Test
    @DisplayName("listPapers - size<1时修正为10")
    void listPapers_sizeLessThanOne_clampsToTen() {
        when(paperRepository.findAll(any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(), PageRequest.of(0, 10), 0));

        paperService.listPapers(1, 0);

        ArgumentCaptor<Pageable> pageableCaptor = ArgumentCaptor.forClass(Pageable.class);
        verify(paperRepository).findAll(pageableCaptor.capture());
        assertThat(pageableCaptor.getValue().getPageSize()).isEqualTo(10);
    }

    @Test
    @DisplayName("listPapers - size>100时限制为100")
    void listPapers_sizeGreaterThanHundred_clampsToHundred() {
        when(paperRepository.findAll(any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(), PageRequest.of(0, 100), 0));

        paperService.listPapers(1, 200);

        ArgumentCaptor<Pageable> pageableCaptor = ArgumentCaptor.forClass(Pageable.class);
        verify(paperRepository).findAll(pageableCaptor.capture());
        assertThat(pageableCaptor.getValue().getPageSize()).isEqualTo(100);
    }

    @Test
    @DisplayName("getPaperDetail - 正常返回PaperDetailResponse")
    void getPaperDetail_normal_returnsDetail() {
        PaperDetailResponse expected = PaperDetailResponse.builder()
                .paperId("arxiv_2024_001")
                .title("Test")
                .build();
        when(paperRepository.findByPaperId("arxiv_2024_001")).thenReturn(Optional.of(samplePaper));
        when(paperMapper.toDetailResponse(samplePaper)).thenReturn(expected);

        PaperDetailResponse result = paperService.getPaperDetail("arxiv_2024_001");

        assertThat(result).isEqualTo(expected);
        verify(paperRepository, times(1)).findByPaperId("arxiv_2024_001");
    }

    @Test
    @DisplayName("getPaperDetail - 论文不存在抛ResourceNotFoundException")
    void getPaperDetail_notFound_throwsResourceNotFound() {
        when(paperRepository.findByPaperId("nonexistent")).thenReturn(Optional.empty());

        assertThatThrownBy(() -> paperService.getPaperDetail("nonexistent"))
                .isInstanceOf(ResourceNotFoundException.class)
                .hasMessageContaining("Paper")
                .hasMessageContaining("nonexistent");

        verify(paperMapper, never()).toDetailResponse(any());
    }
}
