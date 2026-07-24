package io.gpn.ledger.repository;

import io.gpn.ledger.domain.AuthorizationHold;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;
import java.util.UUID;

@Repository
public interface AuthorizationHoldRepository extends JpaRepository<AuthorizationHold, UUID> {
    Optional<AuthorizationHold> findByAuthorizationId(UUID authorizationId);
}
