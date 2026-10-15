from __future__ import annotations

from groq import Groq

from cv_assistant.config import get_settings


def create_groq_client() -> Groq:
    settings = get_settings()
    return Groq(
        api_key=settings.groq_api_key.get_secret_value(),
        timeout=settings.groq_timeout_seconds,
        max_retries=0,
    )
