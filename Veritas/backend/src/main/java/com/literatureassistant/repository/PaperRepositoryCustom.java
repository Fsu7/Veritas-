package com.literatureassistant.repository;

import com.literatureassistant.entity.Paper;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;

public interface PaperRepositoryCustom {

    Page<Paper> searchByKeyword(String keyword, Integer yearFrom, Integer yearTo,
                                String venue, String sort, Pageable pageable);
}