# PRD: GPN Mini Ledger

## 1. Problem Statement

Capital One's Global Payments Network (GPN) processes card transactions across a three-layer architecture: a CP core ledger, an AP edge switch, and a BASE async lane. System design interviews for GPN roles test whether candidates can articulate the priority stack, cite production patterns, and prove correctness under concurrency.

There is no publicly available Java reference implementation that demonstrates all 12 production payment patterns (double-entry ledger, two-layer idempotency, transactional outbox, tamper-evident audit chain, saga with compensation, fail-safe degradation, continuous reconciliation, signed webhooks) in a single runnable codebase with executable invariant tests.

## 2. Product Goal

A minimal but production-shaped GPN-style payment system in Java that:

1. Demonstrates the layered priority stack (CP core, AP edge, BASE async) in working code
2. Implements 12 production payment patterns, each mapped to a GPN layer
3. Includes 5 executable invariant tests at graded proof levels (Domain, Persistence, Concurrency, Recovery)
4. Runs 100% on local emulators (PostgreSQL, Redis, Redpanda, LocalStack), zero cloud cost
5. Can be cloned and verified by a Capital One interviewer in under 10 minutes

## 3. Target Users

| User | What they need from this repo |
|------|------------------------------|
| Capital One GPN interviewer | Proof the candidate can build what they describe in system design |
| Capital One recruiter | A GitHub artifact that demonstrates Java + payments depth |
| The candidate (Sai) | A citable reference during system design and behavioral rounds |
| Any payments engineer | A learning resource for production payment patterns |

## 4. Non-Goals

- Not a production payment system. No real card network integration, no PCI-DSS scope, no real money movement.
- Not a frontend. Backend only. A frontend would dilute the backend signal.
- Not a full GPN replica. GPN has hundreds of services. This has 8 modules.
- Not a Temporal-based system. Uses in-process saga orchestration to keep dependencies minimal. README will note Temporal as the production alternative.
- Not a microservices deployment. Single deployable JAR with module separation in code. README will note the microservices decomposition for production.

## 5. Success Metrics

| Metric | Target | How to measure |
|--------|--------|----------------|
| Invariant tests passing | 5 of 5 | `./mvnw verify` exits 0 |
| Patterns implemented | 12 of 12 | Code review against PATTERNS.md |
| Clone-to-verify time | Under 10 minutes | Fresh clone + `docker compose up` + `./mvnw verify` |
| Cloud cost | $0 | No AWS/Azure account required |
| Java version | 25 (current LTS) | `java -version` in build |
| Spring Boot version | 4.1 (current) | `pom.xml` parent version |
| Lines of test code vs production code | Ratio >= 0.8 | `cloc` output |
| README readability | A reader can explain the priority stack in 5 minutes | Peer review |

## 6. The Layered Priority Stack

This is the core framework the repo demonstrates. Every module maps to exactly one layer.

| Layer | Name | Consistency model | Priority stack | Modules |
|-------|------|-------------------|----------------|---------|
| 1 | Core Ledger | CP (strong, linearizable) | Correctness > Durability > Consistency > Auditability > Availability | `ledger-core`, `audit-chain` |
| 2 | Edge Switch | AP-leaning (idempotent, stateless) | Latency > Availability > Idempotency > Fail-safe | `idempotency`, `orchestrator`, `fraud-degradation` |
| 3 | Async Lane | BASE (eventual consistency) | Throughput > Durability > At-least-once > Reconciliation | `outbox`, `reconciliation`, `webhook` |

### Conflict decision framework

When two priorities conflict, the higher layer wins:

- Layer 1 vs Layer 2: Layer 1 wins. The edge switch may return 503, but the ledger never accepts an inconsistent write.
- Layer 2 vs Layer 3: Layer 2 wins. The edge switch may drop an event, but the outbox never blocks the request path.
- Within a layer: the leftmost priority in that layer's stack wins.

## 7. The 12 Patterns (mapped to GPN layers)

