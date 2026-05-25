package com.literatureassistant.entity;

import com.literatureassistant.enums.AnalysisStatus;
import com.literatureassistant.enums.AnalysisStatusConverter;
import com.literatureassistant.enums.AnalysisType;
import com.literatureassistant.enums.AnalysisTypeConverter;
import jakarta.persistence.Column;
import jakarta.persistence.Convert;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Entity
@Table(name = "analysis_results")
public class AnalysisResult {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "analysis_id", unique = true, nullable = false, length = 100)
    private String analysisId;

    @Column(name = "session_id", nullable = false, length = 100)
    private String sessionId;

    @Convert(converter = AnalysisTypeConverter.class)
    @Column(nullable = false, length = 20)
    private AnalysisType type;

    @Column(nullable = false, columnDefinition = "JSON")
    private String result;

    @Convert(converter = AnalysisStatusConverter.class)
    @Column(nullable = false, length = 20)
    private AnalysisStatus status;

    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
    }
}
