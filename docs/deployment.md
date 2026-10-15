# Deployment and operations

## Status

This is a pre-production release candidate, not an authorization to use AI in hiring. Regression evaluations, peer review, fairness assessment, and deployment-specific counsel review remain incomplete.

## Required services and identities

- PostgreSQL with TLS certificate verification, encrypted storage/backups, separate migration and application roles, network restrictions, and a retention policy.
- OIDC identity provider with a JWKS endpoint. Access tokens must be short-lived and include `sub`, `tenant_id`, and `roles`. Grant only `evaluator` and `reviewer` as needed.
- Groq API account configured for Zero Data Retention. The application sends resume text to the inference API; never treat transport encryption or local checkpoint encryption as anonymization.
- Secrets manager entries for the Groq key, database URL, and separate Fernet keys for raw resume and checkpoint encryption.
- A TLS ingress that enforces request-size limits (recommend 1 MiB), per-tenant/user rate limits, request timeouts, and trusted forwarded headers. The application has no built-in rate limiter and must not be exposed directly to the public internet.
- A user interface that displays `/v1/data-processing-notice` before submission and lets users access the employer's complete retention, deletion, and contact policy. The API version acknowledgment is not itself legal consent or proof of a lawful basis.

## Release procedure

1. Obtain deployment-specific legal, privacy, and independent bias audit approval. Establish the candidate notice, lawful basis, retention/deletion workflow, accommodations, and human reviewer training.
2. Set `APP_ENV=production`, populate the OIDC settings, configure a PostgreSQL URL containing `sslmode=verify-full`, and record references in all required review settings. Set `GROQ_ZERO_DATA_RETENTION=true` only after confirming the Groq organization setting.
3. Run `python scripts/migrate.py` as a restricted migration identity. API workers must not have schema-owner privileges.
4. Build the container from the reviewed source, scan its dependencies and image, then deploy behind the ingress. Verify `/health/ready` and PostgreSQL connectivity.
5. Use synthetic resumes to exercise the end-to-end review workflow in a non-production tenant before enabling real data.
6. Monitor error counts, provider latency, and capacity without logging prompts, source text, or candidate evidence. Establish an incident and key-loss response plan.

## Retention and key management

Checkpoints retain encrypted evaluation state, including evidence and final reports. Define and execute a retention schedule using `PostgresSaver.delete_thread` through an audited administrative service. Database backups require their own expiration and deletion policy. Keep key version metadata and perform a decrypt/re-encrypt migration before retiring any Fernet key. The current application does not implement automated checkpoint expiry, erasure requests, or key rotation.

## Legal and standards review references

Employment selection tools may be regulated even when they provide recommendations or support human decisions. The EU AI Act lists recruitment/selection systems among high-risk use cases in Annex III; NYC Local Law 144 imposes bias audit, public summary, and notice requirements for covered AEDTs; the EEOC explains that Title VII applies to automated systems used to make or inform selection decisions. These sources are not a complete jurisdictional analysis and do not constitute legal advice:

- [EU AI Act, Regulation (EU) 2024/1689](https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng)
- [NYC DCWP Automated Employment Decision Tools](https://www.nyc.gov/site/dca/about/automated-employment-decision-tools.page)
- [EEOC: Assessing Adverse Impact in Software, Algorithms, and AI](https://www.eeoc.gov/laws/guidance/select-issues-assessing-adverse-impact-software-algorithms-and-artificial)
- [Groq: Your Data in GroqCloud](https://console.groq.com/docs/your-data)
