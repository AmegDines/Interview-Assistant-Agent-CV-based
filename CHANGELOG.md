# Changelog

## 0.2.0 — 2026-10-16 (pre-production)

- Replaced local SQLite persistence with PostgreSQL checkpoints and audit records; checkpoints are Fernet-encrypted.
- Added OIDC JWT authentication, tenant scoping, evaluator/reviewer roles, and separation of requester and reviewer.
- Restricted analysis to explicit job requirements, added source-quote validation, and added separate evidence and question approval gates.
- Added structured reports, an API, migration command, production startup attestations, and operational/security documentation.
- Updated the system prompt to v1.1.0. Regression evaluation and peer review have not been completed; no production approval is implied.
