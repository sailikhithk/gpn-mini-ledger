# SRS: GPN Mini Ledger

## 1. Introduction

### 1.1 Purpose

This Software Requirements Specification defines the technical requirements for GPN Mini Ledger, a Java reference implementation of the GPN layered priority stack. It translates the PRD into testable, implementable requirements.

### 1.2 Scope

The system is a backend-only Spring Boot application with 8 modules, 5 invariant tests, and local emulator integration. It is a reference implementation, not a production payment system.

### 1.3 Definitions

| Term | Definition |
|------|-----------|
| GPN | Global Payments Network (Capital One's card payment infrastructure) |
| CP | Consistency + Partition tolerance (strong consistency, linearizable) |
| AP | Availability + Partition tolerance (idempotent, eventually consistent) |
| BASE | Basically Available, Soft state, Eventual consistency |
| Ledger | Append-only double-entry accounting system |
| Idempotency key | Client-generated UUID v7 that uniquely identifies a business operation |
| Outbox | Transactional table that stores events to be published asynchronously |
| Saga | Sequence of local transactions with compensating actions on failure |
| Advisory lock | PostgreSQL session-level lock used to serialize access without table locks |
| SKIP LOCKED | PostgreSQL row-level lock clause that skips locked rows instead of waiting |
| Invariant | A property that must always hold, provable by test |

### 1.4 References

- `reference-repos-analysis.md` (12 patterns with source line references)
- `sentinel-ledger/docs/INVARIANTS.md` (22 invariants with proof levels)
- `merchant-payments-platform/ledger-design.md` (ledger design principles)
- `aether-ledger/src/main/java/com/aetherledger/service/IdempotencyService.java`
- `aether-ledger/src/main/java/com/aetherledger/service/AuditChainService.java`
- `sentinel-ledger/src/main/java/io/github/vinicius/sentinel/outbox/internal/OutboxDispatchWorker.java`
- `merchant-payments-platform/PaymentOrchestrator.java`
- `merchant-payments-platform/LedgerService.java`

## 2. Functional Requirements

### FR-1: Ledger Core (Layer 1, CP)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1.1 | The system shall implement double-entry bookkeeping where every journal entry has equal debits and credits | MUST |
| FR-1.2 | The system shall store all monetary amounts as signed 64-bit integers in minor units (cents) | MUST |
| FR-1.3 | The system shall enforce SERIALIZABLE isolation on all ledger writes | MUST |
| FR-1.4 | The system shall retry on serialization failure (SQLSTATE 40001) up to 3 times with exponential backoff | MUST |
| FR-1.5 | The system shall support account types: ASSET, LIABILITY, REVENUE, EXPENSE | MUST |
| FR-1.6 | The system shall implement createAuthorizationHold, capture, refund operations | MUST |
| FR-1.7 | The system shall validate that total capture for an authorization never exceeds the authorized amount | MUST |
| FR-1.8 | The system shall validate that refund total never exceeds captured total | MUST |
| FR-1.9 | The ledger shall be append-only. No UPDATE or DELETE on journal entries or journal lines | MUST |
| FR-1.10 | The system shall publish a `journal.entry.posted` event to the outbox for every successful write | MUST |

### FR-2: Idempotency (Layer 2, AP)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-2.1 | The system shall accept an `Idempotency-Key` HTTP header on all mutating endpoints | MUST |
| FR-2.2 | The system shall compute a SHA-256 fingerprint of the request body | MUST |
| FR-2.3 | The system shall reject with 409 if the key exists but the fingerprint differs | MUST |
| FR-2.4 | The system shall return the cached response if the key exists and the fingerprint matches | MUST |
| FR-2.5 | The system shall store the idempotency record in a REQUIRES_NEW transaction | MUST |
| FR-2.6 | The system shall use Redis as a fast-path cache with 72-hour TTL | MUST |
| FR-2.7 | The system shall use PostgreSQL as the durable store with a unique constraint on the key | MUST |
| FR-2.8 | The system shall silently swallow DataIntegrityViolationException on concurrent writes | MUST |
| FR-2.9 | The system shall use UUID v7 for time-ordered idempotency keys | SHOULD |

### FR-3: Outbox (Layer 3, BASE)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-3.1 | The system shall write outbox events in the same database transaction as the business write | MUST |
| FR-3.2 | The system shall use `SELECT ... FOR UPDATE SKIP LOCKED` to claim a batch of events | MUST |
| FR-3.3 | The system shall commit the claim transaction before publishing | MUST |
| FR-3.4 | The system shall publish each event in its own REQUIRES_NEW transaction | MUST |
| FR-3.5 | The system shall mark events as published or failed after publish attempt | MUST |
| FR-3.6 | The system shall reclaim stale claims (events claimed but not marked) after a configurable timeout | MUST |
| FR-3.7 | The system shall run the relay as a scheduled task with a configurable poll interval | MUST |
| FR-3.8 | The system shall expose metrics: published count, failed count, stale reclaimed count, by event type | SHOULD |

### FR-4: Audit Chain (Layer 1, CP)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-4.1 | The system shall maintain a tamper-evident SHA-256 hash chain for all audit events | MUST |
| FR-4.2 | Each audit entry's hash shall be computed from: sequence number, event type, entity type, entity ID, payload hash, previous hash | MUST |
| FR-4.3 | The genesis entry shall use the literal string "GENESIS" as the previous hash | MUST |
| FR-4.4 | The system shall serialize all chain writes using a PostgreSQL transaction-scoped advisory lock | MUST |
| FR-4.5 | The system shall provide a `verifyChain()` method that re-derives hashes and detects tampering | MUST |
| FR-4.6 | `verifyChain()` shall return the sequence number where the chain breaks, or 0 if valid | MUST |
| FR-4.7 | The system shall store audit entries in a separate schema from operational data | SHOULD |

### FR-5: Orchestrator (Layer 2, AP)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-5.1 | The system shall orchestrate payment authorization as a saga with explicit steps | MUST |
| FR-5.2 | The saga steps shall be: idempotency check, fraud scoring, authorization decision, card network auth, ledger hold, event emission | MUST |
| FR-5.3 | If the ledger hold fails after card network auth, the system shall reverse the authorization | MUST |
| FR-5.4 | If the reversal fails, the system shall publish to a dead-letter queue for manual intervention | MUST |
| FR-5.5 | The system shall use virtual threads for I/O-bound gRPC or HTTP calls in the saga | MUST |
| FR-5.6 | The system shall enforce a 50ms timeout on the fraud scoring call | MUST |
| FR-5.7 | The system shall emit a `fraud.degraded` metric when the fraud engine is unavailable | SHOULD |

### FR-6: Fraud Degradation (Layer 2, AP)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-6.1 | The system shall apply a configurable degradation policy per merchant risk tier when the fraud engine is unavailable | MUST |
| FR-6.2 | The system shall never fail-open (approve by default) for high-risk merchants | MUST |
| FR-6.3 | The system shall fail-open only for low-risk merchants below a configurable threshold | MAY |
| FR-6.4 | The system shall log every degradation decision with the merchant tier and applied policy | MUST |
| FR-6.5 | The degradation policy shall be: LOW risk = approve, MEDIUM risk = approve with manual review, HIGH risk = decline | SHOULD |

### FR-7: Reconciliation (Layer 3, BASE)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-7.1 | The system shall run continuous reconciliation, not nightly batch | MUST |
| FR-7.2 | The system shall perform three checks: balance invariant, event reconciliation (outbox to ledger), external reconciliation (ledger to network) | MUST |
| FR-7.3 | The system shall create a reconciliation case for each mismatch | MUST |
| FR-7.4 | The system shall fingerprint each case by a deterministic hash of the mismatch details | MUST |
| FR-7.5 | The system shall not create a duplicate open case for the same fingerprint | MUST |
| FR-7.6 | The system shall expose metrics: open cases, closed cases, cases by type | SHOULD |

### FR-8: Webhook (Layer 3, BASE)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-8.1 | The system shall sign every webhook with HMAC-SHA256 using a per-merchant secret | MUST |
| FR-8.2 | The signature header shall include a timestamp to prevent replay | MUST |
| FR-8.3 | The system shall reject webhooks where the timestamp is older than 5 minutes | MUST |
| FR-8.4 | The system shall retry failed webhook deliveries with exponential backoff | MUST |
| FR-8.5 | After 5 failed attempts, the system shall move the webhook to a dead-letter queue | MUST |
| FR-8.6 | The system shall deduplicate webhook deliveries by outbox event ID | MUST |

## 3. Non-Functional Requirements

### NFR-1: Performance

| ID | Requirement |
|----|-------------|
| NFR-1.1 | The ledger write path (journal entry + outbox event in one transaction) shall complete in under 50ms at p99 with 100 concurrent writers |
| NFR-1.2 | The idempotency fast path (Redis hit) shall complete in under 2ms at p99 |
| NFR-1.3 | The outbox relay shall process at least 1000 events per second per worker |
| NFR-1.4 | The fraud scoring call shall have a 50ms timeout |

### NFR-2: Correctness

| ID | Requirement |
|----|-------------|
| NFR-2.1 | The balance invariant (sum of debits = sum of credits) shall hold under 20-thread concurrent capture |
| NFR-2.2 | Exactly-once business effect: 100 same-key submits shall produce exactly one ledger entry |
| NFR-2.3 | At-least-once outbox delivery: no event shall be lost after a worker crash |
| NFR-2.4 | Tamper detection: any manual modification of an audit entry shall be detected by verifyChain() |
| NFR-2.5 | No duplicate reconciliation cases for the same mismatch |

### NFR-3: Operability

| ID | Requirement |
|----|-------------|
| NFR-3.1 | The system shall expose health checks via Spring Actuator |
| NFR-3.2 | The system shall expose Micrometer metrics for all critical paths |
| NFR-3.3 | The system shall use structured JSON logging with MDC trace IDs |
| NFR-3.4 | The system shall never hold a database transaction open across a network call |

### NFR-4: Portability

| ID | Requirement |
|----|-------------|
| NFR-4.1 | The system shall run on any machine with Docker and JDK 25 |
| NFR-4.2 | The system shall require zero cloud accounts (no AWS, no Azure) |
| NFR-4.3 | The system shall start all dependencies via `docker compose up -d` |

### NFR-5: Maintainability

| ID | Requirement |
|----|-------------|
| NFR-5.1 | Each module shall be under 500 lines of production code |
| NFR-5.2 | The test-to-production code ratio shall be at least 0.8 |
| NFR-5.3 | Every public service method shall have a Javadoc comment |
| NFR-5.4 | Every invariant test shall reference the invariant ID it proves |

## 4. Invariant Tests (graded proof levels)

Following the `sentinel-ledger/INVARIANTS.md` framework.

| Test ID | Invariant | Proof level | What the test does |
|---------|-----------|-------------|-------------------|
| INV-1 | PAY-001: capture never exceeds authorized | Concurrency | 20 threads concurrently capture the same authorization. Assert sum of captures equals authorized amount, no thread sees a stale balance. |
| INV-2 | IDEM-001: exactly-once business effect | Persistence | Submit the same payment 100 times with the same idempotency key. Assert exactly one journal entry, 99 cached 201 responses. |
| INV-3 | OUT-002: at-least-once with no lost events | Recovery | Start relay, publish 10 events, kill relay after event 5 is claimed. Assert events 1-4 are published, 5-10 are unpublished. Restart relay. Assert all 10 are published. |
| INV-4 | AUD-001: tamper-evident log | Domain | Insert 5 audit entries. Manually UPDATE entry 3's payload. Assert verifyChain() returns valid=false with breakAtSeq=3. |
| INV-5 | REC-001: no duplicate open cases | Persistence | Inject a missing ledger entry. Run reconciliation. Assert one case created. Run reconciliation again. Assert no second case (same fingerprint). |

## 5. Data Model

### 5.1 accounts

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| code | VARCHAR(32) | UNIQUE NOT NULL |
| type | VARCHAR(16) | NOT NULL (ASSET, LIABILITY, REVENUE, EXPENSE) |
| currency | VARCHAR(3) | NOT NULL (ISO 4217) |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |

### 5.2 journal_entries

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| idempotency_key | VARCHAR(64) | UNIQUE NOT NULL |
| entry_type | VARCHAR(32) | NOT NULL (AUTH_HOLD, CAPTURE, REFUND, REVERSAL) |
| reference_id | UUID | NOT NULL (the authorization this relates to) |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |

### 5.3 journal_lines

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| journal_entry_id | UUID | FK NOT NULL |
| account_id | UUID | FK NOT NULL |
| debit_minor | BIGINT | NOT NULL DEFAULT 0 |
| credit_minor | BIGINT | NOT NULL DEFAULT 0 |
| CHECK | (debit_minor >= 0 AND credit_minor >= 0 AND (debit_minor = 0 OR credit_minor = 0)) |

### 5.4 idempotency_records

| Column | Type | Constraints |
|--------|------|-------------|
| key | VARCHAR(64) | PK |
| request_fingerprint | VARCHAR(64) | NOT NULL |
| response_status | INT | NOT NULL |
| response_body | JSONB | NOT NULL |
| expires_at | TIMESTAMPTZ | NOT NULL |

### 5.5 outbox_events

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| aggregate_type | VARCHAR(32) | NOT NULL |
| aggregate_id | UUID | NOT NULL |
| event_type | VARCHAR(64) | NOT NULL |
| payload | JSONB | NOT NULL |
| status | VARCHAR(16) | NOT NULL DEFAULT 'PENDING' |
| claimed_at | TIMESTAMPTZ | NULL |
| published_at | TIMESTAMPTZ | NULL |
| fail_count | INT | NOT NULL DEFAULT 0 |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |

### 5.6 audit_chain_entries

| Column | Type | Constraints |
|--------|------|-------------|
| seq | BIGSERIAL | PK |
| event_type | VARCHAR(32) | NOT NULL |
| entity_type | VARCHAR(32) | NOT NULL |
| entity_id | UUID | NOT NULL |
| payload_hash | VARCHAR(64) | NOT NULL |
| previous_hash | VARCHAR(64) | NOT NULL |
| current_hash | VARCHAR(64) | NOT NULL UNIQUE |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |

### 5.7 reconciliation_cases

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| fingerprint | VARCHAR(64) | NOT NULL |
| check_type | VARCHAR(32) | NOT NULL |
| status | VARCHAR(16) | NOT NULL DEFAULT 'OPEN' |
| details | JSONB | NOT NULL |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |
| resolved_at | TIMESTAMPTZ | NULL |
| UNIQUE | (fingerprint, status) WHERE status = 'OPEN' |

## 6. API Surface

### 6.1 POST /payments/authorize

Request:
```json
{
  "merchant_id": "uuid",
  "amount_minor": 10000,
  "currency": "USD",
  "card_token": "tok_xxx",
  "idempotency_key": "uuid-v7"
}
```

Response 201:
```json
{
  "authorization_id": "uuid",
  "status": "AUTHORIZED",
  "amount_minor": 10000,
  "currency": "USD"
}
```

Headers: `Idempotency-Key: <uuid-v7>`

### 6.2 POST /payments/{id}/capture

Request:
```json
{
  "amount_minor": 10000,
  "idempotency_key": "uuid-v7"
}
```

### 6.3 POST /payments/{id}/refund

Request:
```json
{
  "amount_minor": 5000,
  "idempotency_key": "uuid-v7"
}
```

### 6.4 GET /audit/verify

Response 200:
```json
{
  "valid": true,
  "break_at_seq": 0,
  "entries_checked": 42
}
```

### 6.5 GET /reconciliation/cases

Response 200:
```json
{
  "open_cases": 2,
  "cases": [...]
}
```

## 7. Technology Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Java version | 25 | Current LTS, matches `sentinel-ledger`, virtual threads mature |
| Framework | Spring Boot 4.1 | Current, matches `sentinel-ledger` |
| Build | Maven | Matches Capital One and Lilly DMS stack |
| Core DB | PostgreSQL 16 | SERIALIZABLE, advisory locks, SKIP LOCKED, JSONB |
| Fast path | Redis 7 | Idempotency cache, TTL |
| Event bus | Redpanda | Kafka-compatible, single binary, no ZooKeeper |
| AWS local | LocalStack | S3, SQS, DynamoDB without AWS account |
| Migrations | Flyway | Matches Lilly DMS, industry standard |
| Tests | JUnit 5 + Testcontainers | Real Postgres/Redis/Redpanda in tests |
| Money type | long (minor units) | No floating point, matches `LedgerService.java` |
| ID type | UUID v7 | Time-ordered, matches `merchant-payments-platform` |
| Isolation | SERIALIZABLE | Matches `LedgerService.java`, prevents lost updates |
| Outbox claim | SKIP LOCKED | Matches `sentinel-ledger/OutboxDispatchWorker.java` |
| Audit serialization | Advisory lock | Matches `aether-ledger/AuditChainService.java` |

## 8. Constraints

| ID | Constraint |
|----|-----------|
| CON-1 | No floating point for money. All amounts in minor units as long. |
| CON-2 | No UPDATE or DELETE on journal_entries or journal_lines. Append-only. |
| CON-3 | No network call inside a database transaction. |
| CON-4 | No fail-open for high-risk merchants. |
| CON-5 | No event lost. Outbox + at-least-once + idempotent consumers. |
| CON-6 | No silent audit tamper. Hash chain + verifyChain(). |
| CON-7 | No duplicate reconciliation cases. Fingerprint + partial unique index. |
| CON-8 | No cloud spend. All emulators local. |

## 9. Assumptions

1. The developer has Docker installed and running.
2. The developer has JDK 25 installed (or uses the Docker build).
3. The reviewer has 10 minutes to clone and verify.
4. The interviewer is a Capital One GPN engineer who understands the priority stack.
5. The system is not under real production load. Performance NFRs are for a single machine.

## 10. Dependencies

| Dependency | Version | Scope |
|------------|---------|-------|
| spring-boot-starter-web | 4.1.0 | compile |
| spring-boot-starter-data-jpa | 4.1.0 | compile |
| spring-boot-starter-validation | 4.1.0 | compile |
| spring-boot-starter-actuator | 4.1.0 | compile |
| spring-boot-starter-data-redis | 4.1.0 | compile |
| spring-boot-starter-flyway | 4.1.0 | compile |
| flyway-database-postgresql | 10.x | compile |
| postgresql | 42.x | runtime |
| lombok | latest | provided |
| testcontainers-junit-jupiter | 1.20+ | test |
| testcontainers-postgresql | 1.20+ | test |
| testcontainers-redis | 1.20+ | test |
| testcontainers-redpanda | 1.20+ | test |
| testcontainers-localstack | 1.20+ | test |
| spring-boot-starter-test | 4.1.0 | test |

## 11. Build and Run

### 11.1 Prerequisites

- JDK 25
- Docker
- Maven 3.9+ (or use `./mvnw`)

### 11.2 Start dependencies

```bash
docker compose up -d
```

Starts: PostgreSQL 16, Redis 7, Redpanda, LocalStack.

### 11.3 Run tests

```bash
./mvnw verify
```

Runs all unit tests and Testcontainers integration tests, including the 5 invariant tests.

### 11.4 Run the app

```bash
./mvnw spring-boot:run
```

### 11.5 Verify invariants manually

```bash
curl http://localhost:8080/audit/verify
curl http://localhost:8080/reconciliation/cases
```

## 12. Module Dependency Graph

```
orchestrator (Layer 2)
  ├── idempotency (Layer 2)
  ├── fraud-degradation (Layer 2)
  ├── ledger-core (Layer 1)
  │     └── audit-chain (Layer 1)
  └── outbox (Layer 3)
        ├── reconciliation (Layer 3)
        └── webhook (Layer 3)
```

The orchestrator is the only module that depends on all others. Each other module depends only on its own schema and Spring Boot starters. This keeps the dependency graph shallow and testable in isolation.

## 13. Test Strategy

| Level | What | How many |
|-------|------|----------|
| Unit | Service logic with mocked repos | ~30 |
| Integration | Testcontainers with real Postgres/Redis/Redpanda | ~15 |
| Invariant | Graded proof tests (the 5) | 5 |
| Contract | API contract tests with RestAssured | ~10 |

Total: ~60 tests. Test-to-production ratio target: >= 0.8.

## 14. Acceptance Criteria

The project is "done" when:

1. `./mvnw verify` passes with 0 failures
2. All 5 invariant tests pass
3. All 12 patterns are implemented and documented in PATTERNS.md with source line refs
4. README.md is present and renders correctly on GitHub
5. `docker compose up -d && ./mvnw verify` works on a fresh clone
6. No cloud account is required
7. Java 25 and Spring Boot 4.1 are in `pom.xml`
8. Each module is under 500 LOC of production code
