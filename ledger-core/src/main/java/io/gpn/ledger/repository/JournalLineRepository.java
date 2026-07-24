package io.gpn.ledger.repository;

import io.gpn.ledger.domain.JournalLine;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

@Repository
public interface JournalLineRepository extends JpaRepository<JournalLine, UUID> {

    List<JournalLine> findByJournalEntryId(UUID journalEntryId);

    /**
     * Sums all debit and credit lines for an account.
     * Used for balance computation and the balance invariant check.
     */
    @Query("""
        SELECT COALESCE(SUM(l.debitMinor), 0), COALESCE(SUM(l.creditMinor), 0)
        FROM JournalLine l
        WHERE l.accountId = :accountId
        """)
    Object[] sumDebitsAndCredits(@Param("accountId") UUID accountId);
}
