<!-- markdownlint-disable first-line-h1 no-inline-html -->

<!--
    By submitting this pull request, you confirm that you have read and
    understood the project's CONTRIBUTING.md and CODE_OF_CONDUCT.

    PR title MUST follow Conventional Commits: type(scope): description
    Examples:
      feat(ledger-core): add SERIALIZABLE capture with retry on 40001
      fix(migration): add CREATE SCHEMA IF NOT EXISTS to V1
      docs(changelog): add 0.8.0 entry for CI/CD workflows
      ci(codeql): add weekly CodeQL analysis workflow

    Allowed types: feat, fix, docs, style, refactor, test, chore, ci, build, perf, revert
    Allowed scopes: ledger-core, api-gateway, outbox, migration, ci, docs, infra
-->

## Summary

<!-- One or two sentences describing what this PR does and why. -->

## Type of Change

<!-- Check all that apply -->

- [ ] `feat` — new feature
- [ ] `fix` — bug fix
- [ ] `docs` — documentation only
- [ ] `refactor` — no behavior change
- [ ] `test` — tests only
- [ ] `ci` — CI/CD pipeline
- [ ] `chore` — build/tooling
- [ ] `perf` — performance
- [ ] `revert` — revert prior commit

## Breaking Changes

- [ ] No — this PR is fully backward-compatible
- [ ] Yes — describe below + add `!` to commit type (e.g., `feat(ledger-core)!: ...`)

<!-- If breaking, describe the impact and migration path. -->

## Testing

- [ ] `./mvnw -B -ntp test` passes locally
- [ ] `pre-commit run --all-files` passes
- [ ] New tests added for new code paths
- [ ] Invariant tests (INV-1, INV-2) still pass

<!-- Paste relevant test output below if applicable. -->

```
$ ./mvnw -B -ntp test
<output>
```

## Database Migrations

- [ ] No migration changes
- [ ] Migration added — follows `V{n}__{description}.sql` naming
- [ ] Migration is idempotent (`IF NOT EXISTS`, named dollar-quoting `$func$`)
- [ ] Migration is append-only (no `DROP`/`DELETE`/`TRUNCATE`)
- [ ] `migration-check.yml` passes locally

## Documentation

- [ ] No docs changes needed
- [ ] `CHANGELOG.md` updated with version entry
- [ ] `LEARNINGS.md` updated if a gotcha was discovered
- [ ] `README.md` updated if user-facing behavior changed

## Copilot Review

- [ ] Copilot review requested (auto on PR open to `main`)
- [ ] Copilot comments addressed or acknowledged

> **DMS lesson:** Copilot review is advisory. Do not rubber-stamp. Human review
> is required for business logic, domain correctness, and architecture.

## Checklist

- [ ] PR title follows Conventional Commits format
- [ ] Branch is up to date with `main` (`git fetch origin && git rebase origin/main`)
- [ ] No secrets / `.env` files committed
- [ ] Self-reviewed my own diff before requesting review
- [ ] Linked related issue: #

## Additional Notes

<!-- Screenshots, migration instructions, benchmarks, related PRs, etc. -->
