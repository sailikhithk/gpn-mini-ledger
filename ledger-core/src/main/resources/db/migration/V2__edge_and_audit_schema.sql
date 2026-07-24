-- =============================================================================
-- V2__edge_idempotency_schema.sql
-- Layer 2 (AP): Edge Switch - idempotency records
-- =============================================================================
-- Design (from aether-ledger/IdempotencyService.java):
--   1. SHA-256 fingerprint of request body detects "same key, different body" conflicts
--   2. REQUIRES_NEW transaction ensures the record is visible to retries regardless
--      of the caller's transaction outcome
--   3. Unique constraint on key is the final guard against duplicate writes
--   4. TTL via expires_at (72 hours default)
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS edge;
CREATE SCHEMA IF NOT EXISTS audit;

CREATE TABLE edge.idempotency_records (
    key                VARCHAR(64)  PRIMARY KEY,
    request_fingerprint VARCHAR(64)  NOT NULL,
    response_status    INTEGER      NOT NULL,
    response_body      JSONB        NOT NULL,
    expires_at         TIMESTAMPTZ  NOT NULL,
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_idem_expires ON edge.idempotency_records (expires_at);

-- =============================================================================
-- V2 also creates the audit chain schema (Layer 1, CP)
-- Design (from aether-ledger/AuditChainService.java):
--   1. SHA-256 hash chain: current_hash = SHA256(seq || event_type || entity_type
--      || entity_id || payload_hash || previous_hash)
--   2. Genesis entry uses literal "GENESIS" as previous_hash
--   3. PostgreSQL advisory lock serializes all writes (prevents sequence gaps)
--   4. verifyChain() re-derives hashes to detect tampering
-- =============================================================================

CREATE TABLE audit.audit_chain_entries (
    seq          BIGSERIAL    PRIMARY KEY,
    event_type   VARCHAR(32)  NOT NULL,
    entity_type  VARCHAR(32)  NOT NULL,
    entity_id    UUID         NOT NULL,
    payload_hash VARCHAR(64)  NOT NULL,
    previous_hash VARCHAR(64) NOT NULL,
    current_hash  VARCHAR(64) NOT NULL UNIQUE,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_entity ON audit.audit_chain_entries (entity_type, entity_id);
CREATE INDEX idx_audit_seq    ON audit.audit_chain_entries (seq);

-- Append-only: audit chain can never be updated or deleted
REVOKE UPDATE, DELETE ON audit.audit_chain_entries FROM gpn;
GRANT SELECT, INSERT ON audit.audit_chain_entries TO gpn;
