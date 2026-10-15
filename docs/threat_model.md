# Threat model

## Assets and trust boundaries

Resume text may contain direct identifiers, sensitive personal details, and malicious instructions. Treat it as untrusted input. Provider requests leave the local machine and may be subject to provider retention terms; verify those terms before use. PostgreSQL stores encrypted workflow checkpoints and audit metadata.

## Threats and current controls

- Prompt injection in resume content and job criteria: prompts label both as untrusted; output is schema-validated and concerns whose quote is not an exact source substring are dropped.
- Fabricated citations: exact substring validation is enforced before approval.
- Unauthorized downstream processing: the graph interrupts and question generation independently checks for `APPROVE`.
- Secret leakage: credentials and encryption keys are required through environment/secrets management; `.env` is ignored by Git.
- Checkpoint disclosure: a Fernet `EncryptedSerializer` wraps the LangGraph checkpoint serializer. Resume text is separately encrypted before entering state. Key management and database encryption remain deployment requirements.
- Tenant/reviewer abuse: OIDC JWTs are validated against JWKS, issuer and audience; tenant claims scope evaluation lookups; reviewers cannot approve their own submissions.
- Audit tampering: PostgreSQL triggers reject updates/deletes by the application role. A database owner can still alter schema or storage; use independent database audit controls and protected backups.

## Limitations

Quote matching does not establish that an interpretation is fair or job-relevant. Resume text is still sent to the LLM provider. The similarity checker uses lexical cosine, not semantic embeddings. There is no automated fairness evaluation suite, robust PII detection, rate limiter, public notice UI, retention/deletion workflow, or independent immutable audit sink. API rate limits and body-size caps must be enforced at ingress. Human reviewers must validate evidence and relevance. A separate deployment-specific legal review and independent bias audit are launch blockers for employment use.
