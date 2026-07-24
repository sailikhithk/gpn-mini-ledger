# Changelog

All notable changes to this project are documented in this file grouped by feature area and date.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Index

| Version   | Date       | Feature Area                          | Summary                                                      |
| --------- | ---------- | ------------------------------------- | ------------------------------------------------------------ |
| 0.1.0     | 2026-07-23 | Project scaffold                      | Multi-module Maven + Spring Boot 4.1 + Java 25 baseline      |
| 0.2.0     | 2026-07-23 | Database schema (Flyway)              | V1-V3 migrations: ledger, edge, audit, async schemas         |
| 0.3.0     | 2026-07-23 | Domain model                          | JPA entities for accounts, journal entries, auth holds       |
| 0.4.0     | 2026-07-23 | Core ledger service                   | SERIALIZABLE double-entry bookkeeping with retry on 40001    |
| 0.5.0     | 2026-07-23 | REST API                              | Authorization, capture, refund endpoints                     |
| 0.6.0     | 2026-07-23 | Invariant test (INV-1)                | 20-thread concurrent capture proof of LED-001 + PAY-001      |
| 0.6.1     | 2026-07-23 | Bugfix: Testcontainers Docker API     | Resolve `client version 1.32 is too old` via docker-java cfg |
| 0.6.2     | 2026-07-23 | Bugfix: Flyway migrations             | Add `CREATE SCHEMA`, UUID v7 function, conditional roles     |
| 0.6.3     | 2026-07-23 | Bugfix: Jackson 3 binding             | Remove incompatible `spring.jackson.serialization` config    |
| 0.7.0     | 2026-07-23 | Bugfix: Transaction isolation bypass  | Replace self-invoked `@Transactional` with `TransactionTemplate` |
| 0.8.0     | 2026-07-24 | CI/CD + pre-commit + docs             | GitHub Actions, pre-commit hooks, CONTRIBUTING, Copilot review |

---

## [0.8.0] — 2026-07-24 — CI/CD + pre-commit + docs

### Added — GitHub Actions (7 workflows, mirrors DMS pipeline)
- `ci.yml` (Gate 3-5): compile + test + package on JDK 25, uploads surefire reports.
- `pr-lint.yml` (W1): validates PR title follows Conventional Commits, non-empty body.
- `migration-check.yml` (Gate 2): 6 Flyway checks — naming, sequencing, idempotency,
  dollar-quoting, append-only, conditional roles.
- `labeler.yml` (W3): file-based + size labels on PRs (module, area, size:xs..xl).
- `copilot-review.yml` (AI-assist): auto-requests Copilot code review on PR open to `main`.
  Advisory only — human approval still required (DMS lesson: no rubber-stamping).
- `codeql.yml` (Security): GitHub CodeQL static analysis for Java, weekly cron.
- `release.yml` (Release): auto-detects new version in `CHANGELOG.md`, creates git tag
  `vX.Y.Z` + GitHub Release with extracted release notes.

### Added — Pre-commit hooks
- `.pre-commit-config.yaml` with 10 hooks: trailing-whitespace, end-of-file-fixer,
  check-yaml, check-merge-conflict, check-case-conflict, check-added-large-files,
  detect-private-key, sqlfluff-lint/fix (Flyway migrations), mvn-compile (local),
  env-leak-check (local, blocks `.env`/secrets).
- `scripts/pre-commit-env-check.sh` — secret detection in staged files.

### Added — Documentation
- `CONTRIBUTING.md`: commit message format (Conventional Commits), branching model,
  tag/release process, branch protection rules, Copilot review policy.
- `.github/CI-CD.md`: workflow index, pre-commit setup, branch protection, tags.

### Changed
- `CHANGELOG.md` index updated with 0.8.0 entry.

---

## [Unreleased] — 2026-07-24

### Documentation
- Added `CHANGELOG.md` with feature-grouped, dated commit history and index table.
- Added `LEARNINGS.md` documenting gotchas encountered and how to avoid them.

---

## [0.7.0] — 2026-07-23 — Bugfix: Transaction isolation bypass

