package com.literatureassistant.repository;

import com.literatureassistant.entity.PaperFavorite;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

import java.util.Optional;

@Repository
@Transactional(readOnly = true)
public interface PaperFavoriteRepository extends JpaRepository<PaperFavorite, Long> {

    Page<PaperFavorite> findByUserIdOrderByCreatedAtDesc(String userId, Pageable pageable);

    boolean existsByUserIdAndPaperId(String userId, String paperId);

    /**
     * task36: 根据 userId + paperId 查询收藏记录（幂等性判断使用）。
     */
    Optional<PaperFavorite> findByUserIdAndPaperId(String userId, String paperId);

    @Transactional
    void deleteByUserIdAndPaperId(String userId, String paperId);
}
