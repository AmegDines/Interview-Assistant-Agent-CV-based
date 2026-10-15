from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

os.environ.setdefault("LANGGRAPH_STRICT_MSGPACK", "true")

from cryptography.fernet import Fernet
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.serde.encrypted import EncryptedSerializer
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import END, START, StateGraph

from cv_assistant.agent.nodes import (
    approval_gate,
    build_report,
    detect_weak_points,
    generate_questions,
    parse_resume,
    question_approval_gate,
)
from cv_assistant.agent.state import EvaluationState
from cv_assistant.config import get_settings
from cv_assistant.memory.audit_store import get_audit_store


class _FernetCipher:
    def __init__(self, key: bytes) -> None:
        self.fernet = Fernet(key)

    def encrypt(self, plaintext: bytes) -> tuple[str, bytes]:
        return "fernet", self.fernet.encrypt(plaintext)

    def decrypt(self, ciphername: str, ciphertext: bytes) -> bytes:
        if ciphername != "fernet":
            raise ValueError(f"Unsupported checkpoint cipher: {ciphername}")
        return self.fernet.decrypt(ciphertext)


def _compile(checkpointer: PostgresSaver):
    builder = StateGraph(EvaluationState)
    builder.add_node("parse_resume", parse_resume)
    builder.add_node("detect_weak_points", detect_weak_points)
    builder.add_node("approval_gate", approval_gate)
    builder.add_node("generate_questions", generate_questions)
    builder.add_node("question_approval_gate", question_approval_gate)
    builder.add_node("build_report", build_report)
    builder.add_edge(START, "parse_resume")
    builder.add_edge("parse_resume", "detect_weak_points")
    builder.add_edge("detect_weak_points", "approval_gate")
    builder.add_conditional_edges(
        "approval_gate",
        lambda state: "generate_questions" if state.get("approval_decision") == "APPROVE" else "build_report",
    )
    builder.add_edge("generate_questions", "question_approval_gate")
    builder.add_edge("question_approval_gate", "build_report")
    builder.add_edge("build_report", END)
    return builder.compile(checkpointer=checkpointer)


@contextmanager
def graph_runtime() -> Iterator[object]:
    """Own a production PostgreSQL checkpointer for the entire compiled graph lifetime."""
    url = get_settings().database_url.get_secret_value()
    key = get_settings().checkpoint_encryption_key.get_secret_value().encode("ascii")
    serde = EncryptedSerializer(_FernetCipher(key), JsonPlusSerializer(allowed_msgpack_modules=[]))
    with PostgresSaver.from_conn_string(url, serde=serde) as saver:
        yield _compile(saver)


def initialize_database() -> None:
    """Run schema setup under a deployment migration identity, never in the API worker."""
    settings = get_settings()
    key = settings.checkpoint_encryption_key.get_secret_value().encode("ascii")
    serde = EncryptedSerializer(_FernetCipher(key), JsonPlusSerializer(allowed_msgpack_modules=[]))
    with PostgresSaver.from_conn_string(settings.database_url.get_secret_value(), serde=serde) as saver:
        saver.setup()
    get_audit_store().setup()