### Fixed — Core ledger correctness
- **Self-invocation bypassed `@Transactional(SERIALIZABLE)`** in `LedgerService.executeWithRetry`.
  The `@Transactional` annotation on the `LedgerOperation` interface method was never applied
  because Spring's proxy-based AOP does not intercept self-invocation through a lambda. All 20
  concurrent capture threads ran in READ_COMMITTED, read `capturedMinor=0` simultaneously, and
  all succeeded — violating PAY-001.
- **Fix**: Replaced the annotation-based approach with a programmatic `TransactionTemplate`
  configured with `ISOLATION_SERIALIZABLE` + `PROPAGATION_REQUIRES_NEW`. The template executes
  inside the retry loop, so each retry attempt gets a fresh SERIALIZABLE transaction.
- **Result**: INV-1 now passes — exactly 10 captures succeed, 10 are rejected with
  `CaptureExceedsAuthorizationException`, `capturedMinor == 10000`, LED-001 holds.

### Changed
- `LedgerService` now depends on `PlatformTransactionManager` (constructor-injected).
- `LedgerOperation` interface simplified to a plain `Supplier`-style functional interface.

---

## [0.6.3] — 2026-07-23 — Bugfix: Jackson 3 binding

### Fixed — Spring Boot 4 / Jackson 3 compatibility
- Removed `spring.jackson.serialization.write-dates-as-timestamps: false` from `application.yml`.
  Spring Boot 4 ships Jackson 3 where `SerializationFeature` moved to `tools.jackson.databind`,
  and the relaxed binding from kebab-case `write-dates-as-timestamps` no longer resolves to the
  enum constant. This caused `BindException` at context startup, blocking the test.

---

## [0.6.2] — 2026-07-23 — Bugfix: Flyway migrations

### Fixed — Migration SQL
- **V1**: Added `CREATE SCHEMA IF NOT EXISTS ledger` — the migration referenced `ledger.*` tables
  without creating the schema first.
- **V1**: Added `CREATE EXTENSION IF NOT EXISTS "pgcrypto"` and a plpgsql `uuid_generate_v7()`
  function. PostgreSQL 16 has no native UUIDv7 generator; the function uses `gen_random_bytes()`
  for entropy and sets the version/variant nibbles per RFC 9562.
- **V1**: Changed dollar-quoting tags from `$$` to distinct tags (`$func$`, `$role$`) to avoid
  Flyway parsing errors on nested `DO` blocks.
- **V1**: Made `gpn` role creation conditional (`IF NOT EXISTS`) so migrations work in
  Testcontainers where only the superuser exists.
- **V2**: Added `CREATE SCHEMA IF NOT EXISTS edge` and `audit`.
- **V3**: Added `CREATE SCHEMA IF NOT EXISTS async` and switched `uuid_generate_v7()` calls to
  the schema-qualified `public.uuid_generate_v7()`.

---

## [0.6.1] — 2026-07-23 — Bugfix: Testcontainers Docker API

### Fixed — Docker environment detection
- Resolved `client version 1.32 is too old. Minimum supported API version is 1.40` error.
  Testcontainers' transitive `docker-java` client defaulted to API v1.32; Docker Desktop
  requires >=1.40.
- **Root cause**: `~/.testcontainers.properties` and POM `systemPropertyVariables` did not
  propagate to the forked surefire JVM. The `docker-java` client reads its own config file.
- **Fix**: Created `~/.docker-java.properties` with `DOCKER_API_VERSION=1.45`. docker-java
  reads this file directly on class load.
- Also pinned `testcontainers.version=1.21.3` and added `docker-java-bom 3.5.1` to parent
  `dependencyManagement` to ensure a compatible client version.

---

## [0.6.0] — 2026-07-23 — Invariant test (INV-1)

### Added — Concurrency proof
- `ConcurrentCaptureInvariantTest`: 20-thread concurrent capture against a single $100.00
  authorization. Asserts exactly 10 captures succeed, 10 are rejected with
  `CaptureExceedsAuthorizationException`, `capturedMinor == 10000` (PAY-001), and
  `isLedgerBalanced() == true` (LED-001).
