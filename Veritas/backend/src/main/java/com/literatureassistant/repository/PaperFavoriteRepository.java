package com.literatureassistant.repository;

import com.literatureassistant.entity.PaperFavorite;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

@Repository
@Transactional(readOnly = true)
public interface PaperFavoriteRepository extends JpaRepository<PaperFavorite, Long> {

    Page<PaperFavorite> findByUserIdOrderByCreatedAtDesc(String userId, Pageable pageable);

    boolean existsByUserIdAndPaperId(String userId, String paperId);

    @Transactional
    void deleteByUserIdAndPaperId(String userId, String paperId);
}
