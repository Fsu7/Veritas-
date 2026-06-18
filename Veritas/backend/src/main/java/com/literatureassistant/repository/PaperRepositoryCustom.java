package com.literatureassistant.repository;

import com.literatureassistant.entity.Paper;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;

public interface PaperRepositoryCustom {

    /**
     * task35: 扩展搜索接口，新增 author/keywords 过滤 + sortDirection 排序方向。
     *
     * @param keyword      搜索关键词（MATCH AGAINST）
     * @param yearFrom     年份下限（可空）
     * @param yearTo       年份上限（可空）
     * @param venue        会议/期刊（可空）
     * @param author       作者过滤（LIKE 模糊匹配，可空）
     * @param keywords     关键词过滤（JSON_CONTAINS，可空）
     * @param sort         排序字段：relevance/year/citations/title
     * @param sortDirection 排序方向：asc/desc（非法值 fallback desc）
     * @param pageable     分页
     */
    Page<Paper> searchByKeyword(String keyword, Integer yearFrom, Integer yearTo,
                                String venue, String author, String keywords,
                                String sort, String sortDirection, Pageable pageable);
}
