# Learnings

Gotchas encountered while building this project, root causes, and how to avoid them next time.

## Index

| #  | Area                  | Gotcha                                                       | Severity |
| -- | --------------------- | ------------------------------------------------------------ | -------- |
| 1  | Spring transactions   | Self-invocation bypasses `@Transactional`                   | Critical |
| 2  | Testcontainers + Mac  | `docker-java` ignores `~/.testcontainers.properties`        | High     |
| 3  | Flyway + PostgreSQL   | Nested `$$` dollar-quoting breaks Flyway parser             | High     |
| 4  | PostgreSQL 16         | No built-in `uuid_generate_v7()`                             | Medium   |
| 5  | Spring Boot 4         | Jackson 3 moves `SerializationFeature` to `tools.jackson`   | Medium   |
| 6  | Flyway                | `CREATE SCHEMA` before `CREATE TABLE schema.x`              | Medium   |
| 7  | Testcontainers roles  | Non-superuser init scripts cannot `CREATE ROLE`             | Medium   |
| 8  | Multi-catch Java      | Subclass + superclass in multi-catch is a compile error     | Low      |

---

## 1. Self-invocation bypasses `@Transactional` (Critical)

**Symptom**: 20 concurrent capture threads all succeeded when only 10 should have. The
`CaptureExceedsAuthorizationException` was never thrown. `capturedMinor` exceeded
`authorizedMinor`, violating PAY-001.

**Root cause**: `LedgerService.executeWithRetry` called
`operation.executeInSerializableTransaction()` where `LedgerOperation` was an interface
annotated with `@Transactional(isolation = SERIALIZABLE, propagation = REQUIRES_NEW)`.
Spring's proxy-based AOP only intercepts calls through the proxy — when a method inside the
same bean calls another method on `this`, the proxy is bypassed and the annotation is never
applied. The lambda was invoked as a plain method call, not through a Spring proxy, so all
threads ran in the default READ_COMMITTED isolation, read `capturedMinor=0` simultaneously,
and all committed.

**Fix**: Replaced the annotation-based approach with a programmatic `TransactionTemplate`:

```java
var tt = new TransactionTemplate(transactionManager);
tt.setIsolationLevel(TransactionDefinition.ISOLATION_SERIALIZABLE);
tt.setPropagationBehavior(TransactionDefinition.PROPAGATION_REQUIRES_NEW);
return tt.execute(status -> operation.execute());
```

The template executes inside the retry loop, so each retry attempt gets a fresh SERIALIZABLE
transaction with the correct isolation level.

**How to avoid**:
- Never rely on `@Transactional` for self-invocation. Either inject the bean into itself
  (ugly) or use `TransactionTemplate` programmatically.
- If you see a concurrency test where all threads succeed when some should fail, suspect
  isolation level misconfiguration. Add a log statement that prints
  `TransactionSynchronizationManager.getCurrentTransactionIsolationLevel()` inside the
  transaction to verify.
- Test with real Postgres (Testcontainers), not H2. H2 doesn't enforce SERIALIZABLE the
  same way and will hide this bug.

