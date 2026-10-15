from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated, Literal
from uuid import UUID

import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from langgraph.types import Command
from pydantic import BaseModel, ConfigDict
from jwt import PyJWKClient

from cv_assistant.agent.graph import graph_runtime
from cv_assistant.config import get_settings, validate_production_readiness
from cv_assistant.memory.audit_store import get_audit_store
from cv_assistant.schemas.resume import EvaluationRequest
from cv_assistant.service import prepare_evaluation

bearer = HTTPBearer(auto_error=False)
_jwk_client: PyJWKClient | None = None


class AuthenticatedUser(BaseModel):
    subject: str
    tenant_id: str
    roles: set[str]


class StartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evaluation: EvaluationRequest
    data_processing_notice_version: str


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["APPROVE", "REVISE"]


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        validate_production_readiness(settings)
        get_audit_store().ping()
        with graph_runtime() as graph:
            app.state.graph = graph
            yield

    app = FastAPI(
        title="CV Assistant API",
        version="0.2.0",
        docs_url="/docs" if settings.app_env == "development" else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.app_env == "development" else None,
        lifespan=lifespan,
    )
    notice_version = "2026-10-v1"
    data_notice = (
        "This service analyzes resume content against the job requirements you provide. "
        "Resume text is sent to Groq for model inference and checkpoint state is encrypted "
        "in the employer's PostgreSQL database. A human reviewer will inspect evidence and "
        "generated questions. Retention, deletion, and contact procedures are deployment-specific; "
        "consult the employer's published privacy notice before submitting candidate data."
    )

    def current_user(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> AuthenticatedUser:
        global _jwk_client
        if credentials is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
        try:
            if _jwk_client is None:
                _jwk_client = PyJWKClient(settings.auth_jwks_url, cache_jwk_set=True, lifespan=300)
            signing_key = _jwk_client.get_signing_key_from_jwt(credentials.credentials)
            claims = jwt.decode(
                credentials.credentials,
                signing_key.key,
                algorithms=["RS256", "ES256"],
                issuer=settings.auth_issuer,
                audience=settings.auth_audience,
                options={"require": ["exp", "iat", "sub", "tenant_id", "roles"]},
            )
            roles = claims["roles"]
            if not isinstance(roles, list) or not all(isinstance(role, str) for role in roles):
                raise ValueError("invalid roles claim")
            return AuthenticatedUser(subject=claims["sub"], tenant_id=claims["tenant_id"], roles=set(roles))
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from exc

    def require_role(role: str):
        def dependency(user: Annotated[AuthenticatedUser, Depends(current_user)]) -> AuthenticatedUser:
            if role not in user.roles:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
            return user
        return dependency

    @app.get("/health/live", include_in_schema=False)
    def live() -> dict[str, str]:
        return {"status": "alive"}

    @app.get("/v1/data-processing-notice")
    def get_data_processing_notice() -> dict[str, str]:
        return {"version": notice_version, "text": data_notice}

    @app.get("/health/ready", include_in_schema=False)
    def ready() -> dict[str, str]:
        if not hasattr(app.state, "graph"):
            raise HTTPException(status_code=503, detail="Service is not ready")
        return {"status": "ready"}

    @app.post("/v1/evaluations", status_code=202)
    def start_evaluation(
        body: StartRequest,
        user: Annotated[AuthenticatedUser, Depends(require_role("evaluator"))],
    ) -> dict:
        if body.data_processing_notice_version != notice_version:
            raise HTTPException(status_code=400, detail="Display and accept the current data processing notice")
        try:
            initial = prepare_evaluation(body.evaluation)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        initial.update({
            "tenant_id": user.tenant_id,
            "requested_by": user.subject,
            "data_processing_notice_version": notice_version,
        })
        thread_id = initial["candidate_id"]
        config = {"configurable": {"thread_id": thread_id}}
        result = app.state.graph.invoke(initial, config)
        return {"evaluation_id": thread_id, "status": result.get("status"), "weak_points": result.get("weak_points", [])}

    def owned_state(evaluation_id: UUID, user: AuthenticatedUser):
        config = {"configurable": {"thread_id": str(evaluation_id)}}
        snapshot = app.state.graph.get_state(config)
        values = snapshot.values or {}
        if values.get("tenant_id") != user.tenant_id:
            raise HTTPException(status_code=404, detail="Evaluation not found")
        return config, snapshot, values

    @app.get("/v1/evaluations/{evaluation_id}")
    def get_evaluation(
        evaluation_id: UUID,
        user: Annotated[AuthenticatedUser, Depends(current_user)],
    ) -> dict:
        config, snapshot, values = owned_state(evaluation_id, user)
        if "evaluator" not in user.roles and "reviewer" not in user.roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        if values.get("requested_by") != user.subject and "reviewer" not in user.roles:
            raise HTTPException(status_code=404, detail="Evaluation not found")
        return {
            "evaluation_id": str(evaluation_id),
            "status": values.get("status"),
            "weak_points": values.get("weak_points", []),
            "report": values.get("report"),
            "awaiting_review": bool(snapshot.next),
        }

    @app.post("/v1/evaluations/{evaluation_id}/review")
    def review_evaluation(
        evaluation_id: UUID,
        body: ReviewRequest,
        user: Annotated[AuthenticatedUser, Depends(require_role("reviewer"))],
    ) -> dict:
        config, snapshot, values = owned_state(evaluation_id, user)
        if not snapshot.next or not (set(snapshot.next) & {"approval_gate", "question_approval_gate"}):
            raise HTTPException(status_code=409, detail="Evaluation is not awaiting review")
        if values.get("requested_by") == user.subject:
            raise HTTPException(status_code=403, detail="The requester cannot approve their own evaluation")
        result = app.state.graph.invoke(
            Command(resume={"decision": body.decision, "reviewer_id": user.subject}), config
        )
        return {"evaluation_id": str(evaluation_id), "status": result.get("status"), "report": result.get("report")}

    @app.exception_handler(Exception)
    async def sanitized_exception_handler(request, exc: Exception):
        # Do not serialize provider exceptions or request bodies, which may contain resume data.
        import logging
        logging.getLogger("cv_assistant.api").error("Unhandled request failure (%s)", type(exc).__name__)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    return app


app = create_app()
