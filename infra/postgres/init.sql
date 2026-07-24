-- GPN Mini Ledger - PostgreSQL initialization
-- Runs on first container start only

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Create schemas for layer separation
CREATE SCHEMA IF NOT EXISTS ledger;       -- Layer 1: Core Ledger (CP)
CREATE SCHEMA IF NOT EXISTS edge;         -- Layer 2: Edge Switch (AP)
CREATE SCHEMA IF NOT EXISTS async;        -- Layer 3: Async Lane (BASE)
CREATE SCHEMA IF NOT EXISTS audit;        -- Layer 1: Audit chain (CP)

-- Grant full access to the app user
GRANT USAGE ON SCHEMA ledger, edge, async, audit TO gpn;
GRANT CREATE ON SCHEMA ledger, edge, async, audit TO gpn;
