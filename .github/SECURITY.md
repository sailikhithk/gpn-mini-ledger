# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.8.x   | :white_check_mark: |
| < 0.8   | :x:                |

## Reporting a Vulnerability

**Do NOT open a public issue for security vulnerabilities.**

Instead, report privately via one of:

1. **GitHub Security Advisory** (preferred):
   - Go to https://github.com/sailikhithk/gpn-mini-ledger/security/advisories/new
   - Fill in the CVE template and submit privately.

2. **Email**: sailikhithcse@gmail.com with subject `[SECURITY] gpn-mini-ledger`

Please include:

- Description of the vulnerability
- Steps to reproduce (PoC if possible)
- Affected versions / commits
- Proposed fix (optional)

You will receive a response within 72 hours. Coordinated disclosure timeline:

- Day 0: report received, acknowledged
- Day 7: triage complete, severity assigned
- Day 30: fix developed, CVE requested (if applicable)
- Day 45: fix released, public advisory published

## Scope

In scope:

- SQL injection in ledger queries
- Broken access control on authorization/capture/refund endpoints
- Double-spend or balance corruption bypass
- Secrets leaked in commits or logs

Out of scope:

- Self-XSS
- Missing security headers on demo endpoints
- Theoretical timing attacks without a working PoC

## Security Measures in This Repo

- **Pre-commit hooks**: `detect-private-key`, `env-leak-check` block secrets at commit time
- **CodeQL**: weekly static analysis for Java
- **CODEOWNERS**: required review on sensitive paths (migrations, CI, infra)
- **Branch protection**: required status checks + code owner review on `main`
- **`.gitignore`**: `.env`, `*.pem`, `*.key` excluded from VCS
