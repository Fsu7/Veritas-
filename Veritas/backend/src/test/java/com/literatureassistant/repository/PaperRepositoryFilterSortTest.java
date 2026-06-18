package com.literatureassistant.repository;

import com.literatureassistant.entity.Paper;
import com.literatureassistant.util.RedisKeyUtil;
import jakarta.persistence.EntityManager;
import jakarta.persistence.Query;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;

import java.util.Collections;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * task35: 论文筛选排序单元测试。
 * <p>验证 PaperRepositoryCustomImpl 的 author/keywords 过滤、sort=title 排序、
 * sortDirection 方向控制、非法值 fallback、组合条件、缓存 Key 隔离。
 * <p>使用 Mockito Mock EntityManager，验证 SQL 拼接和参数绑定正确性。
 */
@ExtendWith(MockitoExtension.class)
class PaperRepositoryFilterSortTest {

    @Mock
    private EntityManager entityManager;

    @Mock
    private Query dataQuery;

    @Mock
    private Query countQuery;

    @InjectMocks
    private PaperRepositoryCustomImpl repository;

    private Pageable pageable;

    @BeforeEach
    void setUp() {
        pageable = PageRequest.of(0, 10);
    }

    @Test
    @DisplayName("testAuthorFilter - author 参数绑定到 ?5 位置参数")
    void testAuthorFilter() {
        when(entityManager.createNativeQuery(anyString(), eq(Paper.class))).thenReturn(dataQuery);
        when(entityManager.createNativeQuery(anyString())).thenReturn(countQuery);
        when(dataQuery.getResultList()).thenReturn(Collections.emptyList());
        when(countQuery.getSingleResult()).thenReturn(0L);

        repository.searchByKeyword("AI", null, null, null,
                "Zhang", null, "relevance", "desc", pageable);

        // 验证 ?5 位置参数绑定 author
        verify(dataQuery).setParameter(5, "Zhang");
        verify(countQuery).setParameter(5, "Zhang");
    }

    @Test
    @DisplayName("testKeywordsFilter - keywords 参数绑定到 ?6 位置参数，SQL 使用 JSON_QUOTE 防注入")
    void testKeywordsFilter() {
        when(entityManager.createNativeQuery(anyString(), eq(Paper.class))).thenReturn(dataQuery);
        when(entityManager.createNativeQuery(anyString())).thenReturn(countQuery);
        when(dataQuery.getResultList()).thenReturn(Collections.emptyList());
        when(countQuery.getSingleResult()).thenReturn(0L);

        repository.searchByKeyword("AI", null, null, null,
                null, "deep learning", "relevance", "desc", pageable);

        // 验证 ?6 位置参数绑定 keywords
        verify(dataQuery).setParameter(6, "deep learning");
        verify(countQuery).setParameter(6, "deep learning");

        // S-003 修复: 验证 SQL 使用 JSON_QUOTE 而非 CONCAT('"', ?6, '"')，防止 JSON 注入
        ArgumentCaptor<String> sqlCaptor = ArgumentCaptor.forClass(String.class);
        verify(entityManager).createNativeQuery(sqlCaptor.capture(), eq(Paper.class));
        assertThat(sqlCaptor.getValue()).contains("JSON_QUOTE(?6)");
        assertThat(sqlCaptor.getValue()).doesNotContain("CONCAT('\"'");
    }

    @Test
    @DisplayName("testTitleSort - sort=title 时 ORDER BY title DESC（默认 desc）")
    void testTitleSort() {
        when(entityManager.createNativeQuery(anyString(), eq(Paper.class))).thenReturn(dataQuery);
        when(entityManager.createNativeQuery(anyString())).thenReturn(countQuery);
        when(dataQuery.getResultList()).thenReturn(Collections.emptyList());
        when(countQuery.getSingleResult()).thenReturn(0L);

        repository.searchByKeyword("AI", null, null, null,
                null, null, "title", "desc", pageable);

        ArgumentCaptor<String> sqlCaptor = ArgumentCaptor.forClass(String.class);
        verify(entityManager).createNativeQuery(sqlCaptor.capture(), eq(Paper.class));
        assertThat(sqlCaptor.getValue()).contains("ORDER BY title desc");
    }

    @Test
    @DisplayName("testSortDirectionAsc - sortDirection=asc 时 ORDER BY {field} asc")
    void testSortDirectionAsc() {
        when(entityManager.createNativeQuery(anyString(), eq(Paper.class))).thenReturn(dataQuery);
        when(entityManager.createNativeQuery(anyString())).thenReturn(countQuery);
        when(dataQuery.getResultList()).thenReturn(Collections.emptyList());
        when(countQuery.getSingleResult()).thenReturn(0L);

        repository.searchByKeyword("AI", null, null, null,
                null, null, "year", "asc", pageable);

        ArgumentCaptor<String> sqlCaptor = ArgumentCaptor.forClass(String.class);
        verify(entityManager).createNativeQuery(sqlCaptor.capture(), eq(Paper.class));
        assertThat(sqlCaptor.getValue()).contains("ORDER BY year asc");
    }

