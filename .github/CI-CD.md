# CI/CD

This project mirrors the DMS (Dose Management System) pipeline pattern: hygiene workflows + build/test gates + security analysis.

## Workflows

| Workflow             | DMS Gate | Trigger                  | Purpose                                              |
| -------------------- | -------- | ------------------------ | ---------------------------------------------------- |
| `ci.yml`             | Gate 3-5 | push, PR                 | Compile + test + package (JDK 25, Maven)             |
| `pr-lint.yml`        | W1       | PR opened/edited         | PR title Conventional Commits format + non-empty body|
| `migration-check.yml`| Gate 2   | PR/push on migrations    | 6 Flyway checks: naming, sequencing, idempotency,    |
|                      |          |                          | dollar-quoting, append-only, conditional roles       |
| `labeler.yml`        | W3       | PR opened/synchronize    | File-based + size labels on PRs                      |
| `copilot-review.yml` | AI-assist| PR opened/reopened       | Auto-request Copilot code review (advisory)          |
| `codeql.yml`         | Security | push, PR, weekly cron    | GitHub CodeQL static analysis for Java               |
| `release.yml`        | Release  | push to main (CHANGELOG) | Auto-tag + GitHub Release on CHANGELOG version bump  |

## Pre-commit Hooks

Install the pre-commit framework and hooks:

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files   # run manually to verify
```

Hooks configured in `.pre-commit-config.yaml`:

| Hook                     | Purpose                                              |
| ------------------------ | ---------------------------------------------------- |
| `trailing-whitespace`    | Trim trailing whitespace                             |
| `end-of-file-fixer`      | Ensure newline at EOF                                |
| `check-yaml`             | Validate YAML syntax                                 |
| `check-merge-conflict`   | Detect merge conflict markers                        |
| `check-case-conflict`    | Check for case-sensitivity conflicts (macOS/Windows) |
| `check-added-large-files`| Block files >500KB                                   |
| `detect-private-key`     | Detect private keys                                  |
| `sqlfluff-lint`          | SQL lint for Flyway migrations (PostgreSQL dialect)  |
| `sqlfluff-fix`           | Auto-fix SQL formatting in migrations                |
| `mvn-compile` (local)    | Maven compile check on Java file changes             |
| `env-leak-check` (local) | Block `.env` / secrets from being committed          |

## Conventional Commits

PR titles must follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): description

# Examples:
feat(ledger-core): add SERIALIZABLE capture with retry on 40001
fix(migration): add CREATE SCHEMA IF NOT EXISTS to V1
docs(changelog): add 0.7.0 entry for isolation bypass fix
ci(codeql): add weekly CodeQL analysis workflow
```

Allowed types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `ci`, `build`, `perf`, `revert`.

## Branch Protection Rules

Configure on `main` via GitHub Settings → Branches → Branch protection rules:

### Required Status Checks

All must pass before merge:

| Check                                  | Workflow             |
| -------------------------------------- | -------------------- |
| `CI / Build + Test (JDK 25)`           | `ci.yml`             |
| `PR Lint / Validate PR title`          | `pr-lint.yml`        |
| `PR Lint / Validate PR description`    | `pr-lint.yml`        |
| `Migration Check / Validate migrations`| `migration-check.yml`|
| `CodeQL / Analyze (Java)`              | `codeql.yml`         |
| `PR Labeler / Apply file-based labels` | `labeler.yml`        |

### Merge Rules

- **Require PR before merging**: at least 1 approval
- **Require status checks to pass**: all listed above
- **Require branches up to date** before merging
- **Require linear history**: squash merges only
- **Disallow force pushes** to `main`
- **Allow force pushes**: `feat/*` and `fix/*` only

### Copilot Review

- Auto-requested on PR open via `copilot-review.yml`
- Advisory (non-blocking) — human approval still required
- **DMS lesson**: do not rubber-stamp. Copilot "looks good" ≠ human approval for business logic, domain correctness, or architecture.

## Tags and Releases

- **Versioning**: Semantic Versioning `MAJOR.MINOR.PATCH`
- **Tag format**: `vX.Y.Z` (e.g., `v0.7.0`)
- **Auto-release**: `release.yml` detects new versions in `CHANGELOG.md` and creates tag + GitHub Release on merge to `main`
- **Manual release**: `git tag -a vX.Y.Z -m "..." && git push origin vX.Y.Z && gh release create vX.Y.Z`

See `CONTRIBUTING.md` for the full commit message format, branching model, and release process.
