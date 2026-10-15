from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def with_exponential_backoff(
    operation: Callable[[], T], *, attempts: int = 3, base_delay_seconds: float = 1.0
) -> T:
    """Retry transient provider operations; the final exception is preserved."""
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    for attempt in range(attempts):
        try:
            return operation()
        except Exception:
            if attempt + 1 == attempts:
                raise
            time.sleep(base_delay_seconds * (2**attempt))
    raise RuntimeError("unreachable")
