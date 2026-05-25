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

@Transactional(readOnly = true)
public class PaperRepositoryCustomImpl implements PaperRepositoryCustom {

    @PersistenceContext
    private EntityManager entityManager;

    private static final String DATA_SQL =
            "SELECT * FROM papers " +
            "WHERE MATCH(title, abstract) AGAINST(?1 IN NATURAL LANGUAGE MODE) " +
            "AND (?2 IS NULL OR year >= ?2) " +
            "AND (?3 IS NULL OR year <= ?3) " +
            "AND (?4 IS NULL OR venue = ?4) " +
            "ORDER BY CASE " +
            "WHEN ?5 = 'relevance' THEN MATCH(title, abstract) AGAINST(?1 IN NATURAL LANGUAGE MODE) " +
            "WHEN ?5 = 'year' THEN year " +
            "WHEN ?5 = 'citations' THEN citation_count " +
            "END DESC";

    private static final String COUNT_SQL =
            "SELECT COUNT(*) FROM papers " +
            "WHERE MATCH(title, abstract) AGAINST(?1 IN NATURAL LANGUAGE MODE) " +
            "AND (?2 IS NULL OR year >= ?2) " +
            "AND (?3 IS NULL OR year <= ?3) " +
            "AND (?4 IS NULL OR venue = ?4)";

    @Override
    public Page<Paper> searchByKeyword(String keyword, Integer yearFrom, Integer yearTo,
                                       String venue, String sort, Pageable pageable) {
        Query dataQuery = entityManager.createNativeQuery(DATA_SQL, Paper.class);
        setParameters(dataQuery, keyword, yearFrom, yearTo, venue, sort);
        dataQuery.setFirstResult((int) pageable.getOffset());
        dataQuery.setMaxResults(pageable.getPageSize());
        List<Paper> results = dataQuery.getResultList();

        Query countQuery = entityManager.createNativeQuery(COUNT_SQL);
        setParameters(countQuery, keyword, yearFrom, yearTo, venue, sort);
        Long total = ((Number) countQuery.getSingleResult()).longValue();

        return new PageImpl<>(results, pageable, total);
    }

    private void setParameters(Query query, String keyword, Integer yearFrom,
                               Integer yearTo, String venue, String sort) {
        query.setParameter(1, keyword);
        query.setParameter(2, yearFrom);
        query.setParameter(3, yearTo);
        query.setParameter(4, venue);
        query.setParameter(5, sort);
    }
}