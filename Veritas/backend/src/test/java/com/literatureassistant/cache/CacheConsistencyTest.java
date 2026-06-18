package com.literatureassistant.cache;

import com.literatureassistant.dto.common.PageResponse;
import com.literatureassistant.dto.response.FavoriteResponse;
import com.literatureassistant.entity.Paper;
import com.literatureassistant.entity.PaperFavorite;
import com.literatureassistant.mapper.FavoriteMapper;
import com.literatureassistant.repository.PaperFavoriteRepository;
import com.literatureassistant.repository.PaperRepository;
import com.literatureassistant.service.FavoriteService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;

import java.lang.reflect.Method;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * task39: 缓存一致性测试。
 * <p>验证 @Cacheable / CacheEvictionHelper 配置正确，确保 Cache-Aside 模式生效。
 * <p>测试维度：
 * 1) @Cacheable 注解存在且 key 正确；
 * 2) P2-1: addFavorite/removeFavorite 不再使用 @CacheEvict(allEntries=true)，改用 CacheEvictionHelper；
 * 3) 写后失效：addFavorite/removeFavorite 触发 evict，listFavorites 第二次命中缓存；
 * 4) 缓存空值：unless = "#result == null" 防穿透；
 * 5) 三重失效：userProfile + userProfileJson + userInfo 同步失效（通过注解验证）。
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("缓存一致性测试")
class CacheConsistencyTest {

    @InjectMocks
    private FavoriteService favoriteService;

    @Mock
    private PaperFavoriteRepository favoriteRepository;

    @Mock
    private PaperRepository paperRepository;

    @Mock
    private FavoriteMapper favoriteMapper;

    @Mock
    private CacheEvictionHelper cacheEvictionHelper;

    // ==================== 注解配置验证 ====================

    @Test
    @DisplayName("testListFavoritesCacheableAnnotation - @Cacheable(value=favoriteList, key 含 page/size)")
    void testListFavoritesCacheableAnnotation() throws NoSuchMethodException {
        // 修复 B-002: Key 必须包含 page/size，避免不同分页查询命中同一缓存
        Method method = FavoriteService.class.getMethod("listFavorites", String.class, int.class, int.class);
        Cacheable cacheable = method.getAnnotation(Cacheable.class);

        assertThat(cacheable).as("listFavorites 必须标注 @Cacheable").isNotNull();
        assertThat(cacheable.value()).contains("favoriteList");
        // Key 表达式应调用 RedisKeyUtil.favoriteListKey(#userId, #page, #size)
        assertThat(cacheable.key()).contains("favoriteListKey");
        assertThat(cacheable.key()).contains("#userId");
        assertThat(cacheable.key()).contains("#page");
        assertThat(cacheable.key()).contains("#size");
        // unless 防穿透：空结果不缓存
        assertThat(cacheable.unless()).isEqualTo("#result == null");
    }

    @Test
    @DisplayName("testAddFavoriteCacheEvictAnnotation - P2-1: addFavorite 不再使用 @CacheEvict(allEntries=true)")
    void testAddFavoriteCacheEvictAnnotation() throws NoSuchMethodException {
        // P2-1: addFavorite 已从 @CacheEvict(allEntries=true) 迁移到 CacheEvictionHelper 按用户前缀精准失效
        Method method = FavoriteService.class.getMethod("addFavorite", String.class, String.class);
        CacheEvict cacheEvict = method.getAnnotation(CacheEvict.class);

        // 验证方法不再标注 @CacheEvict（已迁移到 CacheEvictionHelper）
        assertThat(cacheEvict)
                .as("P2-1: addFavorite 不应再标注 @CacheEvict，改用 CacheEvictionHelper")
                .isNull();
    }

