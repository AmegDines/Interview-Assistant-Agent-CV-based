# CV Assistant

CV Assistant produces evidence-linked clarification items for human review. It does not score, rank, recommend, accept, or reject candidates. Human reviewers approve both the evidence items and generated questions before a report is returned.

This repository is a **pre-production implementation**. Employment use is gated on deployment owners providing policy review references and enabling Groq Zero Data Retention. Even with those settings, use requires deployment-specific legal review, independent bias audit, data-processing approval, and a documented human-review procedure. Startup references are attestations; the software cannot verify that the reviews were adequate.

## Runtime

Python 3.11+, PostgreSQL, an OIDC identity provider exposing a JWKS endpoint, and a Groq account are required. Install the exact direct dependency versions using `pip install .`. Set secrets through a secrets manager, not a committed `.env` file. Create two independent Fernet keys:

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Provide separate generated keys as `DATA_ENCRYPTION_KEY` and `CHECKPOINT_ENCRYPTION_KEY`. Do not rotate them without a planned decrypt-and-reencrypt operation; old checkpoints become unreadable when a key is lost or replaced.

Configure `GROQ_API_KEY`, `DATABASE_URL` (production requires `sslmode=verify-full`), `AUTH_JWKS_URL`, `AUTH_ISSUER`, and `AUTH_AUDIENCE`. Access tokens must contain `sub`, `tenant_id`, and a `roles` list. Assign `evaluator` and `reviewer` roles through the identity provider. A requester cannot review their own evaluation.

Run `python scripts/migrate.py` with a database migration identity before starting the API with `uvicorn cv_assistant.api:app --host 0.0.0.0 --port 8000`. API workers use the application database identity and do not create schema at startup. Terminate TLS at a trusted ingress, enforce request body limits and rate limits there, and restrict database network access. No reverse-proxy, identity-provider, cloud account, or production secret is configured in this repository.

## API flow

1. Fetch `GET /v1/data-processing-notice`, present the text, then `POST /v1/evaluations` with a bearer token in the `evaluator` role, resume, explicit job requirements, and the displayed notice version.
2. A separate `reviewer` retrieves the evaluation and approves or requests revision at the evidence review gate.
3. If approved, the model drafts clarification questions and the graph pauses again for question review.
4. The reviewer approves the questions to receive the final structured report. `REVISE` stops the workflow; create a new evaluation with corrected inputs to rerun.

The API uses tenant claims to isolate evaluations, hides cross-tenant IDs, and requires a different reviewer. Checkpoints are stored in PostgreSQL with Fernet encryption, and resume ciphertext uses a separate key. Audit events contain hashes and operational metadata only. Database backup retention and key management remain deployment responsibilities.

## Operations and launch gates

See [docs/deployment.md](docs/deployment.md), [SECURITY.md](SECURITY.md), [docs/threat_model.md](docs/threat_model.md), and [docs/data_privacy.md](docs/data_privacy.md). Groq documents that inference data is not retained by default, but reliability/abuse monitoring may retain inputs and outputs for up to 30 days unless the organization enables Zero Data Retention. The production startup gate requires the operator to attest that ZDR is enabled. Confirm the applicable Groq terms, DPA, data location, and transfer basis for each deployment.

No regression evaluation suite or independent peer review has been completed. Those are required before calling this ready for real hiring workflows; this repository is not yet approved for production use.
