from __future__ import annotations

import hashlib
import re
from uuid import uuid4

from cv_assistant.config import get_settings
from cv_assistant.schemas.resume import EvaluationRequest
from cv_assistant.security import encrypt_resume

_DISALLOWED_TERMS = re.compile(
    r"\b(age|date of birth|birth date|sex|gender|race|ethnicity|national origin|"
    r"religion|disability|marital status|family status|pregnan\w*|sexual orientation|"
    r"veteran status|citizenship|immigration status|native speaker|native-born|young|"
    r"able-bodied|married|unmarried|single parent)\b",
    re.IGNORECASE,
)


def prepare_evaluation(request: EvaluationRequest, *, candidate_id: str | None = None) -> dict:
    """Validate, minimize checkpoint exposure, and prepare initial workflow state."""
    settings = get_settings()
    if len(request.resume_text) > settings.max_resume_chars:
        raise ValueError(f"resume exceeds MAX_RESUME_CHARS ({settings.max_resume_chars})")
    for requirement in request.job_requirements:
        match = _DISALLOWED_TERMS.search(requirement)
        if match:
            raise ValueError(f"Job requirement contains a protected or sensitive criterion: {match.group(0)}")
    raw = request.resume_text
    return {
        "candidate_id": candidate_id or str(uuid4()),
        "resume_hash": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        "resume_ciphertext": encrypt_resume(raw),
        "job_requirements": [
            {"id": f"R{index}", "text": text}
            for index, text in enumerate(request.job_requirements, start=1)
        ],
        "status": "processing",
    }