Each pattern is grounded in a real reference repository. Source line references are in `reference-repos-analysis.md`.

| # | Pattern | GPN layer | Source reference |
|---|---------|-----------|------------------|
| 1 | Double-entry bookkeeping with balance invariant | Layer 1 | `merchant-payments-platform/LedgerService.java` |
| 2 | SERIALIZABLE isolation for all ledger writes | Layer 1 | `merchant-payments-platform/ledger-design.md` |
| 3 | Minor-unit long money (no float) | Layer 1 | `merchant-payments-platform/LedgerService.java` |
| 4 | Saga orchestration with compensation | Layer 2 | `merchant-payments-platform/PaymentOrchestrator.java`, `ledger-core/PaymentSaga.java` |
| 5 | Two-layer idempotency (Redis + Postgres) | Layer 2 | `aether-ledger/IdempotencyService.java` |
| 6 | Transactional outbox with SKIP LOCKED claim | Layer 3 | `sentinel-ledger/OutboxDispatchWorker.java` |
| 7 | Tamper-evident SHA-256 audit hash chain | Layer 1 | `aether-ledger/AuditChainService.java` |
| 8 | Fail-safe fraud degradation (not fail-open) | Layer 2 | `merchant-payments-platform/PaymentOrchestrator.java` |
| 9 | Stale outbox claim reclaim | Layer 3 | `sentinel-ledger/OutboxDispatchWorker.java` |
| 10 | REQUIRES_NEW for idempotency store | Layer 2 | `aether-ledger/IdempotencyService.java` |
| 11 | Webhook with HMAC + replay protection + DLQ | Layer 3 | `sentinel-ledger/INVARIANTS.md` WHK-001 |
| 12 | Continuous reconciliation with fingerprinted dedup | Layer 3 | `merchant-payments-platform/ledger-design.md` |

## 8. The 5 Invariant Tests

These are the tests that make the repo stand out. Each is graded at a proof level following the `sentinel-ledger/INVARIANTS.md` framework.

| # | Test | Invariant | Proof level | What it proves |
|---|------|-----------|-------------|----------------|
| 1 | 20-thread concurrent capture | PAY-001: capture never exceeds authorized | Concurrency | SERIALIZABLE + balance invariant hold under contention |
| 2 | 100 same-key submits | IDEM-001: exactly-once business effect | Persistence | Two-layer idempotency produces exactly one ledger entry |
| 3 | Outbox relay crash mid-batch | OUT-002: at-least-once with no lost events | Recovery | Stale claim reclaim picks up unpublished events after worker crash |
| 4 | Audit chain tamper detection | AUD-001: tamper-evident log | Domain | `verifyChain()` returns `valid=false` with exact sequence number after manual UPDATE |
| 5 | Reconciliation fingerprinted dedup | REC-001: no duplicate open cases | Persistence | Re-running reconciliation on the same mismatch does not create a second case |

## 9. Tech Stack

| Layer | Technology | Version | Why |
|-------|-----------|---------|-----|
| Language | Java | 25 (LTS) | Current LTS, matches `sentinel-ledger`, virtual threads mature |
| Framework | Spring Boot | 4.1.0 | Current, matches `sentinel-ledger` |
| Build | Maven | 3.9+ | Matches Capital One and Lilly DMS stack |
| Core DB | PostgreSQL | 16 | SERIALIZABLE isolation, advisory locks, SKIP LOCKED |
| Fast path | Redis | 7 | Idempotency cache, 72h TTL |
| Event bus | Redpanda | latest | Kafka-compatible, single-binary, no ZK |
| AWS local | LocalStack | latest | S3 (audit archive), SQS (webhook queue), DynamoDB (idempotency alt) |
| Migrations | Flyway | 10.x | Matches Lilly DMS, industry standard |
| Tests | JUnit 5 + Testcontainers | 1.20+ | Integration tests with real Postgres/Redis/Redpanda |
| HTTP client | Spring WebClient | 4.1 | Non-blocking, virtual-thread friendly |

## 10. Module Breakdown

