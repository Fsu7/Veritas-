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

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * task36: 论文收藏服务单元测试。
 * <p>验证收藏/取消/列表/幂等/数据隔离/缓存失效。
 */
@ExtendWith(MockitoExtension.class)
class FavoriteServiceTest {

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

    @Test
    @DisplayName("testAddFavorite - 正常收藏返回 FavoriteResponse，含论文详情")
    void testAddFavorite() {
        Paper paper = Paper.builder().paperId("p1").title("Test Paper").build();
        PaperFavorite savedFav = PaperFavorite.builder()
                .id(1L).userId("u1").paperId("p1")
                .createdAt(LocalDateTime.now()).build();
        FavoriteResponse expected = FavoriteResponse.builder()
                .favoriteId(1L).paperId("p1").title("Test Paper").build();

        when(paperRepository.findByPaperId("p1")).thenReturn(Optional.of(paper));
        when(favoriteRepository.findByUserIdAndPaperId("u1", "p1")).thenReturn(Optional.empty());
        when(favoriteRepository.save(any(PaperFavorite.class))).thenReturn(savedFav);
        when(favoriteMapper.toResponse(savedFav, paper)).thenReturn(expected);

        FavoriteResponse result = favoriteService.addFavorite("u1", "p1");

        assertThat(result).isNotNull();
        assertThat(result.getFavoriteId()).isEqualTo(1L);
        assertThat(result.getPaperId()).isEqualTo("p1");
        assertThat(result.getTitle()).isEqualTo("Test Paper");

        ArgumentCaptor<PaperFavorite> favCaptor = ArgumentCaptor.forClass(PaperFavorite.class);
        verify(favoriteRepository).save(favCaptor.capture());
        assertThat(favCaptor.getValue().getUserId()).isEqualTo("u1");
        assertThat(favCaptor.getValue().getPaperId()).isEqualTo("p1");
    }

    @Test
    @DisplayName("testAddFavoriteIdempotent - 重复收藏返回成功，不重复插入")
    void testAddFavoriteIdempotent() {
        Paper paper = Paper.builder().paperId("p1").title("Test Paper").build();
        PaperFavorite existingFav = PaperFavorite.builder()
                .id(1L).userId("u1").paperId("p1")
                .createdAt(LocalDateTime.now()).build();
        FavoriteResponse expected = FavoriteResponse.builder()
                .favoriteId(1L).paperId("p1").title("Test Paper").build();

        when(paperRepository.findByPaperId("p1")).thenReturn(Optional.of(paper));
        when(favoriteRepository.findByUserIdAndPaperId("u1", "p1")).thenReturn(Optional.of(existingFav));
        when(favoriteMapper.toResponse(existingFav, paper)).thenReturn(expected);

        FavoriteResponse result = favoriteService.addFavorite("u1", "p1");

        assertThat(result).isNotNull();
        assertThat(result.getFavoriteId()).isEqualTo(1L);
        // 不调用 save
        verify(favoriteRepository, never()).save(any(PaperFavorite.class));
    }

    @Test
    @DisplayName("testAddFavoritePaperNotFound - 收藏不存在论文抛 ResourceNotFoundException")
    void testAddFavoritePaperNotFound() {
        when(paperRepository.findByPaperId("nonexistent")).thenReturn(Optional.empty());

        assertThatThrownBy(() -> favoriteService.addFavorite("u1", "nonexistent"))
                .isInstanceOf(ResourceNotFoundException.class)
                .hasMessageContaining("Paper not found: nonexistent");

        verify(favoriteRepository, never()).save(any(PaperFavorite.class));
    }

    @Test
    @DisplayName("testRemoveFavorite - 取消收藏后调用 deleteByUserIdAndPaperId")
    void testRemoveFavorite() {
        when(favoriteRepository.existsByUserIdAndPaperId("u1", "p1")).thenReturn(true);

        favoriteService.removeFavorite("u1", "p1");

        verify(favoriteRepository).deleteByUserIdAndPaperId("u1", "p1");
    }

    @Test
    @DisplayName("testRemoveFavoriteIdempotent - 重复取消返回成功，不抛异常")
    void testRemoveFavoriteIdempotent() {
        when(favoriteRepository.existsByUserIdAndPaperId("u1", "p1")).thenReturn(false);

        favoriteService.removeFavorite("u1", "p1");

        // 不调用 delete
        verify(favoriteRepository, never()).deleteByUserIdAndPaperId(anyString(), anyString());
    }

    @Test
    @DisplayName("testListFavorites - 分页返回，按 createdAt DESC，含论文详情")
    void testListFavorites() {
        PaperFavorite fav1 = PaperFavorite.builder()
                .id(1L).userId("u1").paperId("p1")
                .createdAt(LocalDateTime.now()).build();
        PaperFavorite fav2 = PaperFavorite.builder()
                .id(2L).userId("u1").paperId("p2")
                .createdAt(LocalDateTime.now().minusHours(1)).build();
        Page<PaperFavorite> favPage = new PageImpl<>(List.of(fav1, fav2), PageRequest.of(0, 10), 2);

        Paper paper1 = Paper.builder().paperId("p1").title("Paper 1").build();
        Paper paper2 = Paper.builder().paperId("p2").title("Paper 2").build();
        FavoriteResponse resp1 = FavoriteResponse.builder().favoriteId(1L).paperId("p1").title("Paper 1").build();
        FavoriteResponse resp2 = FavoriteResponse.builder().favoriteId(2L).paperId("p2").title("Paper 2").build();

        when(favoriteRepository.findByUserIdOrderByCreatedAtDesc(eq("u1"), any(Pageable.class)))
                .thenReturn(favPage);
        when(paperRepository.findByPaperIdIn(List.of("p1", "p2"))).thenReturn(List.of(paper1, paper2));
        when(favoriteMapper.toResponse(fav1, paper1)).thenReturn(resp1);
        when(favoriteMapper.toResponse(fav2, paper2)).thenReturn(resp2);

        PageResponse<FavoriteResponse> result = favoriteService.listFavorites("u1", 1, 10);

        assertThat(result).isNotNull();
        assertThat(result.getItems()).hasSize(2);
        assertThat(result.getTotal()).isEqualTo(2);
        assertThat(result.getItems().get(0).getPaperId()).isEqualTo("p1");
        assertThat(result.getItems().get(1).getPaperId()).isEqualTo("p2");
    }

