from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class ResumeFacts(BaseModel):
    """Extracted facts only; values must be traceable to the supplied resume."""

    model_config = ConfigDict(extra="forbid")

    experience: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)


class EvaluationRequest(BaseModel):
    """Input contract; evaluation is bounded to explicit job requirements."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    resume_text: Annotated[str, StringConstraints(min_length=20, max_length=100_000)]
    job_requirements: list[Annotated[str, StringConstraints(min_length=3, max_length=500)]] = Field(min_length=1, max_length=30)
