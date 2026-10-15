# Security policy

Do not commit credentials, live resumes, candidate identifiers, database files, or production logs. Provide vulnerability reports privately to the repository maintainers; do not open public issues containing exploit details or personal data. No public disclosure address is configured, so obtain the maintainer's approved private channel before sending a report.

The API must run behind TLS termination, request size limits, and rate limits. Keep database migrations separate from the API role. Configure OIDC issuer/audience/JWKS and enforce roles in the identity provider. Fernet keys must be generated independently, access-controlled, backed up, and rotated with a decrypt-and-reencrypt plan. Configure PostgreSQL TLS, backups, retention, and network ACLs. Enable Groq Zero Data Retention and verify contractual/data-location requirements before sending resumes.

Production startup requires references for jurisdiction, legal review, bias audit, privacy review, and the human review workflow. These are deployment attestations, not automatic proof of compliance. Do not use the system to screen, score, rank, recommend, accept, or reject applicants. A human approval control alone does not establish that employment use is lawful or unbiased.
