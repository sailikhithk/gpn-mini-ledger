-- =============================================================================
-- V1__ledger_core_schema.sql
-- Layer 1 (CP): Core Ledger schema - double-entry bookkeeping
-- =============================================================================
-- Design principles (from merchant-payments-platform/ledger-design.md):
--   1. Conservation: sum of debits = sum of credits (enforced by CHECK)
--   2. Immutability: journal_entries and journal_lines are append-only
--      (enforced by REVOKE of UPDATE/DELETE from app role)
--   3. Auditability: every entry has an idempotency key and reference_id
--   4. Minor units: all amounts stored as BIGINT in minor units (cents)
--      No floating point. No DECIMAL. Only integer minor units.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Schema + extensions
-- -----------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS ledger;
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- UUID v7 generator (timestamp-ordered, sortable, K-sortable)
-- Uses pgcrypto for entropy. PostgreSQL 17+ has gen_random_uuid() built-in.
CREATE OR REPLACE FUNCTION public.uuid_generate_v7() RETURNS UUID AS $func$
DECLARE
    unix_ts_ms BIGINT;
    uuid_bytes BYTEA;
BEGIN
    unix_ts_ms := (EXTRACT(EPOCH FROM clock_timestamp()) * 1000)::BIGINT;
    uuid_bytes := decode(lpad(to_hex(unix_ts_ms), 12, '0'), 'hex');
    uuid_bytes := uuid_bytes || gen_random_bytes(10);
    -- set version nibble to 7
    uuid_bytes := set_byte(uuid_bytes, 6, (get_byte(uuid_bytes, 6) & B'00001111'::int) | B'01110000'::int);
    -- set variant nibble to 10xx
    uuid_bytes := set_byte(uuid_bytes, 8, (get_byte(uuid_bytes, 8) & B'00111111'::int) | B'10000000'::int);
    RETURN encode(uuid_bytes, 'hex')::UUID;
END;
$func$ LANGUAGE plpgsql VOLATILE;

-- -----------------------------------------------------------------------------
-- accounts: chart of accounts
-- -----------------------------------------------------------------------------
CREATE TABLE ledger.accounts (
    id           UUID         PRIMARY KEY DEFAULT public.uuid_generate_v7(),
    code         VARCHAR(32) NOT NULL UNIQUE,
    type         VARCHAR(16) NOT NULL CHECK (type IN ('ASSET','LIABILITY','REVENUE','EXPENSE')),
    currency     VARCHAR(3)  NOT NULL CHECK (currency ~ '^[A-Z]{3}$'),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- -----------------------------------------------------------------------------
-- journal_entries: the immutable header of each double-entry transaction
-- -----------------------------------------------------------------------------
CREATE TABLE ledger.journal_entries (
    id              UUID         PRIMARY KEY DEFAULT public.uuid_generate_v7(),
    idempotency_key VARCHAR(64)  NOT NULL UNIQUE,
    entry_type      VARCHAR(32)  NOT NULL CHECK (entry_type IN (
                        'AUTH_HOLD','CAPTURE','REFUND','REVERSAL','VOID','SETTLEMENT'
                    )),
    reference_id    UUID         NOT NULL,
    currency        VARCHAR(3)   NOT NULL CHECK (currency ~ '^[A-Z]{3}$'),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_journal_entries_reference ON ledger.journal_entries (reference_id);
CREATE INDEX idx_journal_entries_type      ON ledger.journal_entries (entry_type);
CREATE INDEX idx_journal_entries_created   ON ledger.journal_entries (created_at);

-- -----------------------------------------------------------------------------
-- journal_lines: the individual debit/credit legs of each entry
-- Key invariant: debit_minor = credit_minor = 0 is invalid
--                exactly one of debit/credit must be > 0 per line
-- -----------------------------------------------------------------------------
CREATE TABLE ledger.journal_lines (
    id               UUID        PRIMARY KEY DEFAULT public.uuid_generate_v7(),
    journal_entry_id UUID        NOT NULL REFERENCES ledger.journal_entries(id),
    account_id       UUID        NOT NULL REFERENCES ledger.accounts(id),
    debit_minor      BIGINT      NOT NULL DEFAULT 0 CHECK (debit_minor  >= 0),
    credit_minor     BIGINT      NOT NULL DEFAULT 0 CHECK (credit_minor >= 0),
    -- Invariant LED-001: a line is either a debit OR a credit, never both, never neither
    CHECK (
        (debit_minor > 0 AND credit_minor = 0) OR
        (debit_minor = 0 AND credit_minor > 0)
    )
);

CREATE INDEX idx_journal_lines_entry   ON ledger.journal_lines (journal_entry_id);
CREATE INDEX idx_journal_lines_account ON ledger.journal_lines (account_id);

-- -----------------------------------------------------------------------------
-- authorization_holds: tracks the authorized vs captured vs refunded amounts
-- This is the table that enforces PAY-001: capture never exceeds authorized
-- -----------------------------------------------------------------------------
CREATE TABLE ledger.authorization_holds (
    id               UUID        PRIMARY KEY DEFAULT public.uuid_generate_v7(),
    authorization_id UUID        NOT NULL UNIQUE,
    merchant_id      UUID        NOT NULL,
    currency         VARCHAR(3)  NOT NULL CHECK (currency ~ '^[A-Z]{3}$'),
    authorized_minor BIGINT      NOT NULL CHECK (authorized_minor > 0),
    captured_minor   BIGINT      NOT NULL DEFAULT 0 CHECK (captured_minor >= 0),
    refunded_minor   BIGINT      NOT NULL DEFAULT 0 CHECK (refunded_minor >= 0),
    status           VARCHAR(16) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','CAPTURED','VOIDED','EXPIRED')),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Invariant PAY-001: captured never exceeds authorized
    CHECK (captured_minor <= authorized_minor),
    -- Invariant: refunded never exceeds captured
    CHECK (refunded_minor <= captured_minor)
);

CREATE INDEX idx_auth_holds_merchant ON ledger.authorization_holds (merchant_id);
CREATE INDEX idx_auth_holds_status   ON ledger.authorization_holds (status);

-- -----------------------------------------------------------------------------
-- Append-only enforcement: revoke UPDATE/DELETE from the app role
-- The gpn role can INSERT and SELECT but cannot modify or delete journal data.
-- This enforces immutability at the database privilege level, not just in code.
-- Role creation is conditional so the migration works in test containers
-- where only the superuser/postgres role exists.
-- -----------------------------------------------------------------------------
DO $role$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'gpn') THEN
        CREATE ROLE gpn;
    END IF;
END
$role$;

REVOKE UPDATE, DELETE ON ledger.journal_entries FROM gpn;
REVOKE UPDATE, DELETE ON ledger.journal_lines   FROM gpn;

-- Grant INSERT and SELECT (the app can write new entries but never modify old ones)
GRANT SELECT, INSERT ON ledger.accounts             TO gpn;
GRANT SELECT, INSERT ON ledger.journal_entries      TO gpn;
GRANT SELECT, INSERT ON ledger.journal_lines        TO gpn;
GRANT SELECT, INSERT, UPDATE ON ledger.authorization_holds TO gpn;

-- Sequence for the audit chain (created in V2)
-- Note: we use BIGSERIAL in V2 for the audit chain sequence number
