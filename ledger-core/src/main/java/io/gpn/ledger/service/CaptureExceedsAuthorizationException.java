package io.gpn.ledger.service;

import java.util.UUID;

/**
 * Thrown when a capture would exceed the authorized amount (PAY-001 violation).
 */
public class CaptureExceedsAuthorizationException extends RuntimeException {
    public CaptureExceedsAuthorizationException(UUID authorizationId, long authorized, long alreadyCaptured, long requested) {
        super(String.format(
            "Capture of %d would exceed authorized amount %d for authorization %s (already captured: %d)",
            requested, authorized, authorizationId, alreadyCaptured));
    }
}
