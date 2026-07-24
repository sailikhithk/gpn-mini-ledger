package io.gpn.ledger.service;

import java.util.UUID;

/**
 * Thrown when a refund would exceed the captured amount.
 */
public class RefundExceedsCapturedException extends RuntimeException {
    public RefundExceedsCapturedException(UUID authorizationId, long captured, long alreadyRefunded, long requested) {
        super(String.format(
            "Refund of %d would exceed captured amount %d for authorization %s (already refunded: %d)",
            requested, captured, authorizationId, alreadyRefunded));
    }
}
