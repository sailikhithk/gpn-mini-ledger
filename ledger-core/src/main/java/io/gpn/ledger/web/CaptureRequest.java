package io.gpn.ledger.web;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Builder;

import java.util.UUID;

@Builder
public record CaptureRequest(
    @NotBlank String idempotencyKey,
    @NotNull UUID authorizationId,
    @Min(1) long amountMinor
) {}
