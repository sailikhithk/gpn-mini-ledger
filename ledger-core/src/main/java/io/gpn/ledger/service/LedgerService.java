package io.gpn.ledger.service;

import io.gpn.ledger.config.LedgerProperties;
import io.gpn.ledger.domain.*;
import io.gpn.ledger.repository.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.dao.ConcurrencyFailureException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.TransactionDefinition;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionTemplate;

import java.util.UUID;

/**
 * Layer 1 (CP): The core double-entry ledger service.
 *
 * <p>This is the single most important class in the project. It enforces:
 * <ul>
 *   <li><b>LED-001</b>: sum of debits = sum of credits (double-entry invariant)</li>
 *   <li><b>PAY-001</b>: captured never exceeds authorized</li>
 *   <li><b>Immutability</b>: journal entries and lines are append-only</li>
 *   <li><b>Isolation</b>: SERIALIZABLE on all writes, with retry on SQLSTATE 40001</li>
 * </ul>
 *
 * <p>Design references:
 * <ul>
 *   <li>{@code merchant-payments-platform/LedgerService.java} - SERIALIZABLE + minor units + retry</li>
 *   <li>{@code sentinel-ledger/INVARIANTS.md} - LED-001, PAY-001 invariants</li>
 *   <li>{@code merchant-payments-platform/ledger-design.md} - double-entry principles</li>
 * </ul>
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class LedgerService {

    private final JournalEntryRepository journalEntryRepository;
    private final JournalLineRepository journalLineRepository;
    private final AuthorizationHoldRepository authorizationHoldRepository;
    private final AccountRepository accountRepository;
    private final LedgerProperties properties;
    private final PlatformTransactionManager transactionManager;

    /**
     * Places an authorization hold: debits the merchant receivable account,
     * credits the customer liability account.
     *
     * <p>Idempotent: if the idempotency key already exists, returns the original
     * journal entry without creating a new one.
     */
    public LedgerEntryResult createAuthorizationHold(
            String idempotencyKey,
            UUID authorizationId,
            UUID merchantId,
            String currency,
            long amountMinor
    ) {
        return executeWithRetry(() -> {
            // Idempotency check inside the SERIALIZABLE transaction
            var existing = journalEntryRepository.findByIdempotencyKey(idempotencyKey);
            if (existing.isPresent()) {
                log.debug("Idempotent replay for key={}, returning existing entry", idempotencyKey);
                return toResult(existing.get(), amountMinor);
            }

            // Create the authorization hold record
            var hold = AuthorizationHold.builder()
                .authorizationId(authorizationId)
                .merchantId(merchantId)
                .currency(currency)
                .authorizedMinor(amountMinor)
                .capturedMinor(0)
                .refundedMinor(0)
                .status("OPEN")
                .build();
            authorizationHoldRepository.save(hold);

            // Post the double-entry: debit receivable, credit customer liability
            var entry = postDoubleEntry(
                idempotencyKey, EntryType.AUTH_HOLD, authorizationId, currency, amountMinor,
                "merchant_receivable", "customer_liability"
            );
            return toResult(entry, amountMinor);
        });
    }

    /**
     * Captures a previously authorized amount: debits customer liability,
     * credits merchant revenue. Enforces PAY-001 (capture <= authorized).
     *
     * <p>Under SERIALIZABLE isolation, concurrent captures of the same
     * authorization will serialize. The first transaction commits, the second
     * sees the updated {@code capturedMinor} and either succeeds (if within
     * the remaining authorized amount) or fails with
     * {@link CaptureExceedsAuthorizationException}.
     */
    public LedgerEntryResult capture(
            String idempotencyKey,
            UUID authorizationId,
            long captureAmount
    ) {
        return executeWithRetry(() -> {
            var existing = journalEntryRepository.findByIdempotencyKey(idempotencyKey);
            if (existing.isPresent()) {
                log.debug("Idempotent replay for capture key={}", idempotencyKey);
                return toResult(existing.get(), captureAmount);
            }

            var hold = authorizationHoldRepository.findByAuthorizationId(authorizationId)
                .orElseThrow(() -> new IllegalArgumentException(
                    "Authorization not found: " + authorizationId));

            // PAY-001: captured never exceeds authorized
            long newCaptured = hold.getCapturedMinor() + captureAmount;
            if (newCaptured > hold.getAuthorizedMinor()) {
                throw new CaptureExceedsAuthorizationException(
                    authorizationId,
                    hold.getAuthorizedMinor(),
                    hold.getCapturedMinor(),
                    captureAmount
                );
            }

            hold.setCapturedMinor(newCaptured);
            if (newCaptured == hold.getAuthorizedMinor()) {
                hold.setStatus("CAPTURED");
            }
            authorizationHoldRepository.save(hold);

            var entry = postDoubleEntry(
                idempotencyKey, EntryType.CAPTURE, authorizationId, hold.getCurrency(),
                captureAmount, "customer_liability", "merchant_revenue"
            );
            return toResult(entry, captureAmount);
        });
    }

    /**
     * Refunds a previously captured amount: debits merchant revenue,
     * credits customer liability. Enforces refund <= captured.
     */
    public LedgerEntryResult refund(
            String idempotencyKey,
            UUID authorizationId,
            long refundAmount
    ) {
        return executeWithRetry(() -> {
            var existing = journalEntryRepository.findByIdempotencyKey(idempotencyKey);
            if (existing.isPresent()) {
                log.debug("Idempotent replay for refund key={}", idempotencyKey);
                return toResult(existing.get(), refundAmount);
            }

            var hold = authorizationHoldRepository.findByAuthorizationId(authorizationId)
                .orElseThrow(() -> new IllegalArgumentException(
                    "Authorization not found: " + authorizationId));

            long newRefunded = hold.getRefundedMinor() + refundAmount;
            if (newRefunded > hold.getCapturedMinor()) {
                throw new RefundExceedsCapturedException(
                    authorizationId,
                    hold.getCapturedMinor(),
                    hold.getRefundedMinor(),
                    refundAmount
                );
            }

            hold.setRefundedMinor(newRefunded);
            authorizationHoldRepository.save(hold);

            var entry = postDoubleEntry(
                idempotencyKey, EntryType.REFUND, authorizationId, hold.getCurrency(),
                refundAmount, "merchant_revenue", "customer_liability"
            );
            return toResult(entry, refundAmount);
        });
    }

    /**
     * Posts a balanced double-entry: debit one account, credit another.
     * Enforces LED-001 (debits = credits) by construction.
     */
    private JournalEntry postDoubleEntry(
            String idempotencyKey,
            EntryType entryType,
            UUID referenceId,
            String currency,
            long amountMinor,
            String debitAccountCode,
            String creditAccountCode
    ) {
        if (amountMinor <= 0) {
            throw new IllegalArgumentException("amountMinor must be positive, got " + amountMinor);
        }

        var entry = JournalEntry.builder()
            .idempotencyKey(idempotencyKey)
            .entryType(entryType)
            .referenceId(referenceId)
            .currency(currency)
            .build();
        entry = journalEntryRepository.save(entry);

        var debitAccount = accountRepository.findByCode(debitAccountCode)
            .orElseThrow(() -> new IllegalStateException(
                "Account not found: " + debitAccountCode));
        var creditAccount = accountRepository.findByCode(creditAccountCode)
            .orElseThrow(() -> new IllegalStateException(
                "Account not found: " + creditAccountCode));

        var debitLine = JournalLine.builder()
            .journalEntryId(entry.getId())
            .accountId(debitAccount.getId())
            .debitMinor(amountMinor)
            .creditMinor(0)
            .build();
        var creditLine = JournalLine.builder()
            .journalEntryId(entry.getId())
            .accountId(creditAccount.getId())
            .debitMinor(0)
            .creditMinor(amountMinor)
            .build();
        journalLineRepository.save(debitLine);
        journalLineRepository.save(creditLine);

        log.info("Posted {} entry id={} amount={} {} debit={} credit={}",
            entryType, entry.getId(), amountMinor, currency, debitAccountCode, creditAccountCode);

        return entry;
    }

    /**
     * Computes the current balance of an account (sum of debits - sum of credits).
     * For ASSET/EXPENSE accounts, debit increases balance.
     * For LIABILITY/REVENUE accounts, credit increases balance.
     */
    @Transactional(readOnly = true, isolation = Isolation.REPEATABLE_READ)
    public long computeBalance(UUID accountId) {
        var result = journalLineRepository.sumDebitsAndCredits(accountId);
        long debits = ((Number) result[0]).longValue();
        long credits = ((Number) result[1]).longValue();
        return debits - credits;
    }

    /**
     * Verifies the balance invariant (LED-001) across ALL journal entries:
     * total debits must equal total credits.
     *
     * <p>This is the method called by the invariant test INV-1 and by the
     * continuous reconciliation job.
     *
     * @return true if the ledger is balanced
     */
    @Transactional(readOnly = true, isolation = Isolation.REPEATABLE_READ)
    public boolean isLedgerBalanced() {
        var entries = journalEntryRepository.findAll();
        for (var entry : entries) {
            var lines = journalLineRepository.findByJournalEntryId(entry.getId());
            long debitSum = lines.stream().mapToLong(JournalLine::getDebitMinor).sum();
            long creditSum = lines.stream().mapToLong(JournalLine::getCreditMinor).sum();
            if (debitSum != creditSum) {
                log.error("LED-001 VIOLATION: entry {} debits={} credits={}",
                    entry.getId(), debitSum, creditSum);
                return false;
            }
        }
        return true;
    }

    // -----------------------------------------------------------------------
    // Retry wrapper for SERIALIZABLE isolation failures (SQLSTATE 40001)
    // -----------------------------------------------------------------------

    /**
     * Executes a ledger operation with SERIALIZABLE isolation and retries on
     * serialization conflicts. PostgreSQL reports these as SQLSTATE 40001,
     * which Spring translates to {@link ConcurrencyFailureException}.
     *
     * <p>Uses {@link TransactionTemplate} programmatically to guarantee the
     * SERIALIZABLE isolation level is actually applied. Annotating a lambda
     * method with {@code @Transactional} does NOT work because Spring's
     * proxy-based AOP only intercepts external calls — self-invocation through
     * a lambda bypasses the proxy and the transaction boundary.
     *
     * <p>The retry logic:
     * <ol>
     *   <li>Attempt the operation in a SERIALIZABLE, REQUIRES_NEW transaction</li>
     *   <li>If it fails with a concurrency exception, back off and retry</li>
     *   <li>After maxRetries, propagate the exception</li>
     * </ol>
     */
    private LedgerEntryResult executeWithRetry(LedgerOperation operation) {
        int maxRetries = properties.getLedger().getMaxRetries();
        long backoffMs = properties.getLedger().getRetryBackoffMs();

        var tt = new TransactionTemplate(transactionManager);
        tt.setIsolationLevel(TransactionDefinition.ISOLATION_SERIALIZABLE);
        tt.setPropagationBehavior(TransactionDefinition.PROPAGATION_REQUIRES_NEW);

        ConcurrencyFailureException lastException = null;
        for (int attempt = 0; attempt <= maxRetries; attempt++) {
            try {
                return tt.execute(status -> operation.execute());
            } catch (ConcurrencyFailureException e) {
                lastException = e;
                if (attempt < maxRetries) {
                    long sleep = backoffMs * (1L << attempt); // exponential backoff
                    log.warn("Serialization conflict on attempt {}/{}, retrying in {}ms: {}",
                        attempt + 1, maxRetries + 1, sleep, e.getMessage());
                    try {
                        Thread.sleep(sleep);
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        throw new RuntimeException("Interrupted during retry backoff", ie);
                    }
                }
            }
        }
        throw lastException != null ? lastException
            : new ConcurrencyFailureException("Max retries exceeded without specific exception");
    }

    @FunctionalInterface
    private interface LedgerOperation {
        LedgerEntryResult execute();
    }

    // -----------------------------------------------------------------------
    // Result mapping
    // -----------------------------------------------------------------------

    private LedgerEntryResult toResult(JournalEntry entry, long amountMinor) {
        return new LedgerEntryResult(
            entry.getId(),
            entry.getEntryType(),
            entry.getCurrency(),
            amountMinor,
            entry.getCreatedAt()
        );
    }

    public record LedgerEntryResult(
        UUID journalEntryId,
        EntryType entryType,
        String currency,
        long amountMinor,
        java.time.Instant createdAt
    ) {}
}
