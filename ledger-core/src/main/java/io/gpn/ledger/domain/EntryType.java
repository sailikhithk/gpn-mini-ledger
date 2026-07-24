package io.gpn.ledger.domain;

/**
 * Journal entry types representing the payment lifecycle.
 * Each type produces a specific double-entry pattern.
 */
public enum EntryType {
    /** Places a hold on customer funds (debit receivable, credit customer liability) */
    AUTH_HOLD,
    /** Converts a hold to settled funds (debit customer liability, credit revenue) */
    CAPTURE,
    /** Returns captured funds to customer (debit revenue, credit customer liability) */
    REFUND,
    /** Reverses an uncaptured authorization (debit customer liability, credit receivable) */
    REVERSAL,
    /** Voids an authorization before capture */
    VOID,
    /** Final settlement to the network */
    SETTLEMENT
}
