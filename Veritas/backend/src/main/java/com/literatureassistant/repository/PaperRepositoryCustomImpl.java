package com.literatureassistant.repository;

import com.literatureassistant.entity.Paper;
import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import jakarta.persistence.Query;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.Pageable;
import org.springframework.transaction.annotation.Transactional;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

@Transactional(readOnly = true)
public class PaperRepositoryCustomImpl implements PaperRepositoryCustom {

    /**
     * task35: 排序字段映射（不含方向，方向由 sortDirection 动态拼接）。
     * relevance 使用 MATCH AGAINST 表达式（无方向，sortDirection 对其无效，保持 DESC）。
     */
    private static final Map<String, String> SORT_MAPPING = new HashMap<>();
    static {
        SORT_MAPPING.put("relevance", "MATCH(title, `abstract`) AGAINST(?1 IN NATURAL LANGUAGE MODE)");
        SORT_MAPPING.put("year", "year");
        SORT_MAPPING.put("citations", "citation_count");
        SORT_MAPPING.put("title", "title");
    }

    private static final String DEFAULT_ORDER = "year";

    /**
     * task35: 排序方向白名单（统一小写）。非法值 fallback desc。
     */
    private static final Set<String> ALLOWED_DIRECTIONS = Set.of("asc", "desc");

    /**
     * task35: 扩展 SQL 模板，新增 author LIKE + keywords JSON_CONTAINS 过滤。
     * <p>注意：不使用 String.format 拼接 ORDER BY，因为 SQL 中 LIKE 通配符 '%' 会与
     * String.format 的格式说明符冲突（UnknownFormatConversionException）。
     * 改用字符串拼接 ORDER BY 子句。
     * <p>S-003 修复: keywords 过滤改用 JSON_QUOTE 自动转义特殊字符，防止 JSON 注入。
     */
    private static final String DATA_SQL_TEMPLATE =
            "SELECT * FROM papers " +
            "WHERE MATCH(title, `abstract`) AGAINST(?1 IN NATURAL LANGUAGE MODE) " +
            "AND (?2 IS NULL OR year >= ?2) " +
            "AND (?3 IS NULL OR year <= ?3) " +
            "AND (?4 IS NULL OR venue = ?4) " +
            "AND (?5 IS NULL OR authors LIKE CONCAT('%', ?5, '%')) " +
            "AND (?6 IS NULL OR JSON_CONTAINS(keywords, JSON_QUOTE(?6)))";

    private static final String COUNT_SQL =
            "SELECT COUNT(*) FROM papers " +
            "WHERE MATCH(title, `abstract`) AGAINST(?1 IN NATURAL LANGUAGE MODE) " +
            "AND (?2 IS NULL OR year >= ?2) " +
            "AND (?3 IS NULL OR year <= ?3) " +
            "AND (?4 IS NULL OR venue = ?4) " +
            "AND (?5 IS NULL OR authors LIKE CONCAT('%', ?5, '%')) " +
            "AND (?6 IS NULL OR JSON_CONTAINS(keywords, JSON_QUOTE(?6)))";

    @PersistenceContext
    private EntityManager entityManager;

    @Override
    public Page<Paper> searchByKeyword(String keyword, Integer yearFrom, Integer yearTo,
                                       String venue, String author, String keywords,
                                       String sort, String sortDirection, Pageable pageable) {
        // task35: 排序字段 fallback
        String sortField = SORT_MAPPING.getOrDefault(sort == null ? "" : sort, DEFAULT_ORDER);
        // task35: 排序方向白名单校验（统一小写，非法 fallback desc）
        String direction = (sortDirection != null && ALLOWED_DIRECTIONS.contains(sortDirection.toLowerCase()))
                ? sortDirection.toLowerCase() : "desc";
        // relevance 使用 MATCH AGAINST 表达式，强制 DESC（相关度降序）
        String orderClause = "relevance".equals(sort)
                ? sortField + " DESC"
                : sortField + " " + direction;
        String dataSql = DATA_SQL_TEMPLATE + " ORDER BY " + orderClause;

        Query dataQuery = entityManager.createNativeQuery(dataSql, Paper.class);
        setParameters(dataQuery, keyword, yearFrom, yearTo, venue, author, keywords);
        dataQuery.setFirstResult((int) pageable.getOffset());
        dataQuery.setMaxResults(pageable.getPageSize());
        List<Paper> results = dataQuery.getResultList();

        Query countQuery = entityManager.createNativeQuery(COUNT_SQL);
        setParameters(countQuery, keyword, yearFrom, yearTo, venue, author, keywords);
        Long total = ((Number) countQuery.getSingleResult()).longValue();

        return new PageImpl<>(results, pageable, total);
    }

    /**
     * task35: 扩展为 6 个参数（keyword/yearFrom/yearTo/venue/author/keywords）。
     */
    private void setParameters(Query query, String keyword, Integer yearFrom,
                               Integer yearTo, String venue, String author, String keywords) {
        query.setParameter(1, keyword);
        query.setParameter(2, yearFrom);
        query.setParameter(3, yearTo);
        query.setParameter(4, venue);
        query.setParameter(5, author);
        query.setParameter(6, keywords);
    }
}
