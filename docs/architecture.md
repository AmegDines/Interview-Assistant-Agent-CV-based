# Architecture

The FastAPI service validates OIDC identity, tenant scope, and evaluator/reviewer roles. The LangGraph workflow parses resume facts, detects quote-backed clarification points tied to explicit requirements, pauses for evidence review, generates linked questions, pauses for question review, then assembles the final report. Pydantic v2 validates inputs and model outputs. PostgreSQL stores checkpoints encrypted through LangGraph's serializer and a separate append-only audit table. Resume content is separately encrypted before entering graph state. Provider calls have bounded exponential backoff for transient failures.

See the repository README and deployment runbook for launch gates. Similarity uses local lexical cosine rather than semantic embeddings, and deployment-level rate limiting, retention automation, and deletion request handling are not implemented.
