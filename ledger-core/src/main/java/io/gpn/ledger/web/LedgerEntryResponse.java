package io.gpn.ledger.web;

import lombok.Builder;

import java.time.Instant;
import java.util.UUID;

@Builder
public record LedgerEntryResponse(
    UUID journalEntryId,
    String entryType,
    String currency,
    long amountMinor,
    Instant createdAt
) {}
