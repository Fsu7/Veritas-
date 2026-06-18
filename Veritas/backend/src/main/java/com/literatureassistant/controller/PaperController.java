package com.literatureassistant.controller;

import com.literatureassistant.dto.common.ApiResponse;
import com.literatureassistant.dto.common.PageResponse;
import com.literatureassistant.dto.response.FavoriteResponse;
import com.literatureassistant.dto.response.PaperDetailResponse;
import com.literatureassistant.dto.response.PaperResponse;
import com.literatureassistant.exception.AuthenticationException;
import com.literatureassistant.service.FavoriteService;
import com.literatureassistant.service.PaperService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/papers")
@RequiredArgsConstructor
@Slf4j
public class PaperController {

    private final PaperService paperService;
    private final FavoriteService favoriteService;

    @GetMapping
    public ApiResponse<PageResponse<PaperResponse>> listPapers(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size) {
        PageResponse<PaperResponse> response = paperService.listPapers(page, size);
        return ApiResponse.success(response);
    }

    /**
     * task35: 扩展搜索端点，新增 author/keywords 过滤 + sortDirection 排序方向。
     */
    @GetMapping("/search")
    public ApiResponse<PageResponse<PaperResponse>> searchPapers(
            @RequestParam String q,
            @RequestParam(required = false) Integer yearFrom,
            @RequestParam(required = false) Integer yearTo,
            @RequestParam(required = false) String venue,
            @RequestParam(required = false) String author,
            @RequestParam(required = false) String keywords,
            @RequestParam(defaultValue = "relevance") String sort,
            @RequestParam(defaultValue = "desc") String sortDirection,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size) {
        PageResponse<PaperResponse> response = paperService.searchPapers(
                q, yearFrom, yearTo, venue, author, keywords,
                sort, sortDirection, page, size);
        return ApiResponse.success(response);
    }

    @GetMapping("/{paperId}")
    public ApiResponse<PaperDetailResponse> getPaperDetail(@PathVariable String paperId) {
        PaperDetailResponse response = paperService.getPaperDetail(paperId);
        return ApiResponse.success(response);
    }

    // ==================== task36: 收藏端点 ====================

    /**
     * task36: 收藏论文（幂等）。
     * <p>POST /api/papers/{paperId}/favorite
     */
    @PostMapping("/{paperId}/favorite")
    public ApiResponse<FavoriteResponse> addFavorite(
            @PathVariable String paperId,
            @AuthenticationPrincipal String userId) {
        String currentUserId = validateUserId(userId);
        log.info("REST addFavorite: userId={}, paperId={}", currentUserId, paperId);
        FavoriteResponse response = favoriteService.addFavorite(currentUserId, paperId);
        return ApiResponse.success(response);
    }

    /**
     * task36: 取消收藏（幂等）。
     * <p>DELETE /api/papers/{paperId}/favorite
     */
    @DeleteMapping("/{paperId}/favorite")
    public ApiResponse<Void> removeFavorite(
            @PathVariable String paperId,
            @AuthenticationPrincipal String userId) {
        String currentUserId = validateUserId(userId);
        log.info("REST removeFavorite: userId={}, paperId={}", currentUserId, paperId);
        favoriteService.removeFavorite(currentUserId, paperId);
        return ApiResponse.success(null);
    }

    /**
     * task36: 收藏列表分页查询。
     * <p>GET /api/papers/favorites
     */
    @GetMapping("/favorites")
    public ApiResponse<PageResponse<FavoriteResponse>> listFavorites(
            @AuthenticationPrincipal String userId,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size) {
        String currentUserId = validateUserId(userId);
        log.info("REST listFavorites: userId={}, page={}, size={}", currentUserId, page, size);
        PageResponse<FavoriteResponse> response = favoriteService.listFavorites(currentUserId, page, size);
        return ApiResponse.success(response);
    }

    /**
     * task36: 校验 JWT 鉴权，提取当前用户 ID。
     * <p>userId 必须来自 @AuthenticationPrincipal，禁止前端传入 userId 参数。
     */
    private String validateUserId(String userId) {
        String currentUserId = userId != null ? userId : extractCurrentUserId();
        if (currentUserId == null || currentUserId.isBlank()) {
            throw new AuthenticationException("未认证，请先登录");
        }
        return currentUserId;
    }

    private String extractCurrentUserId() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication != null && authentication.getPrincipal() instanceof String principal) {
            return principal;
        }
        return null;
    }
}
