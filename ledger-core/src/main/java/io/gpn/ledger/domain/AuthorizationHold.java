package io.gpn.ledger.domain;

import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;
import java.util.UUID;

/**
 * Tracks the lifecycle of an authorization: authorized, captured, and refunded amounts.
 *
 * <p>Invariant PAY-001: {@code capturedMinor} never exceeds {@code authorizedMinor}.
 * Enforced by a CHECK constraint in the V1 migration and by the SERIALIZABLE
 * isolation level in {@code LedgerService.capture}.
 *
 * <p>Invariant: {@code refundedMinor} never exceeds {@code capturedMinor}.
 */
@Entity
@Table(schema = "ledger", name = "authorization_holds")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class AuthorizationHold {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "authorization_id", nullable = false, unique = true)
    private UUID authorizationId;

    @Column(name = "merchant_id", nullable = false)
    private UUID merchantId;

    @Column(nullable = false, length = 3)
    private String currency;

    @Column(name = "authorized_minor", nullable = false)
    private long authorizedMinor;

    @Column(name = "captured_minor", nullable = false)
    private long capturedMinor;

    @Column(name = "refunded_minor", nullable = false)
    private long refundedMinor;

    @Column(nullable = false, length = 16)
    private String status;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    @PrePersist
    void onCreate() {
        if (createdAt == null) createdAt = Instant.now();
        if (updatedAt == null) updatedAt = Instant.now();
        if (status == null) status = "OPEN";
    }

    @PreUpdate
    void onUpdate() {
        updatedAt = Instant.now();
    }
}
