package com.literatureassistant.controller;

import com.literatureassistant.dto.common.ApiResponse;
import com.literatureassistant.dto.common.PageResponse;
import com.literatureassistant.dto.response.PaperDetailResponse;
import com.literatureassistant.dto.response.PaperResponse;
import com.literatureassistant.service.PaperService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/papers")
@RequiredArgsConstructor
@Slf4j
public class PaperController {

    private final PaperService paperService;

    @GetMapping
    public ApiResponse<PageResponse<PaperResponse>> listPapers(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size) {
        PageResponse<PaperResponse> response = paperService.listPapers(page, size);
        return ApiResponse.success(response);
    }

    @GetMapping("/search")
    public ApiResponse<PageResponse<PaperResponse>> searchPapers(
            @RequestParam String q,
            @RequestParam(required = false) Integer yearFrom,
            @RequestParam(required = false) Integer yearTo,
            @RequestParam(required = false) String venue,
            @RequestParam(defaultValue = "relevance") String sort,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size) {
        PageResponse<PaperResponse> response = paperService.searchPapers(
                q, yearFrom, yearTo, venue, sort, page, size);
        return ApiResponse.success(response);
    }

    @GetMapping("/{paperId}")
    public ApiResponse<PaperDetailResponse> getPaperDetail(@PathVariable String paperId) {
        PaperDetailResponse response = paperService.getPaperDetail(paperId);
        return ApiResponse.success(response);
    }
}
