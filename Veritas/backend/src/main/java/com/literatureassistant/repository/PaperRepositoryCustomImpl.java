package com.literatureassistant.repository;

import com.literatureassistant.entity.Paper;
import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import jakarta.persistence.Query;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.Pageable;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Map;

@Transactional(readOnly = true)
public class PaperRepositoryCustomImpl implements PaperRepositoryCustom {

    private static final Map<String, String> SORT_MAPPING = Map.of(
            "relevance", "MATCH(title, `abstract`) AGAINST(?1 IN NATURAL LANGUAGE MODE) DESC",
            "year", "year DESC",
            "citations", "citation_count DESC"
    );

    private static final String DEFAULT_ORDER = "year DESC";

    private static final String DATA_SQL_TEMPLATE =
            "SELECT * FROM papers " +
            "WHERE MATCH(title, `abstract`) AGAINST(?1 IN NATURAL LANGUAGE MODE) " +
            "AND (?2 IS NULL OR year >= ?2) " +
            "AND (?3 IS NULL OR year <= ?3) " +
            "AND (?4 IS NULL OR venue = ?4) " +
            "ORDER BY %s";

    private static final String COUNT_SQL =
            "SELECT COUNT(*) FROM papers " +
            "WHERE MATCH(title, `abstract`) AGAINST(?1 IN NATURAL LANGUAGE MODE) " +
            "AND (?2 IS NULL OR year >= ?2) " +
            "AND (?3 IS NULL OR year <= ?3) " +
            "AND (?4 IS NULL OR venue = ?4)";

    @PersistenceContext
    private EntityManager entityManager;

    @Override
    public Page<Paper> searchByKeyword(String keyword, Integer yearFrom, Integer yearTo,
                                       String venue, String sort, Pageable pageable) {
        String orderClause = SORT_MAPPING.getOrDefault(sort, DEFAULT_ORDER);
        String dataSql = String.format(DATA_SQL_TEMPLATE, orderClause);

        Query dataQuery = entityManager.createNativeQuery(dataSql, Paper.class);
        setParameters(dataQuery, keyword, yearFrom, yearTo, venue);
        dataQuery.setFirstResult((int) pageable.getOffset());
        dataQuery.setMaxResults(pageable.getPageSize());
        List<Paper> results = dataQuery.getResultList();

        Query countQuery = entityManager.createNativeQuery(COUNT_SQL);
        setParameters(countQuery, keyword, yearFrom, yearTo, venue);
        Long total = ((Number) countQuery.getSingleResult()).longValue();

        return new PageImpl<>(results, pageable, total);
    }

    private void setParameters(Query query, String keyword, Integer yearFrom,
                               Integer yearTo, String venue) {
        query.setParameter(1, keyword);
        query.setParameter(2, yearFrom);
        query.setParameter(3, yearTo);
        query.setParameter(4, venue);
    }
}
