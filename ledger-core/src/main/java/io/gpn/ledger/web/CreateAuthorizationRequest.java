package io.gpn.ledger.web;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Builder;

import java.util.UUID;

/**
 * Request to place an authorization hold on customer funds.
 * The idempotency key is extracted by the API Gateway from the
 * {@code Idempotency-Key} header and injected here.
 */
@Builder
public record CreateAuthorizationRequest(
    @NotBlank String idempotencyKey,
    @NotNull UUID merchantId,
    @NotNull UUID authorizationId,
    @NotBlank String currency,
    @Min(1) long amountMinor
) {}