| Module | GPN layer | Key classes | Invariant test |
|--------|-----------|-------------|----------------|
| `ledger-core` | Layer 1 | `LedgerService`, `JournalEntry`, `JournalLine`, `Account` | #1 (concurrent capture) |
| `idempotency` | Layer 2 | `IdempotencyService`, `IdempotencyRecord` | #2 (100 same-key submits) |
| `outbox` | Layer 3 | `OutboxDispatchWorker`, `OutboxEvent` | #3 (crash recovery) |
| `audit-chain` | Layer 1 | `AuditChainService`, `AuditEntry` | #4 (tamper detection) |
| `orchestrator` | Layer 2 | `PaymentOrchestrator`, `PaymentSaga` | (covered by #1) |
| `fraud-degradation` | Layer 2 | `FraudClient`, `DegradationPolicy` | (unit test) |
| `reconciliation` | Layer 3 | `ReconciliationService`, `ReconciliationCase` | #5 (fingerprinted dedup) |
| `webhook` | Layer 3 | `WebhookService`, `WebhookSignature` | (unit test) |

## 11. Local Emulator Usage

| Cloud service | Local emulator | Used for | In project |
|---------------|---------------|----------|------------|
| AWS S3 | LocalStack | Audit log archive (cold storage) | `audit-chain` module |
| AWS SQS | LocalStack | Webhook delivery queue | `webhook` module |
| AWS DynamoDB | LocalStack | Idempotency store alternative | `idempotency` module (optional) |
| AWS Kinesis | LocalStack | Event stream alternative to Redpanda | `outbox` module (optional) |
| AWS Secrets Manager | LocalStack | HMAC signing keys | `webhook` module |

No AWS account, no Azure account, no cloud spend. All emulators run in Docker via Testcontainers or `docker-compose.yml`.

## 12. README Structure (the 30-second sell)

```
# GPN Mini Ledger

A minimal GPN-style payment system demonstrating the layered priority stack
(CP core ledger, AP edge switch, BASE async lane) with executable invariant
tests. Runs 100% on local emulators, zero cloud cost.

## What this proves
- Java 25 + Spring Boot 4.1 (current LTS, matches Capital One stack)
- 12 production payment patterns (see PATTERNS.md, each with source line refs)
- 5 invariant tests at graded proof levels
- LocalStack integration (S3, SQS, DynamoDB)
- Zero cloud cost, clone and run in 10 minutes

## Quick start
docker compose up -d
./mvnw verify

## The priority stack
[diagram]

## Patterns demonstrated
[table mapping each pattern to source file + line number]
```

## 13. Interview Citation Plan

When the interviewer asks "how would you actually build this?", the answer is:

> "I built a minimal version of this. It is on my GitHub at [link]. The core ledger uses SERIALIZABLE isolation with a balance invariant test under 20-thread contention. The idempotency layer is two-tier, Redis fast path plus Postgres durable, with SHA-256 fingerprinting. The outbox uses SKIP LOCKED claim with stale claim reclaim. The audit log is a SHA-256 hash chain with PostgreSQL advisory locks. All 5 invariant tests pass. You can clone it and run `./mvnw verify` in 10 minutes."

This is a different conversation than someone who only read about the patterns.

## 14. Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| Scope creep | 8 modules max. No frontend. No microservices deployment. |
| Java 25 not on recruiter machine | Maven wrapper + Docker include JDK 25 |
| LocalStack flaky in CI | Testcontainers with retry, fallback to H2 for unit tests |
| Too much code for interview skim | Each module under 500 LOC. README is the entry point. |
| Looks like a tutorial, not production | Invariant tests at graded proof levels, SERIALIZABLE isolation, advisory locks, hash chain. These are not tutorial patterns. |

## 15. Out of Scope (explicit)

- Real card network integration (Visa/MC/Amex)
- PCI-DSS compliance scope
- Real money movement
- Kubernetes deployment
- Frontend UI
- OAuth2 / OIDC auth
- Multi-tenant SaaS
- Mobile SDK
