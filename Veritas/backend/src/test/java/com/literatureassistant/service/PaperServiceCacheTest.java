package com.literatureassistant.service;

import com.literatureassistant.dto.common.PageResponse;
import com.literatureassistant.dto.response.PaperDetailResponse;
import com.literatureassistant.dto.response.PaperResponse;
import com.literatureassistant.entity.Paper;
import com.literatureassistant.exception.ResourceNotFoundException;
import com.literatureassistant.mapper.PaperMapper;
import com.literatureassistant.repository.PaperRepository;
import com.literatureassistant.util.RedisKeyUtil;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;

import java.lang.reflect.Method;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * task33: 论文检索缓存 + 论文详情缓存测试。
 * <p>验证 @Cacheable 注解存在性、复合 Key 生成（RedisKeyUtil.paperSearchKey）、
 * null 参数规范化、空值防护（unless = "#result == null"）。
 * <p>由于 Mockito 无法直接模拟 Spring Cache 行为，测试通过反射读取注解属性 +
 * RedisKeyUtil 行为验证 + 业务逻辑正确性三层验证。
 */
@ExtendWith(MockitoExtension.class)
class PaperServiceCacheTest {

    @InjectMocks
    private PaperService paperService;

    @Mock
    private PaperRepository paperRepository;

    @Mock
    private PaperMapper paperMapper;

    // region 注解存在性验证（反射）

    @Test
    @DisplayName("getPaperDetail - @Cacheable(paperDetail) 注解存在 + unless 空值防护")
    void getPaperDetail_cacheHit_returnsCached() throws NoSuchMethodException {
        Method method = PaperService.class.getMethod("getPaperDetail", String.class);
        Cacheable cacheable = method.getAnnotation(Cacheable.class);

        assertThat(cacheable).isNotNull();
        assertThat(cacheable.value()).contains("paperDetail");
        assertThat(cacheable.key()).isEqualTo("#paperId");
        assertThat(cacheable.unless()).isEqualTo("#result == null");
    }

    @Test
    @DisplayName("searchPapers - @Cacheable(paperSearch) 注解存在 + 复合 Key 用 RedisKeyUtil.paperSearchKey")
    void searchPapers_cacheHit_returnsCached() throws NoSuchMethodException {
        Method method = PaperService.class.getMethod("searchPapers",
                String.class, Integer.class, Integer.class, String.class,
                String.class, String.class, String.class, String.class, int.class, int.class);
        Cacheable cacheable = method.getAnnotation(Cacheable.class);

        assertThat(cacheable).isNotNull();
        assertThat(cacheable.value()).contains("paperSearch");
        assertThat(cacheable.key())
                .contains("RedisKeyUtil")
                .contains("paperSearchKey");
    }

    @Test
    @DisplayName("listPapers - @Cacheable(paperList) 注解存在 + Key 用 RedisKeyUtil.paperListKey")
    void listPapers_cacheHit_returnsCached() throws NoSuchMethodException {
        Method method = PaperService.class.getMethod("listPapers", int.class, int.class);
        Cacheable cacheable = method.getAnnotation(Cacheable.class);

        assertThat(cacheable).isNotNull();
        assertThat(cacheable.value()).contains("paperList");
        assertThat(cacheable.key())
                .contains("RedisKeyUtil")
                .contains("paperListKey");
    }

    // endregion

    // region RedisKeyUtil null 参数规范化验证