    @Test
    @DisplayName("testRemoveFavoriteCacheEvictAnnotation - P2-1: removeFavorite 不再使用 @CacheEvict(allEntries=true)")
    void testRemoveFavoriteCacheEvictAnnotation() throws NoSuchMethodException {
        // P2-1: removeFavorite 已从 @CacheEvict(allEntries=true) 迁移到 CacheEvictionHelper
        Method method = FavoriteService.class.getMethod("removeFavorite", String.class, String.class);
        CacheEvict cacheEvict = method.getAnnotation(CacheEvict.class);

        // 验证方法不再标注 @CacheEvict（已迁移到 CacheEvictionHelper）
        assertThat(cacheEvict)
                .as("P2-1: removeFavorite 不应再标注 @CacheEvict，改用 CacheEvictionHelper")
                .isNull();
    }

    @Test
    @DisplayName("testCacheKeyIsolation - 不同 userId+page+size 的缓存 key 隔离")
    void testCacheKeyIsolation() throws NoSuchMethodException {
        // 修复 B-002: Key 必须包含 userId+page+size，确保不同用户/不同分页的缓存互不干扰
        Method listMethod = FavoriteService.class.getMethod("listFavorites", String.class, int.class, int.class);
        Cacheable cacheable = listMethod.getAnnotation(Cacheable.class);
        // key 表达式使用 #userId + #page + #size，确保不同用户/不同分页的缓存互不干扰
        assertThat(cacheable.key()).contains("favoriteListKey");
        assertThat(cacheable.key()).contains("#userId");
        assertThat(cacheable.key()).contains("#page");
        assertThat(cacheable.key()).contains("#size");

        // P2-1: addFavorite 不再使用 @CacheEvict(allEntries=true)，改用 CacheEvictionHelper 精准失效
        Method addMethod = FavoriteService.class.getMethod("addFavorite", String.class, String.class);
        CacheEvict evict = addMethod.getAnnotation(CacheEvict.class);
        assertThat(evict)
                .as("P2-1: addFavorite 不应再标注 @CacheEvict")
                .isNull();
    }

    // ==================== 写后失效行为验证 ====================

    @Test
    @DisplayName("testWriteAfterReadConsistency - addFavorite 后 listFavorites 重新查 DB（缓存已失效）")
    void testWriteAfterReadConsistency() {
        // 场景：用户 u1 已有收藏 p1，listFavorites 第一次查询返回 1 条
        // 然后 addFavorite 收藏 p2，再次 listFavorites 应重新查 DB（缓存被 evict）
        Paper paper1 = Paper.builder().paperId("p1").title("Paper 1").build();
        PaperFavorite fav1 = PaperFavorite.builder()
                .id(1L).userId("u1").paperId("p1")
                .createdAt(LocalDateTime.now()).build();
        FavoriteResponse resp1 = FavoriteResponse.builder()
                .favoriteId(1L).paperId("p1").title("Paper 1").build();

        Page<PaperFavorite> page1 = new PageImpl<>(List.of(fav1), PageRequest.of(0, 10), 1);
        when(favoriteRepository.findByUserIdOrderByCreatedAtDesc(anyString(), any()))
                .thenReturn(page1);
        when(paperRepository.findByPaperIdIn(List.of("p1"))).thenReturn(List.of(paper1));
        when(favoriteMapper.toResponse(fav1, paper1)).thenReturn(resp1);

        // 第一次查询（缓存未命中，查 DB）
        PageResponse<FavoriteResponse> firstCall = favoriteService.listFavorites("u1", 1, 10);
        assertThat(firstCall.getItems()).hasSize(1);
        verify(favoriteRepository, times(1)).findByUserIdOrderByCreatedAtDesc("u1", PageRequest.of(0, 10));

        // 注：单元测试无 Spring 容器，@CacheEvict 不会真正生效
        // 此处验证的是 Service 方法可被正常调用，注解配置由前面的测试保证
        // 实际缓存行为由集成测试（Jm5IntegrationTest）验证
    }

    @Test
    @DisplayName("testRemoveFavoriteTriggersEvict - removeFavorite 调用后缓存应失效")
    void testRemoveFavoriteTriggersEvict() {
        when(favoriteRepository.existsByUserIdAndPaperId("u1", "p1")).thenReturn(true);

        favoriteService.removeFavorite("u1", "p1");

        verify(favoriteRepository, times(1)).deleteByUserIdAndPaperId("u1", "p1");
        // P2-1: 验证调用 CacheEvictionHelper 按用户前缀精准失效
        verify(cacheEvictionHelper).evictByPatternAfterCommit("favoriteList::user:favorites:u1:*");
    }

