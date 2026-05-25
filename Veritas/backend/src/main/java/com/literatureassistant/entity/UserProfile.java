package com.literatureassistant.entity;

import com.literatureassistant.enums.EducationLevel;
import com.literatureassistant.enums.EducationLevelConverter;
import com.literatureassistant.enums.KnowledgeLevel;
import com.literatureassistant.enums.KnowledgeLevelConverter;
import com.literatureassistant.enums.PreferredStyle;
import com.literatureassistant.enums.PreferredStyleConverter;
import jakarta.persistence.Column;
import jakarta.persistence.Convert;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.PreUpdate;
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
@Table(name = "user_profiles")
public class UserProfile {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false, length = 100)
    private String userId;

    @Convert(converter = EducationLevelConverter.class)
    @Column(name = "education_level", length = 20)
    private EducationLevel educationLevel;

    @Column(name = "research_field", length = 200)
    private String researchField;

    @Convert(converter = KnowledgeLevelConverter.class)
    @Column(name = "knowledge_level", length = 20)
    private KnowledgeLevel knowledgeLevel;

    @Convert(converter = PreferredStyleConverter.class)
    @Column(name = "preferred_style", length = 20)
    private PreferredStyle preferredStyle;

    @Column(name = "profile_data", columnDefinition = "JSON")
    private String profileData;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    @PrePersist
    @PreUpdate
    protected void onUpdate() {
        updatedAt = LocalDateTime.now();
    }
}