    @Test
    @DisplayName("testListFavoritesEmpty - 空收藏列表返回空 PageResponse")
    void testListFavoritesEmpty() {
        Page<PaperFavorite> emptyPage = new PageImpl<>(List.of(), PageRequest.of(0, 10), 0);
        when(favoriteRepository.findByUserIdOrderByCreatedAtDesc(eq("u1"), any(Pageable.class)))
                .thenReturn(emptyPage);
        when(paperRepository.findByPaperIdIn(List.of())).thenReturn(List.of());

        PageResponse<FavoriteResponse> result = favoriteService.listFavorites("u1", 1, 10);

        assertThat(result).isNotNull();
        assertThat(result.getItems()).isEmpty();
        assertThat(result.getTotal()).isEqualTo(0);
    }

    @Test
    @DisplayName("testCacheEvictOnAdd - addFavorite 调用 CacheEvictionHelper 按用户前缀精准失效（P2-1）")
    void testCacheEvictOnAdd() {
        // P2-1: 移除 @CacheEvict(allEntries=true)，改用 CacheEvictionHelper 按用户前缀精准失效
        Paper paper = Paper.builder().paperId("p1").title("Test").build();
        PaperFavorite savedFav = PaperFavorite.builder()
                .id(1L).userId("u1").paperId("p1").build();
        FavoriteResponse resp = FavoriteResponse.builder()
                .favoriteId(1L).paperId("p1").title("Test").build();

        when(paperRepository.findByPaperId("p1")).thenReturn(Optional.of(paper));
        when(favoriteRepository.findByUserIdAndPaperId("u1", "p1")).thenReturn(Optional.empty());
        when(favoriteRepository.save(any(PaperFavorite.class))).thenReturn(savedFav);
        when(favoriteMapper.toResponse(savedFav, paper)).thenReturn(resp);

        favoriteService.addFavorite("u1", "p1");

        // 验证按用户前缀精准失效，而非 allEntries=true 清空整个缓存空间
        verify(cacheEvictionHelper).evictByPatternAfterCommit("favoriteList::user:favorites:u1:*");
    }

    @Test
    @DisplayName("testCacheEvictOnRemove - removeFavorite 调用 CacheEvictionHelper 按用户前缀精准失效（P2-1）")
    void testCacheEvictOnRemove() {
        // P2-1: 移除 @CacheEvict(allEntries=true)，改用 CacheEvictionHelper 按用户前缀精准失效
        when(favoriteRepository.existsByUserIdAndPaperId("u1", "p1")).thenReturn(true);

        favoriteService.removeFavorite("u1", "p1");

        verify(favoriteRepository).deleteByUserIdAndPaperId("u1", "p1");
        verify(cacheEvictionHelper).evictByPatternAfterCommit("favoriteList::user:favorites:u1:*");
    }

    @Test
    @DisplayName("testDataIsolation - 用户A收藏列表查询仅传 userId=u1，不含用户B数据")
    void testDataIsolation() {
        Page<PaperFavorite> emptyPage = new PageImpl<>(List.of(), PageRequest.of(0, 10), 0);
        // 用户 u1 查询时仅传 "u1"
        when(favoriteRepository.findByUserIdOrderByCreatedAtDesc(eq("u1"), any(Pageable.class)))
                .thenReturn(emptyPage);
        when(paperRepository.findByPaperIdIn(List.of())).thenReturn(List.of());

        favoriteService.listFavorites("u1", 1, 10);

        // 验证 Repository 调用时 userId 参数为 "u1"，不会查询到 u2 的数据
        ArgumentCaptor<String> userIdCaptor = ArgumentCaptor.forClass(String.class);
        verify(favoriteRepository).findByUserIdOrderByCreatedAtDesc(userIdCaptor.capture(), any(Pageable.class));
        assertThat(userIdCaptor.getValue()).isEqualTo("u1");
    }

    @Test
    @DisplayName("testListFavoritesCacheable - listFavorites 方法含 @Cacheable(favoriteList) 注解，Key 含 page/size")
    void testListFavoritesCacheable() throws NoSuchMethodException {
        // 修复 B-002: Key 必须包含 page/size，避免不同分页查询命中同一缓存
        var method = FavoriteService.class.getMethod("listFavorites", String.class, int.class, int.class);
        var cacheable = method.getAnnotation(org.springframework.cache.annotation.Cacheable.class);
        assertThat(cacheable).isNotNull();
        assertThat(cacheable.value()).contains("favoriteList");
        // Key 表达式应调用 RedisKeyUtil.favoriteListKey(#userId, #page, #size)
        assertThat(cacheable.key()).contains("favoriteListKey");
        assertThat(cacheable.key()).contains("#userId");
        assertThat(cacheable.key()).contains("#page");
        assertThat(cacheable.key()).contains("#size");
    }
}