- Uses Testcontainers `PostgreSQLContainer` (`postgres:16-alpine`) with Flyway migrations.
- Dynamic properties override `retry-backoff-ms=10` and `max-retries=5` for fast test runs.

---

## [0.5.0] — 2026-07-23 — REST API

### Added — Ledger endpoints
- `LedgerController` with `POST /api/v1/ledger/authorizations`, `POST /api/v1/ledger/captures`,
  `POST /api/v1/ledger/refunds`.
- Request DTOs: `CreateAuthorizationRequest`, `CaptureRequest`.
- Response DTO: `LedgerEntryResponse` (journal entry id, type, currency, amount, timestamp).
- `ChartOfAccountsInitializer` seeds the chart of accounts (`merchant_receivable`,
  `customer_liability`, `merchant_revenue`) on application startup.

---

## [0.4.0] — 2026-07-23 — Core ledger service

### Added — Double-entry bookkeeping engine
- `LedgerService` with `createAuthorizationHold`, `capture`, `refund` operations.
- SERIALIZABLE transaction isolation with exponential-backoff retry on SQLSTATE 40001
  (`ConcurrencyFailureException`).
- Idempotency: every operation checks `journal_entries.idempotency_key` inside the transaction;
  replays return the original result without side effects.
- PAY-001 enforcement: `capture` rejects if `capturedMinor + captureAmount > authorizedMinor`.
- LED-001 enforcement: `postDoubleEntry` posts balanced debit/credit legs by construction.
- `isLedgerBalanced()` verification method for continuous reconciliation.
- `LedgerProperties` configures `isolation`, `max-retries`, `retry-backoff-ms`.
- Domain exceptions: `CaptureExceedsAuthorizationException`, `RefundExceedsCapturedException`.

---

## [0.3.0] — 2026-07-23 — Domain model

### Added — JPA entities
- `Account` (chart of accounts: code, type, currency).
- `AccountType` enum (`ASSET`, `LIABILITY`, `REVENUE`, `EXPENSE`).
- `JournalEntry` (immutable header: idempotency key, entry type, reference id, currency).
- `JournalLine` (debit/credit leg: account, debit_minor, credit_minor).
- `EntryType` enum (`AUTH_HOLD`, `CAPTURE`, `REFUND`, `REVERSAL`, `VOID`, `SETTLEMENT`).
- `AuthorizationHold` (authorized/captured/refunded minor units, status).
- Spring Data JPA repositories for each entity.

---

## [0.2.0] — 2026-07-23 — Database schema (Flyway)

### Added — Migrations
- `V1__ledger_core_schema.sql`: `ledger` schema with `accounts`, `journal_entries`,
  `journal_lines`, `authorization_holds`. CHECK constraints enforce LED-001 (debit XOR credit
  per line) and PAY-001 (captured <= authorized, refunded <= captured). Append-only enforcement
  via `REVOKE UPDATE, DELETE`.
- `V2__edge_and_audit_schema.sql`: `edge.idempotency_records` (SHA-256 fingerprint, TTL) and
  `audit.audit_chain_entries` (SHA-256 hash chain with genesis entry).
- `V3__async_outbox_schema.sql`: `async.outbox_events` (transactional outbox with
  `SKIP LOCKED` claim index) and `async.reconciliation_cases` (fingerprinted dedup).

---

## [0.1.0] — 2026-07-23 — Project scaffold

### Added — Build & infrastructure
- Multi-module Maven project: `ledger-core`, `api-gateway`, `outbox`.
- Parent POM with Java 25, Spring Boot 4.1, Flyway, Testcontainers BOM, Lombok.
- `docker-compose.yml` for local Postgres + Redis.
- `infra/postgres/init.sql` for local development bootstrap.
- Maven wrapper (`mvnw` / `mvnw.cmd`).
- `.gitignore` covering `target/`, IDE files, and secrets (`.env`).
- `PRD.md` (product requirements) and `SRS.md` (software requirements specification).
