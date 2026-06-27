package com.literatureassistant.repository;

import com.literatureassistant.entity.Session;
import jakarta.persistence.LockModeType;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

import java.util.Optional;

@Repository
@Transactional(readOnly = true)
public interface SessionRepository extends JpaRepository<Session, Long> {

    Optional<Session> findBySessionId(String sessionId);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("SELECT s FROM Session s WHERE s.sessionId = :sessionId")
    Optional<Session> findBySessionIdForUpdate(@Param("sessionId") String sessionId);

    Page<Session> findByUserIdOrderByCreatedAtDesc(String userId, Pageable pageable);
}
