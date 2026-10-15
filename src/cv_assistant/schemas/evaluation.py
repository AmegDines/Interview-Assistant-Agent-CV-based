from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Confidence(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class WeakPoint(StrictModel):
    id: Annotated[str, StringConstraints(min_length=1, max_length=32)]
    requirement_id: Annotated[str, StringConstraints(min_length=1, max_length=32)]
    claim: Annotated[str, StringConstraints(min_length=1, max_length=500)]
    quote: Annotated[str, StringConstraints(min_length=1, max_length=500)]
    location: Annotated[str, StringConstraints(max_length=100)] | None = None
    confidence: Confidence


class ProbingQuestion(StrictModel):
    weak_point_id: Annotated[str, StringConstraints(min_length=1, max_length=32)]
    question: Annotated[str, StringConstraints(min_length=10, max_length=1000)]


class ApprovalEvent(StrictModel):
    decision: Literal["APPROVE", "REVISE"]
    reviewer_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    note: str | None = None


class EvaluationMetadata(StrictModel):
    model: str
    prompt_version: str
    software_version: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: Literal["awaiting_approval", "approved", "revision_requested", "complete"]
    confidence: Confidence


class ResumeEvaluationReport(StrictModel):
    candidate_id: UUID
    resume_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    weak_points: list[WeakPoint]
    probing_questions: list[ProbingQuestion]
    approval_log: list[ApprovalEvent]
    evaluation_metadata: EvaluationMetadata
