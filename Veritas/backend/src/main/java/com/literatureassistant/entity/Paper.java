package com.literatureassistant.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.EqualsAndHashCode;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.LocalDateTime;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Entity
@Table(name = "papers")
@EqualsAndHashCode(onlyExplicitlyIncluded = true)
public class Paper {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @EqualsAndHashCode.Include
    private Long id;

    @Column(name = "paper_id", unique = true, nullable = false, length = 100)
    private String paperId;

    @Column(nullable = false, length = 500)
    private String title;

    @Column(columnDefinition = "JSON")
    private String authors;

    @Column(name = "abstract", columnDefinition = "TEXT")
    private String abstractText;

    @Column
    private Integer year;

    @Column(length = 200)
    private String venue;

    @Column(columnDefinition = "JSON")
    private String keywords;

    @Column(name = "citation_count")
    private Integer citationCount;

    @Column(name = "pdf_url", length = 500)
    private String pdfUrl;

    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        updatedAt = LocalDateTime.now();
    }

    @PreUpdate
    protected void onUpdate() {
        updatedAt = LocalDateTime.now();
    }
}
