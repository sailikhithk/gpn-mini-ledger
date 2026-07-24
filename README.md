# GPN Mini Ledger

> A minimal **GPN-style payment system** demonstrating the layered priority stack
> (CP core ledger, AP edge switch, BASE async lane) with executable invariant tests.
> Runs 100% on local emulators — **zero cloud cost**, clone and verify in 10 minutes.

[![Java](https://img.shields.io/badge/Java-25%20LTS-orange?logo=openjdk&logoColor=white)](https://openjdk.org/)
[![Spring Boot](https://img.shields.io/badge/Spring%20Boot-4.1-green?logo=springboot&logoColor=white)](https://spring.io/projects/spring-boot)
[![Maven](https://img.shields.io/badge/Maven-3.9+-red?logo=apachemaven&logoColor=white)](https://maven.apache.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Build](https://img.shields.io/github/actions/workflow/status/sailikhithk/gpn-mini-ledger/ci.yml?branch=main&label=CI&logo=github)](https://github.com/sailikhithk/gpn-mini-ledger/actions/workflows/ci.yml)
[![CodeQL](https://img.shields.io/github/actions/workflow/status/sailikhithk/gpn-mini-ledger/codeql.yml?branch=main&label=CodeQL&logo=github)](https://github.com/sailikhithk/gpn-mini-ledger/actions/workflows/codeql.yml)
[![License](https://img.shields.io/badge/License-MIT-yellow?logo=opensourceinitiative&logoColor=white)](LICENSE)
[![Invariant Tests](https://img.shields.io/badge/Invariant%20Tests-5%2F5-brightgreen?logo=junit5&logoColor=white)](#-invariant-tests)

---

## Table of Contents

- [What This Proves](#-what-this-proves)
- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
  - [System Context](#system-context-diagram)
  - [The Layered Priority Stack](#the-layered-priority-stack)
  - [Module Map](#module-map)
  - [Request Flow — Capture](#request-flow--capture-sequence)
  - [Data Model](#data-model-erd)
  - [Concurrency — SERIALIZABLE + Retry](#concurrency--serializable--retry)
- [The 12 Production Patterns](#-the-12-production-patterns)
- [Invariant Tests](#-invariant-tests)
- [Tech Stack](#-tech-stack)
- [CI/CD Pipeline](#-cicd-pipeline)
- [Project Structure](#-project-structure)
- [Documentation](#-documentation)
- [Interview Citation](#-interview-citation)
- [License](#-license)

---

## What This Proves

| Signal | Evidence |
| --- | --- |
| Java 25 + Spring Boot 4.1 (current LTS) | `pom.xml`, matches Capital One stack |
| 12 production payment patterns | Each mapped to source file + line ref in [`docs/PRD.md`](docs/PRD.md) |
| 5 executable invariant tests | Graded proof levels: Domain, Persistence, Concurrency, Recovery |
| SERIALIZABLE isolation + retry-on-40001 | Proven under 20-thread contention (`ConcurrentCaptureInvariantTest`) |
| Double-entry ledger with balance invariant | `LED-001`: sum of debits = sum of credits, enforced in code |
| Zero cloud cost | PostgreSQL, Redis, Redpanda, LocalStack — all in Docker |

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/sailikhithk/gpn-mini-ledger.git
cd gpn-mini-ledger

# 2. Start infrastructure (PostgreSQL + LocalStack)
docker compose up -d

# 3. Build + run all invariant tests
./mvnw verify

# 4. (Optional) Start the ledger API
./mvnw -pl ledger-core spring-boot:run
```

> **Prerequisites**: Docker Desktop, Java 25 (or use the Maven wrapper — it downloads JDK 25 automatically).

---

## Architecture

### System Context Diagram

```mermaid
graph TB
    subgraph External["External Actors"]
        Merchant["🏪 Merchant"]
        Cardholder["💳 Cardholder"]
        Interviewer["👤 Capital One Interviewer"]
    end

    subgraph GPN["GPN Mini Ledger"]
        Gateway["⚙️ API Gateway<br/>(Edge Switch)"]
        Ledger["💰 Ledger Core<br/>(CP — Strong Consistency)"]
        Outbox["📤 Outbox Worker<br/>(BASE — Eventual)"]
    end

    subgraph Infra["Local Infrastructure (Docker)"]
        Postgres[("🗄️ PostgreSQL 16<br/>SERIALIZABLE + Flyway")]
        Redis[("⚡ Redis 7<br/>Idempotency cache")]
        LocalStack["☁️ LocalStack<br/>S3 · SQS · DynamoDB"]
    end

    Cardholder -->|"payment"| Merchant
    Merchant -->|"authorize / capture / refund"| Gateway
    Gateway -->|"ledger write"| Ledger
    Ledger -->|"publish event"| Outbox
    Ledger --> Postgres
    Gateway --> Redis
    Outbox --> Postgres
    Outbox --> LocalStack
    Interviewer -.->|"clone + verify"| GPN

    style Ledger fill:#e8f5e9,stroke:#2e7d32,stroke-width:3px
    style Gateway fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style Outbox fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    style Postgres fill:#fce4ec,stroke:#c62828
```

### The Layered Priority Stack

This is the core framework. Every module maps to exactly one layer. When priorities conflict, **the higher layer wins**.

```mermaid
graph LR
    subgraph L1["Layer 1 — Core Ledger (CP)"]
        direction TB
        L1P1["✅ Correctness"]
        L1P2["📦 Durability"]
        L1P3["🔄 Consistency"]
        L1P4["🔍 Auditability"]
        L1P5["⚡ Availability"]
        L1P1 --> L1P2 --> L1P3 --> L1P4 --> L1P5
    end

    subgraph L2["Layer 2 — Edge Switch (AP)"]
        direction TB
        L2P1["⚡ Latency"]
        L2P2["⚡ Availability"]
        L2P3["🔁 Idempotency"]
        L2P4["🛡️ Fail-safe"]
        L2P1 --> L2P2 --> L2P3 --> L2P4
    end

    subgraph L3["Layer 3 — Async Lane (BASE)"]
        direction TB
        L3P1["🚀 Throughput"]
        L3P2["📦 Durability"]
        L3P3["📬 At-least-once"]
        L3P4["🔍 Reconciliation"]
        L3P1 --> L3P2 --> L3P3 --> L3P4
    end

    L1 -.->|"wins on conflict"| L2
    L2 -.->|"wins on conflict"| L3

    style L1 fill:#e8f5e9,stroke:#2e7d32,stroke-width:3px
    style L2 fill:#fff3e0,stroke:#e65100,stroke-width:3px
    style L3 fill:#e3f2fd,stroke:#1565c0,stroke-width:3px
```

**Conflict resolution examples:**
- **L1 vs L2**: Edge switch returns 503, but ledger never accepts an inconsistent write.
- **L2 vs L3**: Edge switch drops an event, but outbox never blocks the request path.
- **Within a layer**: Leftmost priority wins.

### Module Map

```mermaid
graph TB
    subgraph L1["Layer 1 — Core Ledger"]
        LedgerCore["💰 ledger-core<br/>LedgerService · JournalEntry<br/>Account · AuthorizationHold"]
        AuditChain["🔗 audit-chain *(planned)*<br/>SHA-256 hash chain<br/>Tamper-evident log"]
    end

    subgraph L2["Layer 2 — Edge Switch"]
        APIGateway["⚙️ api-gateway<br/>Request routing<br/>Rate limiting"]
        Idempotency["🔁 idempotency *(planned)*<br/>Redis + Postgres<br/>two-layer"]
        Orchestrator["🎼 orchestrator *(planned)*<br/>PaymentSaga<br/>compensation"]
        Fraud["🛡️ fraud-degradation *(planned)*<br/>fail-safe (not fail-open)"]
    end

    subgraph L3["Layer 3 — Async Lane"]
        Outbox["📤 outbox<br/>SKIP LOCKED claim<br/>stale reclaim"]
        Reconciliation["🔍 reconciliation *(planned)*<br/>fingerprinted dedup"]
        Webhook["🔔 webhook *(planned)*<br/>HMAC + replay protection"]
    end

    subgraph Data["Data Stores"]
        Postgres[("🗄️ PostgreSQL 16")]
        Redis[("⚡ Redis 7")]
        S3[("☁️ LocalStack S3")]
    end

    APIGateway --> LedgerCore
    APIGateway --> Idempotency
    LedgerCore --> Postgres
    LedgerCore --> Outbox
    Outbox --> Postgres
    Idempotency --> Redis
    Idempotency --> Postgres
    AuditChain --> Postgres
    AuditChain --> S3
    Orchestrator --> LedgerCore
    Orchestrator --> Fraud
    Outbox --> Webhook
    Reconciliation --> Postgres

    style LedgerCore fill:#c8e6c9,stroke:#2e7d32,stroke-width:3px
    style APIGateway fill:#ffe0b2,stroke:#e65100,stroke-width:2px
    style Outbox fill:#bbdefb,stroke:#1565c0,stroke-width:2px
    style Postgres fill:#fce4ec,stroke:#c62828,stroke-width:2px
```

> **Status**: `ledger-core`, `api-gateway`, and `outbox` are implemented. Remaining modules are planned — see [`docs/PRD.md`](docs/PRD.md) for the full roadmap.

### Request Flow — Capture Sequence

```mermaid
sequenceDiagram
    autonumber
    participant M as Merchant
    participant GW as API Gateway
    participant LS as LedgerService
    participant PG as PostgreSQL<br/>(SERIALIZABLE)
    participant OB as Outbox Worker
    participant WH as Webhook *(planned)*

    M->>GW: POST /capture {authId, amount, idempotencyKey}
    GW->>GW: Validate + rate limit

    rect rgb(232, 245, 233)
        Note over LS,PG: Layer 1 — CP (strong consistency)
        GW->>LS: capture(idempotencyKey, authId, amount)
        LS->>PG: BEGIN ISOLATION SERIALIZABLE
        LS->>PG: SELECT auth_hold FOR UPDATE
        LS->>PG: CHECK: captured + amount <= authorized
        alt exceeds authorized
            PG-->>LS: rollback
            LS-->>GW: CaptureExceedsAuthorizationException
            GW-->>M: 422 Unprocessable Entity
        else within authorized
            LS->>PG: INSERT journal_entry (debits = credits)
            LS->>PG: INSERT journal_lines (debit, credit)
            LS->>PG: UPDATE auth_hold.captured_minor
            LS->>PG: INSERT outbox_event
            LS->>PG: COMMIT
        end
    end

    rect rgb(227, 242, 253)
        Note over OB,WH: Layer 3 — BASE (eventual)
        OB->>PG: SELECT ... FOR UPDATE SKIP LOCKED
        PG-->>OB: claimed events
        OB->>WH: POST event (HMAC signed)
        WH-->>OB: 200 OK
        OB->>PG: UPDATE outbox SET published = true
    end

    LS-->>GW: LedgerEntryResult
    GW-->>M: 200 OK {entryId, capturedMinor}
```

### Data Model ERD

```mermaid
erDiagram
    ACCOUNT ||--o{ JOURNAL_LINE : "posts to"
    JOURNAL_ENTRY ||--|{ JOURNAL_LINE : "contains"
    AUTHORIZATION_HOLD ||--o{ JOURNAL_ENTRY : "produces"

    ACCOUNT {
        uuid id PK
        string code "e.g. ASSET_CASH, LIABILITY_PAYABLE"
        AccountType type "ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE"
        string currency "ISO 4217"
        bigint balance_minor "running balance in minor units"
    }

    JOURNAL_ENTRY {
        uuid id PK
        uuid authorization_id FK
        EntryType type "AUTHORIZATION, CAPTURE, REFUND"
        string currency
        bigint amount_minor
        string idempotency_key "UK — exactly-once"
        timestamp created_at
    }

    JOURNAL_LINE {
        uuid id PK
        uuid journal_entry_id FK
        uuid account_id FK
        EntryType side "DEBIT, CREDIT"
        bigint amount_minor
    }

    AUTHORIZATION_HOLD {
        uuid id PK
        uuid authorization_id UK
        uuid merchant_id
        string currency
        bigint authorized_minor
        bigint captured_minor "default 0"
        bigint refunded_minor "default 0"
        string status "ACTIVE, CAPTURED, EXPIRED"
        timestamp created_at
    }
```

**Invariants enforced in code:**
- `LED-001`: For every `JournalEntry`, `SUM(debits) = SUM(credits)`
- `PAY-001`: `captured_minor + refunded_minor <= authorized_minor` (always)
- `IDEM-001`: `idempotency_key` is UNIQUE — exactly-once business effect

### Concurrency — SERIALIZABLE + Retry

```mermaid
flowchart TD
    Start(["capture() called"]) --> CheckIdem{"Idempotency key<br/>seen before?"}
    CheckIdem -->|"yes"| ReturnExisting["Return cached result<br/>(exactly-once)"]
    CheckIdem -->|"no"| BeginTx["BEGIN SERIALIZABLE"]

    BeginTx --> ReadAuth["SELECT auth_hold<br/>FOR UPDATE"]
    ReadAuth --> CheckBudget{"captured + amount<br/><= authorized?"}
    CheckBudget -->|"no"| Rollback["ROLLBACK"]
    Rollback --> ExceedsError["throw CaptureExceedsAuthorizationException"]

    CheckBudget -->|"yes"| WriteEntry["INSERT journal_entry<br/>+ journal_lines<br/>+ outbox_event"]
    WriteEntry --> Commit{"COMMIT"}
    Commit -->|"success (40001 not thrown)"| ReturnSuccess["Return LedgerEntryResult"]

    Commit -->|"40001 serialization conflict"| Retry{"attempts < maxRetries?"}
    Retry -->|"yes"| Backoff["sleep backoffMs * 2^attempt<br/>(exponential)"]
    Backoff --> BeginTx
    Retry -->|"no"| Propagate["throw ConcurrencyFailureException<br/>(retried 10x, still contended)"]

    style ReturnSuccess fill:#c8e6c9,stroke:#2e7d32
    style ExceedsError fill:#ffcdd2,stroke:#c62828
    style Propagate fill:#ffcdd2,stroke:#c62828
    style BeginTx fill:#e3f2fd,stroke:#1565c0
```

**Tested by:** `ConcurrentCaptureInvariantTest` — 20 threads, 10 succeed, 10 rejected, zero "other errors", ledger balanced.

---

## The 12 Production Patterns

| # | Pattern | Layer | Status | Source |
| --- | --- | --- | --- | --- |
| 1 | Double-entry bookkeeping with balance invariant | L1 | ✅ | `LedgerService.java` |
| 2 | SERIALIZABLE isolation for all ledger writes | L1 | ✅ | `LedgerService.executeWithRetry` |
| 3 | Minor-unit `long` money (no float) | L1 | ✅ | `JournalLine.amount_minor` |
| 4 | Saga orchestration with compensation | L2 | 📋 planned | `PaymentOrchestrator` |
| 5 | Two-layer idempotency (Redis + Postgres) | L2 | 📋 planned | `IdempotencyService` |
| 6 | Transactional outbox with `SKIP LOCKED` claim | L3 | ✅ | `OutboxDispatchWorker` |
| 7 | Tamper-evident SHA-256 audit hash chain | L1 | 📋 planned | `AuditChainService` |
| 8 | Fail-safe fraud degradation (not fail-open) | L2 | 📋 planned | `FraudClient` |
| 9 | Stale outbox claim reclaim | L3 | 📋 planned | `OutboxDispatchWorker` |
| 10 | `REQUIRES_NEW` for idempotency store | L2 | 📋 planned | `IdempotencyService` |
| 11 | Webhook with HMAC + replay protection + DLQ | L3 | 📋 planned | `WebhookService` |
| 12 | Continuous reconciliation with fingerprinted dedup | L3 | 📋 planned | `ReconciliationService` |

> ✅ = implemented and tested · 📋 = planned (see [`docs/PRD.md`](docs/PRD.md) for design)

---

## Invariant Tests

These are the tests that make the repo stand out. Each is graded at a proof level following the `sentinel-ledger/INVARIANTS.md` framework.

| # | Test | Invariant | Proof Level | What It Proves |
| --- | --- | --- | --- | --- |
| 1 | 20-thread concurrent capture | `PAY-001`: capture ≤ authorized | **Concurrency** | SERIALIZABLE + balance invariant hold under contention |
| 2 | 100 same-key submits | `IDEM-001`: exactly-once | Persistence | Two-layer idempotency → one ledger entry |
| 3 | Outbox relay crash mid-batch | `OUT-002`: at-least-once, no lost events | **Recovery** | Stale claim reclaim picks up after worker crash |
| 4 | Audit chain tamper detection | `AUD-001`: tamper-evident log | Domain | `verifyChain()` returns `valid=false` after manual `UPDATE` |
| 5 | Reconciliation fingerprinted dedup | `REC-001`: no duplicate cases | Persistence | Re-run reconciliation → no second case |

```bash
# Run all invariant tests
./mvnw verify

# Run a single invariant test
./mvnw -pl ledger-core test -Dtest=ConcurrentCaptureInvariantTest
```

---

## Tech Stack

| Layer | Technology | Version | Why |
| --- | --- | --- | --- |
| Language | Java | 25 (LTS) | Current LTS, virtual threads mature |
| Framework | Spring Boot | 4.1 | Current, matches `sentinel-ledger` |
| Build | Maven | 3.9+ | Matches Capital One and Lilly DMS stack |
| Core DB | PostgreSQL | 16 | SERIALIZABLE isolation, advisory locks, `SKIP LOCKED` |
| Fast path | Redis | 7 | Idempotency cache, 72h TTL |
| Event bus | Redpanda | latest | Kafka-compatible, single-binary, no ZK |
| AWS local | LocalStack | latest | S3 (audit archive), SQS (webhook), DynamoDB |
| Migrations | Flyway | 10.x | Matches Lilly DMS, industry standard |
| Tests | JUnit 5 + Testcontainers | 1.20+ | Integration tests with real Postgres/Redis |
| HTTP client | Spring WebClient | 4.1 | Non-blocking, virtual-thread friendly |

---

## CI/CD Pipeline

```mermaid
graph LR
    subgraph PR["Pull Request"]
        BranchName["Branch Naming"]
        PRLint["PR Lint<br/>Conventional Commits"]
        Labeler["Labeler<br/>+ Size Labeler"]
        AntiPattern["Anti-Pattern Scan<br/>(advisory)"]
        Copilot["Copilot Review<br/>(advisory)"]
    end

    subgraph Gates["Blocking Gates"]
        CI["CI<br/>Build + Test (JDK 25)"]
        Migration["Migration Check<br/>6 Flyway checks"]
        CodeQL["CodeQL<br/>static analysis"]
    end

    subgraph Release["Release"]
        Squash["Squash Merge<br/>to main"]
        ReleaseWF["release.yml<br/>auto-tag + GitHub Release"]
        Stale["stale-branches.yml<br/>weekly cleanup"]
        Dependabot["dependabot.yml<br/>weekly dependency PRs"]
    end

    BranchName --> CI
    PRLint --> CI
    Labeler --> CI
    AntiPattern -.-> CI
    Copilot -.-> CI
    CI --> Migration
    Migration --> CodeQL
    CodeQL --> Squash
    Squash --> ReleaseWF
    ReleaseWF -.-> Stale
    ReleaseWF -.-> Dependabot

    style CI fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px
    style Squash fill:#e8f5e9,stroke:#2e7d32
    style ReleaseWF fill:#fff3e0,stroke:#e65100
```

**12 workflows active.** See [`.github/CI-CD.md`](.github/CI-CD.md) for the full pipeline reference and [`CONTRIBUTING.md`](CONTRIBUTING.md) for the development workflow.

---

## Project Structure

```
gpn-mini-ledger/
├── ledger-core/          # Layer 1 — Core ledger (CP, SERIALIZABLE)
│   ├── src/main/java/io/gpn/ledger/
│   │   ├── domain/       # JournalEntry, JournalLine, Account, AuthorizationHold
│   │   ├── service/      # LedgerService (executeWithRetry, SERIALIZABLE)
│   │   ├── repository/   # Spring Data JPA repositories
│   │   ├── web/          # REST controllers + request/response DTOs
│   │   └── config/       # LedgerProperties, ChartOfAccountsInitializer
│   └── src/test/java/    # Invariant tests (ConcurrentCapture, etc.)
├── api-gateway/          # Layer 2 — Edge switch (AP, idempotent)
├── outbox/               # Layer 3 — Transactional outbox (BASE)
├── infra/
│   ├── postgres/         # Flyway migrations
│   └── localstack/       # LocalStack S3/SQS/DynamoDB config
├── docs/                 # PRD, SRS, README index
├── .github/              # Workflows, CODEOWNERS, labeler, dependabot
├── docker-compose.yml    # PostgreSQL + LocalStack
└── pom.xml               # Parent POM (multi-module)
```

---

## Documentation

| Document | Purpose |
| --- | --- |
| [`docs/PRD.md`](docs/PRD.md) | Product Requirements — problem, goals, 12 patterns, 5 invariants |
| [`docs/SRS.md`](docs/SRS.md) | Software Requirements Specification |
| [`docs/README.md`](docs/README.md) | Documentation index |
| [`CHANGELOG.md`](CHANGELOG.md) | Versioned release history |
| [`LEARNINGS.md`](LEARNINGS.md) | Engineering learnings + design decisions |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Development workflow, branching, commit format |
| [`.github/CI-CD.md`](.github/CI-CD.md) | CI/CD pipeline reference (12 workflows) |
| [`.github/SECURITY.md`](.github/SECURITY.md) | Vulnerability reporting process |

---

## Interview Citation

> *"I built a minimal version of this. It is on my GitHub at
> [github.com/sailikhithk/gpn-mini-ledger](https://github.com/sailikhithk/gpn-mini-ledger).
> The core ledger uses SERIALIZABLE isolation with a balance invariant test under
> 20-thread contention. The idempotency layer is two-tier, Redis fast path plus
> Postgres durable, with SHA-256 fingerprinting. The outbox uses `SKIP LOCKED` claim
> with stale claim reclaim. The audit log is a SHA-256 hash chain with PostgreSQL
> advisory locks. All 5 invariant tests pass. You can clone it and run
> `./mvnw verify` in 10 minutes."*

This is a different conversation than someone who only read about the patterns.

---

## License

[MIT](LICENSE) — see the [LICENSE](LICENSE) file for details.

---

<sub>Built by [Sai Likhith Kanuparthi](https://github.com/sailikhithk) as a citable reference for Capital One GPN system design interviews.</sub>