**Reference**: [Spring Framework docs — Transaction Management — Self-invocation](https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/annotations.html#transaction-declarative-annotations-method-visibility)

---

## 2. Testcontainers `docker-java` ignores `~/.testcontainers.properties` (High)

**Symptom**: `BadRequestException (Status 400: {"message":"client version 1.32 is too old.
Minimum supported API version is 1.40..."})` on every Testcontainers test.

**Root cause**: Testcontainers delegates to the `docker-java` client library. The client
defaults to Docker API v1.32, but modern Docker Desktop requires >=1.40. I tried setting
`DOCKER_API_VERSION` in `~/.testcontainers.properties`, in the POM `systemPropertyVariables`,
and as an environment variable on the `mvnw` command — none propagated to the forked
surefire JVM. The `docker-java` client reads its own config file (`~/.docker-java.properties`)
on class load, not the Testcontainers properties file.

**Fix**: Created `~/.docker-java.properties`:

```
DOCKER_HOST=unix:///var/run/docker.sock
DOCKER_API_VERSION=1.45
```

Also pinned `testcontainers.version=1.21.3` and added `docker-java-bom 3.5.1` to parent
`dependencyManagement` to ensure a compatible client version.

**How to avoid**:
- On macOS with Docker Desktop, if Testcontainers can't find Docker, check
  `ls -la /var/run/docker.sock` — it should be a symlink to
  `~/.docker/run/docker.sock`. If not, create it: `sudo ln -sf ~/.docker/run/docker.sock /var/run/docker.sock`.
- If you see `client version X is too old`, the fix is `~/.docker-java.properties`, not
  `~/.testcontainers.properties`.
- Verify the resolved docker-java version: `./mvnw dependency:tree -Dincludes=com.github.docker-java`.

---

## 3. Nested `$$` dollar-quoting breaks Flyway parser (High)

**Symptom**: `ERROR: syntax error at or near "DECLARE"` at line 22 of V1 migration.

**Root cause**: The migration used a `DO $$ ... $$` block containing a nested
`CREATE FUNCTION ... AS $$ ... $$` block. Flyway's SQL parser splits on `$$` and the nested
`$$` terminated the outer block early, leaving `DECLARE` as a top-level keyword.

**Fix**: Use distinct dollar-quote tags for each nesting level:

```sql
DO $role$
BEGIN
    -- ...
END
$role$;

CREATE OR REPLACE FUNCTION public.uuid_generate_v7() RETURNS UUID AS $func$
DECLARE
    -- ...
BEGIN
    -- ...
END;
$func$ LANGUAGE plpgsql VOLATILE;
```

**How to avoid**:
- Always use named dollar-quote tags (`$func$`, `$body$`, `$role$`) instead of bare `$$`
  when nesting plpgsql blocks in Flyway migrations.
- Flyway parses each statement before sending it to Postgres. Nested `$$` confuses the
  parser even though Postgres itself would accept it.

---

## 4. PostgreSQL 16 has no built-in `uuid_generate_v7()` (Medium)

**Symptom**: `ERROR: function uuid_generate_v7() does not exist`.

**Root cause**: The migrations assumed `uuid_generate_v7()` was available. It isn't —
PostgreSQL 16 only has `gen_random_uuid()` (v4) from `pgcrypto`. UUIDv7 support landed in
PostgreSQL 18 (as `uuidv7()`).

**Fix**: Added a plpgsql function that constructs a UUIDv7 from the current Unix timestamp
in milliseconds + `gen_random_bytes()` for the random tail, with version (7) and variant
(10xx) nibbles set per RFC 9562.

**How to avoid**:
- Don't assume a UUID function exists. Check the PostgreSQL version's function list.
- For timestamp-ordered UUIDs on PG <=17, roll your own with `gen_random_bytes()` from
  `pgcrypto`.
- On PG >=18, use the native `uuidv7()`.

---

## 5. Spring Boot 4 + Jackson 3: `SerializationFeature` moved (Medium)

**Symptom**: `BindException: Failed to bind properties under 'spring.jackson.serialization'
to java.util.Map<tools.jackson.databind.SerializationFeature, java.lang.Boolean>` at
context startup.

**Root cause**: Spring Boot 4 ships Jackson 3, where the `SerializationFeature` enum moved
from `com.fasterxml.jackson.databind` to `tools.jackson.databind`. The relaxed binding from
kebab-case `write-dates-as-timestamps` no longer resolves to the enum constant.

**Fix**: Removed the `spring.jackson.serialization.write-dates-as-timestamps` config from
`application.yml`. The default behavior in Jackson 3 is already ISO-8601 strings, so the
config was unnecessary.

**How to avoid**:
- When upgrading to Spring Boot 4, audit all Jackson config. Jackson 3 is a breaking change.
- Use the enum constant name (`WRITE_DATES_AS_TIMESTAMPS`) instead of kebab-case if you
  must configure it — but verify the enum is in `tools.jackson.databind` first.
- Prefer Java `java.time.Instant` / `OffsetDateTime` over `Date` to avoid serialization
  config entirely.

---

## 6. `CREATE SCHEMA` before `CREATE TABLE schema.x` (Medium)

**Symptom**: `ERROR: schema "ledger" does not exist` during Flyway migration.

**Root cause**: V1 migration created `ledger.accounts` etc. without first running
`CREATE SCHEMA ledger`. The `application.yml` had `spring.flyway.schemas: ledger, edge, async, audit`
but that only tells Flyway which schemas to manage — it doesn't create them.

**Fix**: Added `CREATE SCHEMA IF NOT EXISTS ledger;` (and `edge`, `audit`, `async`) at the
top of the respective migration files.

**How to avoid**:
- `spring.flyway.schemas` tells Flyway where to put its history table. It does NOT create
  the schemas. Always `CREATE SCHEMA IF NOT EXISTS` in the migration itself.
- Test with a fresh database (Testcontainers) on every run — a local dev DB that already
  has the schema will hide this bug.

---

## 7. Testcontainers non-superuser init scripts cannot `CREATE ROLE` (Medium)

**Symptom**: Initial test used `withInitScript("V1__ledger_core_schema.sql")` with
`withUsername("gpn")`. The migration's `CREATE ROLE gpn` failed because the `gpn` user
created by Testcontainers is not a superuser.

**Root cause**: Testcontainers creates the database user specified by `withUsername` as a
regular (non-superuser) role. `CREATE ROLE` requires superuser privileges.

**Fix**: Switched from `withInitScript` to Flyway-managed migrations. Flyway connects as
the same DB user (which Testcontainers grants superuser-like privileges to within the
test database). Also made the `CREATE ROLE gpn` conditional with `IF NOT EXISTS` so it
doesn't fail if the role already exists.

**How to avoid**:
- In Testcontainers, either use the default `test`/`test` superuser for DDL-heavy init
  scripts, or let Flyway manage migrations (Flyway runs as the app user and the container
  grants sufficient privileges).
- Always wrap `CREATE ROLE` in `IF NOT EXISTS` — the role may already exist in dev/staging
  environments.

---

## 8. Multi-catch with subclass + superclass is a compile error (Low)

**Symptom**: `error: types in multi-catch must be disjoint: ConcurrencyFailureException is a
subclass of ObjectOptimisticLockingFailureException`.

**Root cause**: A multi-catch block tried to catch both
`ObjectOptimisticLockingFailureException` and `ConcurrencyFailureException`. Since the former
extends the latter, catching both is redundant and Java disallows it.

**Fix**: Removed `ObjectOptimisticLockingFailureException` from the multi-catch and caught
only `ConcurrencyFailureException` (the superclass), which covers both serialization conflicts
and optimistic lock failures.

**How to avoid**:
- Check the inheritance hierarchy before multi-catching. If one exception extends another,
  catch only the superclass.
- Spring's exception hierarchy: `ConcurrencyFailureException` is the parent of
  `ObjectOptimisticLockingFailureException`, `PessimisticLockingFailureException`, etc.
  Catch the parent to cover all concurrency-related failures.
