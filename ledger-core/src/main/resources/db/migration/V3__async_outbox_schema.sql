-- =============================================================================
-- V3__async_outbox_schema.sql
-- Layer 3 (BASE): Async Lane - transactional outbox + reconciliation
-- =============================================================================
-- Design (from sentinel-ledger/OutboxDispatchWorker.java):
--   1. Events written in same DB transaction as business write (atomic)
--   2. Claim uses SELECT ... FOR UPDATE SKIP LOCKED (no contention between workers)
--   3. Claim transaction commits BEFORE publishing (crash-safe)
--   4. Stale claims reclaimed by scheduled task after configurable timeout
--   5. Each event has fail_count for retry tracking
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS async;

CREATE TABLE async.outbox_events (
    id             UUID         PRIMARY KEY DEFAULT public.uuid_generate_v7(),
    aggregate_type VARCHAR(32)  NOT NULL,
    aggregate_id   UUID         NOT NULL,
    event_type     VARCHAR(64)  NOT NULL,
    payload        JSONB        NOT NULL,
    status         VARCHAR(16)  NOT NULL DEFAULT 'PENDING'
                     CHECK (status IN ('PENDING','CLAIMED','PUBLISHED','FAILED')),
    claimed_at     TIMESTAMPTZ,
    published_at   TIMESTAMPTZ,
    fail_count     INTEGER      NOT NULL DEFAULT 0,
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- Index for the SKIP LOCKED claim query
CREATE INDEX idx_outbox_status_claimed ON async.outbox_events (status, claimed_at)
    WHERE status IN ('PENDING','CLAIMED');

CREATE INDEX idx_outbox_aggregate ON async.outbox_events (aggregate_type, aggregate_id);

-- =============================================================================
-- Reconciliation cases (Layer 3)
-- Design (from merchant-payments-platform/ledger-design.md):
--   1. Continuous reconciliation, not nightly batch
--   2. Three checks: balance invariant, event reconciliation, external reconciliation
--   3. Fingerprinted dedup: same mismatch never creates two open cases
-- =============================================================================

CREATE TABLE async.reconciliation_cases (
    id          UUID         PRIMARY KEY DEFAULT public.uuid_generate_v7(),
    fingerprint VARCHAR(64)  NOT NULL,
    check_type  VARCHAR(32)  NOT NULL CHECK (check_type IN (
                    'BALANCE_INVARIANT','EVENT_RECONCILIATION','EXTERNAL_RECONCILIATION'
                )),
    status      VARCHAR(16)  NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','RESOLVED','IGNORED')),
    details     JSONB        NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ
);

-- Partial unique index: no two OPEN cases with the same fingerprint
-- This is the dedup mechanism (REC-001 invariant)
CREATE UNIQUE INDEX idx_recon_open_fingerprint
    ON async.reconciliation_cases (fingerprint)
    WHERE status = 'OPEN';

CREATE INDEX idx_recon_status ON async.reconciliation_cases (status);