    @Test
    @DisplayName("testSortDirectionDesc - sortDirection=desc 时 ORDER BY {field} desc")
    void testSortDirectionDesc() {
        when(entityManager.createNativeQuery(anyString(), eq(Paper.class))).thenReturn(dataQuery);
        when(entityManager.createNativeQuery(anyString())).thenReturn(countQuery);
        when(dataQuery.getResultList()).thenReturn(Collections.emptyList());
        when(countQuery.getSingleResult()).thenReturn(0L);

        repository.searchByKeyword("AI", null, null, null,
                null, null, "citations", "desc", pageable);

        ArgumentCaptor<String> sqlCaptor = ArgumentCaptor.forClass(String.class);
        verify(entityManager).createNativeQuery(sqlCaptor.capture(), eq(Paper.class));
        assertThat(sqlCaptor.getValue()).contains("ORDER BY citation_count desc");
    }

    @Test
    @DisplayName("testInvalidSortDirectionFallback - sortDirection=random 时 fallback desc")
    void testInvalidSortDirectionFallback() {
        when(entityManager.createNativeQuery(anyString(), eq(Paper.class))).thenReturn(dataQuery);
        when(entityManager.createNativeQuery(anyString())).thenReturn(countQuery);
        when(dataQuery.getResultList()).thenReturn(Collections.emptyList());
        when(countQuery.getSingleResult()).thenReturn(0L);

        repository.searchByKeyword("AI", null, null, null,
                null, null, "year", "random", pageable);

        ArgumentCaptor<String> sqlCaptor = ArgumentCaptor.forClass(String.class);
        verify(entityManager).createNativeQuery(sqlCaptor.capture(), eq(Paper.class));
        // 非法方向 fallback desc
        assertThat(sqlCaptor.getValue()).contains("ORDER BY year desc");
    }

    @Test
    @DisplayName("testCombinedFilterSort - author+keywords+year+venue+sort=title+sortDirection=asc 同时生效")
    void testCombinedFilterSort() {
        when(entityManager.createNativeQuery(anyString(), eq(Paper.class))).thenReturn(dataQuery);
        when(entityManager.createNativeQuery(anyString())).thenReturn(countQuery);
        when(dataQuery.getResultList()).thenReturn(Collections.emptyList());
        when(countQuery.getSingleResult()).thenReturn(0L);

        repository.searchByKeyword("AI", 2020, 2024, "ICML",
                "Zhang", "deep learning", "title", "asc", pageable);

        // 验证所有参数正确绑定
        verify(dataQuery).setParameter(1, "AI");
        verify(dataQuery).setParameter(2, 2020);
        verify(dataQuery).setParameter(3, 2024);
        verify(dataQuery).setParameter(4, "ICML");
        verify(dataQuery).setParameter(5, "Zhang");
        verify(dataQuery).setParameter(6, "deep learning");

        // 验证 SQL 含 ORDER BY title asc
        ArgumentCaptor<String> sqlCaptor = ArgumentCaptor.forClass(String.class);
        verify(entityManager).createNativeQuery(sqlCaptor.capture(), eq(Paper.class));
        assertThat(sqlCaptor.getValue()).contains("ORDER BY title asc");
    }

    @Test
    @DisplayName("testCacheKeyIsolation - 不同 author/keywords/sortDirection 参数组合生成不同缓存 key")
    void testCacheKeyIsolation() {
        // 组合1：全 null
        String key1 = RedisKeyUtil.paperSearchKey("AI", null, null, null,
                null, null, "relevance", "desc", 1, 10);
        // 组合2：含 author
        String key2 = RedisKeyUtil.paperSearchKey("AI", null, null, null,
                "Zhang", null, "relevance", "desc", 1, 10);
        // 组合3：含 keywords
        String key3 = RedisKeyUtil.paperSearchKey("AI", null, null, null,
                null, "deep learning", "relevance", "desc", 1, 10);
        // 组合4：含 sortDirection=asc
        String key4 = RedisKeyUtil.paperSearchKey("AI", null, null, null,
                null, null, "relevance", "asc", 1, 10);
        // 组合5：sort=title
        String key5 = RedisKeyUtil.paperSearchKey("AI", null, null, null,
                null, null, "title", "desc", 1, 10);

        // 所有 key 互不相同
        assertThat(key1).isNotEqualTo(key2);
        assertThat(key1).isNotEqualTo(key3);
        assertThat(key1).isNotEqualTo(key4);
        assertThat(key1).isNotEqualTo(key5);
        assertThat(key2).isNotEqualTo(key3);
        assertThat(key4).isNotEqualTo(key5);

        // null 参数规范化为 "all"，不出现 "null" 字符串
        assertThat(key1).doesNotContain("null");
        assertThat(key1).contains("all");

        // key 前缀正确
        assertThat(key1).startsWith("paper:search:");
    }

    @Test
    @DisplayName("testRelevanceSortForcedDesc - sort=relevance 时强制 DESC（sortDirection 无效）")
    void testRelevanceSortForcedDesc() {
        when(entityManager.createNativeQuery(anyString(), eq(Paper.class))).thenReturn(dataQuery);
        when(entityManager.createNativeQuery(anyString())).thenReturn(countQuery);
        when(dataQuery.getResultList()).thenReturn(Collections.emptyList());
        when(countQuery.getSingleResult()).thenReturn(0L);

        // 即使 sortDirection=asc，relevance 也强制 DESC
        repository.searchByKeyword("AI", null, null, null,
                null, null, "relevance", "asc", pageable);

        ArgumentCaptor<String> sqlCaptor = ArgumentCaptor.forClass(String.class);
        verify(entityManager).createNativeQuery(sqlCaptor.capture(), eq(Paper.class));
        assertThat(sqlCaptor.getValue()).contains("ORDER BY MATCH(title, `abstract`) AGAINST(?1 IN NATURAL LANGUAGE MODE) DESC");
    }
}