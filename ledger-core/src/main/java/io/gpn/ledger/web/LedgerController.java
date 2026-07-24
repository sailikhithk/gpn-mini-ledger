package io.gpn.ledger.web;

import io.gpn.ledger.service.CaptureExceedsAuthorizationException;
import io.gpn.ledger.service.LedgerService;
import io.gpn.ledger.service.RefundExceedsCapturedException;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;
import java.util.UUID;

/**
 * REST API for the core ledger (Layer 1, CP).
 *
 * <p>All endpoints accept an {@code Idempotency-Key} header. The API Gateway
 * extracts this and passes it through. The ledger service uses it to guarantee
 * exactly-once business effect.
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/ledger")
@RequiredArgsConstructor
public class LedgerController {

    private final LedgerService ledgerService;

    @PostMapping("/authorizations")
    public ResponseEntity<LedgerService.LedgerEntryResult> createAuthorization(
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @RequestBody CreateAuthorizationRequest request
    ) {
        log.info("Create authorization idem={} auth={} amount={}",
            idempotencyKey, request.authorizationId(), request.amountMinor());
        var result = ledgerService.createAuthorizationHold(
            idempotencyKey,
            request.authorizationId(),
            request.merchantId(),
            request.currency(),
            request.amountMinor()
        );
        return ResponseEntity.ok(result);
    }

    @PostMapping("/captures")
    public ResponseEntity<LedgerService.LedgerEntryResult> capture(
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @RequestBody CaptureRequest request
    ) {
        log.info("Capture idem={} auth={} amount={}",
            idempotencyKey, request.authorizationId(), request.amountMinor());
        var result = ledgerService.capture(
            idempotencyKey,
            request.authorizationId(),
            request.amountMinor()
        );
        return ResponseEntity.ok(result);
    }

    @PostMapping("/refunds")
    public ResponseEntity<LedgerService.LedgerEntryResult> refund(
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @RequestBody CaptureRequest request
    ) {
        log.info("Refund idem={} auth={} amount={}",
            idempotencyKey, request.authorizationId(), request.amountMinor());
        var result = ledgerService.refund(
            idempotencyKey,
            request.authorizationId(),
            request.amountMinor()
        );
        return ResponseEntity.ok(result);
    }

    @GetMapping("/accounts/{accountId}/balance")
    public ResponseEntity<Map<String, Object>> getBalance(@PathVariable UUID accountId) {
        long balance = ledgerService.computeBalance(accountId);
        return ResponseEntity.ok(Map.of("accountId", accountId, "balanceMinor", balance));
    }

    @GetMapping("/invariant/balanced")
    public ResponseEntity<Map<String, Object>> checkBalanceInvariant() {
        boolean balanced = ledgerService.isLedgerBalanced();
        return ResponseEntity.ok(Map.of(
            "invariant", "LED-001",
            "description", "sum of debits equals sum of credits for every entry",
            "satisfied", balanced
        ));
    }

    // -----------------------------------------------------------------------
    // Exception handlers
    // -----------------------------------------------------------------------

    @ExceptionHandler(CaptureExceedsAuthorizationException.class)
    public ResponseEntity<Map<String, Object>> handleCaptureExceeds(CaptureExceedsAuthorizationException e) {
        log.warn("PAY-001 violation: {}", e.getMessage());
        return ResponseEntity.status(HttpStatus.CONFLICT).body(Map.of(
            "error", "CAPTURE_EXCEEDS_AUTHORIZATION",
            "invariant", "PAY-001",
            "message", e.getMessage()
        ));
    }

    @ExceptionHandler(RefundExceedsCapturedException.class)
    public ResponseEntity<Map<String, Object>> handleRefundExceeds(RefundExceedsCapturedException e) {
        log.warn("Refund exceeds captured: {}", e.getMessage());
        return ResponseEntity.status(HttpStatus.CONFLICT).body(Map.of(
            "error", "REFUND_EXCEEDS_CAPTURED",
            "message", e.getMessage()
        ));
    }
}