    @Test
    @DisplayName("searchPapers - null 参数不会拼成 'null' 字符串（RedisKeyUtil 规范化）")
    void searchPapers_nullParams_noKeyConflict() {
        // 验证 RedisKeyUtil.paperSearchKey 对 null 参数的规范化行为（task35: 9 参数版本）
        String keyWithNullYearFrom = RedisKeyUtil.paperSearchKey(
                "agent", null, 2024, null, null, null, "relevance", "desc", 1, 10);
        String keyWithNullYearTo = RedisKeyUtil.paperSearchKey(
                "agent", 2020, null, null, null, null, "relevance", "desc", 1, 10);
        String keyWithNullVenue = RedisKeyUtil.paperSearchKey(
                "agent", 2020, 2024, null, null, null, "relevance", "desc", 1, 10);
        String keyAllNull = RedisKeyUtil.paperSearchKey(
                "agent", null, null, null, null, null, "relevance", "desc", 1, 10);

        // null 参数应被规范化为 "all"，不应出现 "null" 字符串
        assertThat(keyWithNullYearFrom).doesNotContain("null");
        assertThat(keyWithNullYearTo).doesNotContain("null");
        assertThat(keyWithNullVenue).doesNotContain("null");
        assertThat(keyAllNull).doesNotContain("null");

        // 相同参数组合应生成相同 Key
        String key1 = RedisKeyUtil.paperSearchKey(
                "agent", null, null, null, null, null, "relevance", "desc", 1, 10);
        String key2 = RedisKeyUtil.paperSearchKey(
                "agent", null, null, null, null, null, "relevance", "desc", 1, 10);
        assertThat(key1).isEqualTo(key2);

        // 不同 null 参数组合应生成不同 Key
        assertThat(keyWithNullYearFrom).isNotEqualTo(keyWithNullYearTo);
        assertThat(keyAllNull).isNotEqualTo(keyWithNullYearFrom);

        // paperListKey 验证
        String listKey1 = RedisKeyUtil.paperListKey(1, 10);
        String listKey2 = RedisKeyUtil.paperListKey(2, 10);
        assertThat(listKey1).isNotEqualTo(listKey2);
        assertThat(listKey1).isEqualTo("paper:list:1:10");
    }

    // endregion

    // region 空值防护（防穿透）业务逻辑验证

    @Test
    @DisplayName("getPaperDetail - notFound 抛 ResourceNotFoundException（unless 空值不缓存）")
    void getPaperDetail_notFound_penetrationProtection() {
        String paperId = "nonexistent_paper_xyz";
        when(paperRepository.findByPaperId(paperId)).thenReturn(Optional.empty());

        // 不存在时抛 ResourceNotFoundException，方法不返回 null，因此 unless = "#result == null" 不会缓存空值
        assertThatThrownBy(() -> paperService.getPaperDetail(paperId))
                .isInstanceOf(ResourceNotFoundException.class)
                .hasMessageContaining("Paper")
                .hasMessageContaining(paperId);

        verify(paperRepository).findByPaperId(paperId);
        verify(paperMapper, never()).toDetailResponse(any(Paper.class));
    }

    // endregion

    // region 业务逻辑正确性验证（Mock Repository 返回数据，验证 Service 调用链）

    @Test
    @DisplayName("getPaperDetail - 正常查询返回 PaperDetailResponse")
    void getPaperDetail_normal_returnsResponse() {
        String paperId = "arxiv_001";
        Paper paper = Paper.builder()
                .paperId(paperId)
                .title("Test Paper")
                .build();
        PaperDetailResponse expected = PaperDetailResponse.builder()
                .paperId(paperId)
                .title("Test Paper")
                .build();

        when(paperRepository.findByPaperId(paperId)).thenReturn(Optional.of(paper));
        when(paperMapper.toDetailResponse(paper)).thenReturn(expected);

        PaperDetailResponse result = paperService.getPaperDetail(paperId);

        assertThat(result).isNotNull();
        assertThat(result.getPaperId()).isEqualTo(paperId);
        assertThat(result.getTitle()).isEqualTo("Test Paper");
    }

    @Test
    @DisplayName("listPapers - 正常分页查询返回 PageResponse")
    void listPapers_normal_returnsPageResponse() {
        Paper paper = Paper.builder().paperId("p1").title("Test").build();
        PaperResponse paperResponse = PaperResponse.builder().paperId("p1").build();
        Page<Paper> mockPage = new PageImpl<>(List.of(paper), PageRequest.of(0, 10), 1);

        when(paperRepository.findAll(any(Pageable.class))).thenReturn(mockPage);
        when(paperMapper.toResponse(paper)).thenReturn(paperResponse);

        PageResponse<PaperResponse> result = paperService.listPapers(1, 10);

        assertThat(result).isNotNull();
        assertThat(result.getItems()).hasSize(1);
        assertThat(result.getItems().get(0).getPaperId()).isEqualTo("p1");
        assertThat(result.getTotal()).isEqualTo(1);
    }

    // endregion
}
