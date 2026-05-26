package com.literatureassistant.entity;

import com.literatureassistant.enums.EducationLevel;
import com.literatureassistant.enums.KnowledgeLevel;
import com.literatureassistant.enums.PreferredStyle;
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
@Table(name = "user_profiles")
@EqualsAndHashCode(onlyExplicitlyIncluded = true)
public class UserProfile {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @EqualsAndHashCode.Include
    private Long id;

    @Column(name = "user_id", nullable = false, unique = true, length = 100)
    private String userId;

    @Column(name = "education_level", length = 20)
    private EducationLevel educationLevel;

    @Column(name = "research_field", length = 200)
    private String researchField;

    @Column(name = "knowledge_level", length = 20)
    private KnowledgeLevel knowledgeLevel;

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
