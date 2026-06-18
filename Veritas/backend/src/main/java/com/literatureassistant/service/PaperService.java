package com.literatureassistant.service;

import com.literatureassistant.dto.common.PageResponse;
import com.literatureassistant.dto.response.PaperDetailResponse;
import com.literatureassistant.dto.response.PaperResponse;
import com.literatureassistant.entity.Paper;
import com.literatureassistant.exception.BusinessException;
import com.literatureassistant.exception.ResourceNotFoundException;
import com.literatureassistant.mapper.PaperMapper;
import com.literatureassistant.repository.PaperRepository;
import com.literatureassistant.util.RedisKeyUtil;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Set;

@Service
@Slf4j
@RequiredArgsConstructor
public class PaperService {

    private static final int DEFAULT_PAGE = 1;
    private static final int DEFAULT_SIZE = 10;
    private static final int MAX_SIZE = 100;

    private static final String SORT_RELEVANCE = "relevance";
    private static final String SORT_YEAR = "year";
    private static final String SORT_CITATIONS = "citations";
    private static final String SORT_TITLE = "title";
    private static final Set<String> ALLOWED_SORTS = Set.of(SORT_RELEVANCE, SORT_YEAR, SORT_CITATIONS, SORT_TITLE);

    /**
     * task35: 排序方向白名单（统一小写）。非法值 fallback desc。
     */
    private static final Set<String> ALLOWED_SORT_DIRECTIONS = Set.of("asc", "desc");

    private final PaperRepository paperRepository;
    private final PaperMapper paperMapper;

    @Cacheable(value = "paperList",
            key = "T(com.literatureassistant.util.RedisKeyUtil).paperListKey(#page, #size)",
            sync = true)  // U-005 修复: 防止高并发查询同一 key 时缓存击穿
    @Transactional(readOnly = true)
    public PageResponse<PaperResponse> listPapers(int page, int size) {
        int safePage = page < 1 ? DEFAULT_PAGE : page;
        int safeSize = size < 1 ? DEFAULT_SIZE : Math.min(size, MAX_SIZE);

        Pageable pageable = PageRequest.of(safePage - 1, safeSize,
                Sort.by(Sort.Direction.DESC, "createdAt"));

        Page<Paper> paperPage = paperRepository.findAll(pageable);
        List<PaperResponse> items = paperPage.getContent().stream()
                .map(paperMapper::toResponse)
                .toList();

        log.info("Paper list: page={}, size={}, total={}", safePage, safeSize, paperPage.getTotalElements());

        return PageResponse.fromPage(paperPage, items);
    }

    @Cacheable(value = "paperDetail", key = "#paperId", unless = "#result == null",
            sync = true)  // U-005 修复: 防止高并发查询同一 key 时缓存击穿
    @Transactional(readOnly = true)
    public PaperDetailResponse getPaperDetail(String paperId) {
        Paper paper = paperRepository.findByPaperId(paperId)
                .orElseThrow(() -> new ResourceNotFoundException("Paper", paperId));

        log.info("Paper detail fetched from DB: paperId={}", paperId);

        return paperMapper.toDetailResponse(paper);
    }

    /**
     * task35: 扩展搜索方法签名，新增 author/keywords 过滤 + sortDirection 排序方向。
     */
    @Cacheable(value = "paperSearch",
            key = "T(com.literatureassistant.util.RedisKeyUtil).paperSearchKey(#q, #yearFrom, #yearTo, #venue, #author, #keywords, #sort, #sortDirection, #page, #size)",
            sync = true)  // U-005 修复: 防止高并发查询同一 key 时缓存击穿
    @Transactional(readOnly = true)
    public PageResponse<PaperResponse> searchPapers(String q, Integer yearFrom, Integer yearTo,
                                                    String venue, String author, String keywords,
                                                    String sort, String sortDirection, int page, int size) {
        if (q == null || q.trim().isEmpty()) {
            // U-002 修复: 使用 BusinessException 替代 IllegalArgumentException，统一异常体系
            throw new BusinessException(400, "搜索关键词不能为空", "INVALID_PARAMETER");
        }

        if (yearFrom != null && yearTo != null && yearFrom > yearTo) {
            throw new BusinessException(400, "yearFrom不能大于yearTo", "INVALID_PARAMETER");
        }

        String safeSort = sort;
        if (safeSort == null || !ALLOWED_SORTS.contains(safeSort)) {
            log.warn("Invalid sort value, fallback to 'relevance': inputSort={}", sort);
            safeSort = SORT_RELEVANCE;
        }

        // task35: sortDirection 白名单校验（统一小写，非法 fallback desc）
        String safeSortDirection = "desc";
        if (sortDirection != null) {
            String lower = sortDirection.toLowerCase();
            if (ALLOWED_SORT_DIRECTIONS.contains(lower)) {
                safeSortDirection = lower;
            } else {
                log.warn("Invalid sortDirection value, fallback to 'desc': inputSortDirection={}", sortDirection);
            }
        }

        int safePage = page < 1 ? DEFAULT_PAGE : page;
        int safeSize = size < 1 ? DEFAULT_SIZE : Math.min(size, MAX_SIZE);

        Pageable pageable = PageRequest.of(safePage - 1, safeSize);

        Page<Paper> paperPage = paperRepository.searchByKeyword(
                q.trim(), yearFrom, yearTo, venue, author, keywords,
                safeSort, safeSortDirection, pageable);

        List<PaperResponse> items = paperPage.getContent().stream()
                .map(paperMapper::toResponse)
                .toList();

        log.info("Paper search: q={}, sort={}, sortDirection={}, page={}, size={}, total={}",
                q, safeSort, safeSortDirection, safePage, safeSize, paperPage.getTotalElements());

        return PageResponse.fromPage(paperPage, items);
    }
}
