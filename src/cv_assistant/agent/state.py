from typing import TypedDict

class EvaluationState(TypedDict, total=False):
    candidate_id: str
    resume_ciphertext: str
    job_requirements: list[dict[str, str]]
    resume_hash: str
    resume_facts: dict
    weak_points: list[dict]
    probing_questions: list[dict]
    approval_log: list[dict]
    report: dict
    approval_decision: str
    status: str
    model: str
