from __future__ import annotations

import math
import re
from collections import Counter

from cv_assistant.schemas.evaluation import ProbingQuestion


def _terms(text: str) -> Counter[str]:
    return Counter(re.findall(r"[a-z0-9]+", text.casefold()))


def cosine_similarity(left: str, right: str) -> float:
    """Deterministic lexical cosine; this intentionally avoids an external embedding API."""
    a, b = _terms(left), _terms(right)
    if not a or not b:
        return 0.0
    dot = sum(count * b.get(term, 0) for term, count in a.items())
    norm_a = math.sqrt(sum(count * count for count in a.values()))
    norm_b = math.sqrt(sum(count * count for count in b.values()))
    return dot / (norm_a * norm_b)


def remove_near_duplicates(
    questions: list[ProbingQuestion], threshold: float
) -> list[ProbingQuestion]:
    if not 0.0 < threshold <= 1.0:
        raise ValueError("similarity threshold must be in (0, 1]")
    accepted: list[ProbingQuestion] = []
    for candidate in questions:
        if any(cosine_similarity(candidate.question, prior.question) >= threshold for prior in accepted):
            continue
        accepted.append(candidate)
    return accepted
