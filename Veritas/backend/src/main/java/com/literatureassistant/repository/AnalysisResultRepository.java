package com.literatureassistant.repository;

import com.literatureassistant.entity.AnalysisResult;
import com.literatureassistant.enums.AnalysisStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;

@Repository
@Transactional(readOnly = true)
public interface AnalysisResultRepository extends JpaRepository<AnalysisResult, Long> {

    Optional<AnalysisResult> findByAnalysisId(String analysisId);

    List<AnalysisResult> findBySessionId(String sessionId);

    List<AnalysisResult> findBySessionIdAndStatus(String sessionId, AnalysisStatus status);

    long countBySessionId(String sessionId);
}
