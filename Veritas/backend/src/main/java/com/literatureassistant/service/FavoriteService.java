package com.literatureassistant.service;

import com.literatureassistant.cache.CacheEvictionHelper;
import com.literatureassistant.dto.common.PageResponse;
import com.literatureassistant.dto.response.FavoriteResponse;
import com.literatureassistant.entity.Paper;
import com.literatureassistant.entity.PaperFavorite;
import com.literatureassistant.exception.ResourceNotFoundException;
import com.literatureassistant.mapper.FavoriteMapper;
import com.literatureassistant.repository.PaperFavoriteRepository;
import com.literatureassistant.repository.PaperRepository;
import com.literatureassistant.util.RedisKeyUtil;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * 论文收藏服务。
 * <p>提供收藏/取消收藏/收藏列表/收藏状态查询功能。
 * <p>缓存策略：listFavorites 使用 @Cacheable(favoriteList, TTL=10min)；
 * addFavorite/removeFavorite 使用 CacheEvictionHelper 按用户前缀精准失效（P2-1）。
 * <p>幂等性：重复收藏/取消收藏均返回成功，不抛异常。
 * <p>数据隔离：所有操作强制 WHERE user_id = currentUserId。
 * <p>task36 新建。
 *
 * @author XH-202630 Literature Assistant
 * @since 0.5
 */
@Service
@Slf4j
@RequiredArgsConstructor
public class FavoriteService {

    private static final int DEFAULT_PAGE = 1;
    private static final int DEFAULT_SIZE = 10;
    private static final int MAX_SIZE = 100;

    private final PaperFavoriteRepository favoriteRepository;
    private final PaperRepository paperRepository;
    private final FavoriteMapper favoriteMapper;
    private final CacheEvictionHelper cacheEvictionHelper;

    /**
     * 收藏论文（幂等）。
     * <p>1) 校验 paperId 存在；2) 若已收藏直接返回已有记录；3) 否则新建收藏。
     *
     * @param userId  当前用户 ID（来自 JWT）
     * @param paperId 论文 ID
     * @return 收藏响应 DTO（含论文详情）
     */
    @Transactional
    // P2-1: 移除 @CacheEvict(allEntries=true)，改用 CacheEvictionHelper 按用户前缀精准失效。
    // 原方案 allEntries=true 会清空整个 favoriteList 缓存空间，影响其他用户的收藏列表缓存。
    // 新方案在事务提交后按 "favoriteList::user:favorites:{userId}:*" 前缀精准删除当前用户的分页缓存。
    public FavoriteResponse addFavorite(String userId, String paperId) {
        // 1) 校验 paperId 存在
        Paper paper = paperRepository.findByPaperId(paperId)
                .orElseThrow(() -> new ResourceNotFoundException("Paper", paperId));

        // 2) 幂等：已存在直接返回已有记录
        Optional<PaperFavorite> existing = favoriteRepository.findByUserIdAndPaperId(userId, paperId);
        if (existing.isPresent()) {
            log.info("Favorite already exists (idempotent): userId={}, paperId={}", userId, paperId);
            // P2-1: 幂等场景也触发缓存失效，保证一致性（与原 @CacheEvict 行为一致）
            cacheEvictionHelper.evictByPatternAfterCommit(
                    "favoriteList::user:favorites:" + userId + ":*");
            return favoriteMapper.toResponse(existing.get(), paper);
        }

        // 3) 新建收藏
        PaperFavorite favorite = PaperFavorite.builder()
                .userId(userId)
                .paperId(paperId)
                .build();
        PaperFavorite saved = favoriteRepository.save(favorite);

        // P2-1: 事务提交后精准失效该用户的收藏列表缓存（写后删，避免脏读回填）
        cacheEvictionHelper.evictByPatternAfterCommit(
                "favoriteList::user:favorites:" + userId + ":*");

        log.info("Favorite added: userId={}, paperId={}, favoriteId={}", userId, paperId, saved.getId());
        return favoriteMapper.toResponse(saved, paper);
    }

    /**
     * 取消收藏（幂等）。
     * <p>不存在时直接返回，不抛异常。
     *
     * @param userId  当前用户 ID（来自 JWT）
     * @param paperId 论文 ID
     */
    @Transactional
    // P2-1: 移除 @CacheEvict(allEntries=true)，改用 CacheEvictionHelper 按用户前缀精准失效。
    public void removeFavorite(String userId, String paperId) {
        if (!favoriteRepository.existsByUserIdAndPaperId(userId, paperId)) {
            log.info("Favorite not exists (idempotent remove): userId={}, paperId={}", userId, paperId);
            // P2-1: 幂等场景也触发缓存失效，保证一致性（与原 @CacheEvict 行为一致）
            cacheEvictionHelper.evictByPatternAfterCommit(
                    "favoriteList::user:favorites:" + userId + ":*");
            return;
        }
        favoriteRepository.deleteByUserIdAndPaperId(userId, paperId);

        // P2-1: 事务提交后精准失效该用户的收藏列表缓存
        cacheEvictionHelper.evictByPatternAfterCommit(
                "favoriteList::user:favorites:" + userId + ":*");

        log.info("Favorite removed: userId={}, paperId={}", userId, paperId);
    }

    /**
     * 分页查询收藏列表（含论文详情）。
     * <p>使用 @Cacheable(favoriteList, TTL=10min)，相同 userId+page+size 第二次查询命中缓存。
     *
     * @param userId 当前用户 ID（来自 JWT）
     * @param page   页码（1-based）
     * @param size   每页大小
     * @return 分页收藏响应
     */
    // 修复 B-002: Key 必须包含 page/size，避免不同分页查询命中同一缓存
    @Cacheable(value = "favoriteList",
            key = "T(com.literatureassistant.util.RedisKeyUtil).favoriteListKey(#userId, #page, #size)",
            unless = "#result == null")
    @Transactional(readOnly = true)
    public PageResponse<FavoriteResponse> listFavorites(String userId, int page, int size) {
        int safePage = page < 1 ? DEFAULT_PAGE : page;
        int safeSize = size < 1 ? DEFAULT_SIZE : Math.min(size, MAX_SIZE);
        Pageable pageable = PageRequest.of(safePage - 1, safeSize);

        Page<PaperFavorite> favPage = favoriteRepository.findByUserIdOrderByCreatedAtDesc(userId, pageable);

        // 批量查询论文详情（避免 N+1）
        List<String> paperIds = favPage.getContent().stream()
                .map(PaperFavorite::getPaperId)
                .toList();
        Map<String, Paper> paperMap = paperRepository.findByPaperIdIn(paperIds).stream()
                .collect(Collectors.toMap(Paper::getPaperId, Function.identity()));

        List<FavoriteResponse> items = favPage.getContent().stream()
                .map(fav -> favoriteMapper.toResponse(fav, paperMap.get(fav.getPaperId())))
                .toList();

        log.info("Favorite list: userId={}, page={}, size={}, total={}",
                userId, safePage, safeSize, favPage.getTotalElements());

        return PageResponse.fromPage(favPage, items);
    }

    /**
     * 查询收藏状态。
     *
     * @param userId  当前用户 ID（来自 JWT）
     * @param paperId 论文 ID
     * @return true=已收藏，false=未收藏
     */
    @Transactional(readOnly = true)
    public boolean isFavorite(String userId, String paperId) {
        return favoriteRepository.existsByUserIdAndPaperId(userId, paperId);
    }
}