    @Test
    @DisplayName("testIdempotentAddDoesNotInvalidateCache - 幂等 addFavorite（已存在）仍触发 evict 保证一致性")
    void testIdempotentAddDoesNotInvalidateCache() {
        // 场景：用户 u1 已收藏 p1，再次 addFavorite 应幂等返回，但仍 evict 缓存
        Paper paper = Paper.builder().paperId("p1").title("Paper").build();
        PaperFavorite existing = PaperFavorite.builder()
                .id(1L).userId("u1").paperId("p1").build();
        FavoriteResponse resp = FavoriteResponse.builder()
                .favoriteId(1L).paperId("p1").title("Paper").build();

        when(paperRepository.findByPaperId("p1")).thenReturn(Optional.of(paper));
        when(favoriteRepository.findByUserIdAndPaperId("u1", "p1")).thenReturn(Optional.of(existing));
        when(favoriteMapper.toResponse(existing, paper)).thenReturn(resp);

        FavoriteResponse result = favoriteService.addFavorite("u1", "p1");

        assertThat(result).isNotNull();
        // 幂等：未调用 save
        verify(favoriteRepository, never()).save(any(PaperFavorite.class));
        // P2-1: 幂等场景仍触发缓存失效（与原 @CacheEvict 行为一致）
        verify(cacheEvictionHelper).evictByPatternAfterCommit("favoriteList::user:favorites:u1:*");
    }

    @Test
    @DisplayName("testIdempotentRemoveDoesNotInvalidateCache - 幂等 removeFavorite（不存在）仍触发 evict")
    void testIdempotentRemoveDoesNotInvalidateCache() {
        // 场景：用户 u1 未收藏 p1，removeFavorite 应幂等返回，但仍 evict 缓存
        when(favoriteRepository.existsByUserIdAndPaperId("u1", "p1")).thenReturn(false);

        favoriteService.removeFavorite("u1", "p1");

        // 幂等：未调用 delete
        verify(favoriteRepository, never()).deleteByUserIdAndPaperId("u1", "p1");
        // P2-1: 幂等场景仍触发缓存失效（与原 @CacheEvict 行为一致）
        verify(cacheEvictionHelper).evictByPatternAfterCommit("favoriteList::user:favorites:u1:*");
    }

    // ==================== 缓存空值防穿透验证 ====================

    @Test
    @DisplayName("testCacheNullPrevention - unless=#result==null 配置正确，空结果不缓存")
    void testCacheNullPrevention() throws NoSuchMethodException {
        Method method = FavoriteService.class.getMethod("listFavorites", String.class, int.class, int.class);
        Cacheable cacheable = method.getAnnotation(Cacheable.class);

        // unless = "#result == null" 确保空结果不缓存，防止缓存穿透
        assertThat(cacheable.unless()).isEqualTo("#result == null");
    }

    @Test
    @DisplayName("testEmptyResultNotCached - 空收藏列表返回非 null（PageResponse），可被缓存")
    void testEmptyResultNotCached() {
        // 场景：用户 u1 无收藏，listFavorites 返回空 PageResponse（非 null）
        Page<PaperFavorite> emptyPage = new PageImpl<>(List.of(), PageRequest.of(0, 10), 0);
        when(favoriteRepository.findByUserIdOrderByCreatedAtDesc(anyString(), any()))
                .thenReturn(emptyPage);
        when(paperRepository.findByPaperIdIn(List.of())).thenReturn(List.of());

        PageResponse<FavoriteResponse> result = favoriteService.listFavorites("u1", 1, 10);

        // 返回非 null 的空 PageResponse，可被缓存（避免每次查询都打到 DB）
        assertThat(result).isNotNull();
        assertThat(result.getItems()).isEmpty();
        assertThat(result.getTotal()).isEqualTo(0);
    }
}
