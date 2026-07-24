# Contributing

## Commit Message Format

This project uses [Conventional Commits](https://www.conventionalcommits.org/) for all commit messages and PR titles.

### Format

```
type(scope): description

[optional body]

[optional footer(s)]
```

### Types

| Type       | When to use                                              |
| ---------- | -------------------------------------------------------- |
| `feat`     | A new feature                                            |
| `fix`      | A bug fix                                                |
| `docs`     | Documentation only changes                               |
| `style`    | Formatting, whitespace, semicolons — no code logic       |
| `refactor` | Code change that neither fixes a bug nor adds a feature  |
| `test`     | Adding or correcting tests                               |
| `chore`    | Build, deps, tooling — no production code change         |
| `ci`       | CI/CD pipeline changes                                   |
| `build`    | Build system or dependencies                             |
| `perf`     | Performance improvement                                  |
| `revert`   | Reverting a previous commit                              |

### Scopes

| Scope          | Covers                                                   |
| -------------- | -------------------------------------------------------- |
| `ledger-core`  | Core ledger module (domain, service, web, config)        |
| `api-gateway`  | API gateway module                                       |
| `outbox`       | Outbox module                                            |
| `migration`    | Flyway migration scripts                                 |
| `ci`           | GitHub Actions workflows                                 |
| `docs`         | README, CHANGELOG, LEARNINGS, CONTRIBUTING               |
| `infra`        | docker-compose, infra/ scripts                           |

### Breaking Changes

Append `!` after the type/scope:

```
feat(ledger-core)!: switch from @Transactional to TransactionTemplate for SERIALIZABLE

BREAKING CHANGE: LedgerService now requires PlatformTransactionManager bean.
```

### Examples

```
feat(ledger-core): add SERIALIZABLE capture with retry on SQLSTATE 40001
fix(migration): add CREATE SCHEMA IF NOT EXISTS to V1 ledger migration
docs(changelog): add 0.7.0 entry for transaction isolation bypass fix
ci(codeql): add weekly CodeQL analysis workflow
test(ledger-core): add INV-1 20-thread concurrent capture invariant test
refactor(ledger-core): replace self-invoked @Transactional with TransactionTemplate
```

### CI Commits

When CI files (workflows, pre-commit config) need propagation across release branches, prefix with the release branch tag (DMS pattern):

```
[Release-1.0] ci: sync CodeQL workflow across branches
```

---

## Branching Model

### Branches

| Branch        | Purpose                                  | Protection         |
| ------------- | ---------------------------------------- | ------------------ |
| `main`        | Production-ready, released code          | Fully protected    |
| `feat/*`      | Feature branches off `main`              | None (short-lived) |
| `fix/*`       | Bug fix branches off `main`              | None (short-lived) |
| `release/*`   | Release maintenance (future)             | Protected          |

### Branch Naming

```
feat/<short-description>      # e.g. feat/serializable-capture-retry
fix/<short-description>       # e.g. fix/flyway-schema-creation
docs/<short-description>      # e.g. docs/changelog-and-learnings
ci/<short-description>        # e.g. ci/codeql-workflow
```

**Enforced by CI**: `branch-naming.yml` fails the PR if the branch name does not
start with one of: `feat/`, `feature/`, `fix/`, `bugfix/`, `hotfix/`, `docs/`,
`style/`, `refactor/`, `test/`, `chore/`, `ci/`, `build/`, `perf/`, `revert/`,
`release/`, `dependabot/`, `renovate/`.

### Workflow

1. Create a feature branch off `main`: `git checkout -b feat/serializable-capture-retry`
2. Make commits following Conventional Commits format.
3. Push and open a PR targeting `main`.
4. CI gates run: `CI`, `PR Lint`, `Branch Naming`, `Migration Check`, `CodeQL`, `Labeler`, `Size Labeler`.
5. Advisory checks run: `Copilot Review`, `Anti-Pattern Scan`.
6. Human review + approval.
7. Squash-merge to `main` (keeps history clean, one commit per PR).
8. Release workflow tags the merge commit if `CHANGELOG.md` has a new version.

---

## Tags and Releases

### Versioning

This project follows [Semantic Versioning](https://semver.org/):

```
MAJOR.MINOR.PATCH
```

- **MAJOR**: incompatible API changes
- **MINOR**: new features, backward-compatible
- **PATCH**: bug fixes, backward-compatible

### Tag Format

```
v0.1.0    # initial scaffold
v0.2.0    # database schema
v0.7.0    # transaction isolation bypass fix
```

### Release Process

Releases are automated via the `release.yml` workflow:

1. Update `CHANGELOG.md` with a new version entry under `## [X.Y.Z] — YYYY-MM-DD`.
2. Open a PR with the CHANGELOG update.
3. On merge to `main`, the release workflow detects the new version and creates a git tag `vX.Y.Z` + GitHub Release with the CHANGELOG section as release notes.
4. The tag triggers the CI workflow to build and publish artifacts.

### Manual Release (fallback)

```bash
git tag -a v0.7.0 -m "fix(ledger-core): replace self-invoked @Transactional with TransactionTemplate"
git push origin v0.7.0
gh release create v0.7.0 --notes-file CHANGELOG.md
```

---

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
| `PR Labeler / Apply labels`            | `labeler.yml`        |

### Merge Rules

- **Require PR before merging**: at least 1 approval
- **Require status checks to pass**: all listed above
- **Require branches up to date** before merging
- **Require linear history**: squash merges only
- **Disallow force pushes** to `main`
- **Allow force pushes**: `feat/*` and `fix/*` only
- **Require review from Code Owners**: enabled (see `.github/CODEOWNERS`)

### Copilot Review

- Auto-requested on PR open via `copilot-review.yml`
- Advisory (non-blocking) — human approval still required
- **DMS lesson**: do not rubber-stamp. Copilot "looks good" ≠ human approval for business logic, domain correctness, or architecture.

---

## Code Owners

See `.github/CODEOWNERS`. Code owners are auto-requested as reviewers on PRs that touch their owned paths. Enable enforcement via:

**Settings → Branches → main → ✓ Require review from Code Owners**

---

## Pull Request Template

A PR template is auto-loaded from `.github/PULL_REQUEST_TEMPLATE.md` when you open a new PR. It includes:

- Summary
- Type of change (Conventional Commits checklist)
- Breaking changes
- Testing checklist
- Migration checklist
- Documentation checklist
- Copilot review acknowledgment
- Self-review checklist

Multiple templates can be added later in `.github/PULL_REQUEST_TEMPLATE/` if needed (e.g., `feature.md`, `bugfix.md`, `hotfix.md`). Select via URL query: `?template=feature.md`.

---

## Labels

Labels are auto-applied by `actions/labeler@v6` (see `.github/labeler.yml`). All labels below must exist in the repo — create them with:

```bash
gh label create "module:ledger-core"  --color 0E8A16 --description "Changes to ledger-core module"
gh label create "module:api-gateway"  --color 0E8A16 --description "Changes to api-gateway module"
gh label create "module:outbox"       --color 0E8A16 --description "Changes to outbox module"
gh label create "area:migration"      --color BFD4F2 --description "Flyway migration changes"
gh label create "area:domain"         --color BFD4F2 --description "Domain model changes"
gh label create "area:service"        --color BFD4F2 --description "Service layer changes"
gh label create "area:api"            --color BFD4F2 --description "REST API / controller changes"
gh label create "area:config"         --color BFD4F2 --description "application.yml / config changes"
gh label create "area:test"           --color FBCA04 --description "Test-only changes"
gh label create "area:ci-cd"          --color 5319E7 --description "GitHub Actions / pre-commit changes"
gh label create "area:infra"          --color 5319E7 --description "Docker / infra changes"
gh label create "area:docs"           --color 0075CA --description "Documentation changes"
gh label create "type:feature"        --color A2EEEF --description "New feature (feat/* branch)"
gh label create "type:bugfix"         --color D73A4A --description "Bug fix (fix/* branch)"
gh label create "type:docs"           --color 0075CA --description "Docs (docs/* branch)"
gh label create "type:ci"             --color 5319E7 --description "CI (ci/* branch)"
gh label create "type:refactor"       --color FBCA04 --description "Refactor (refactor/* branch)"
gh label create "type:test"           --color FBCA04 --description "Tests (test/* branch)"
gh label create "type:chore"          --color C5DEF5 --description "Chore/build/perf/revert branch"
gh label create "area:needs-triage"  --color FBCA04 --description "Needs initial triage"
```

### Label Categories

| Prefix        | Purpose                                  | Examples                          |
| ------------- | ---------------------------------------- | --------------------------------- |
| `module:*`    | Which Maven module is affected           | `module:ledger-core`              |
| `area:*`      | Which architectural area is affected     | `area:migration`, `area:service`  |
| `type:*`      | PR type (from branch name)               | `type:feature`, `type:bugfix`     |

---

## Pre-commit Hooks

Install before your first commit:

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files   # verify everything passes
```

See `.pre-commit-config.yaml` for the full hook list.

---

## Issue Templates

Bug reports and feature requests use templates in `.github/ISSUE_TEMPLATE/`:

- `bug_report.md` — includes invariant checklist (LED-001, PAY-001)
- `feature_request.md` — includes motivation + testing plan

These auto-populate when you open a new issue on GitHub.
