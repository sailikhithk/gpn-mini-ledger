package io.gpn.ledger.domain;

import jakarta.persistence.*;
import lombok.*;

import java.util.UUID;

/**
 * A single debit or credit leg of a {@link JournalEntry}.
 *
 * <p>Invariant LED-001: exactly one of {@code debitMinor} or {@code creditMinor}
 * must be greater than zero. A line is either a debit OR a credit, never both,
 * never neither. This is enforced by a CHECK constraint in the V1 migration
 * and validated in {@code LedgerService} before persisting.
 *
 * <p>All amounts are stored as signed 64-bit integers in minor units
 * (cents for USD, paise for INR). No floating point. No DECIMAL.
 */
@Entity
@Table(schema = "ledger", name = "journal_lines")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class JournalLine {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "journal_entry_id", nullable = false)
    private UUID journalEntryId;

    @Column(name = "account_id", nullable = false)
    private UUID accountId;

    /**
     * Debit amount in minor units. Zero if this is a credit line.
     */
    @Column(name = "debit_minor", nullable = false)
    private long debitMinor;

    /**
     * Credit amount in minor units. Zero if this is a debit line.
     */
    @Column(name = "credit_minor", nullable = false)
    private long creditMinor;
}
