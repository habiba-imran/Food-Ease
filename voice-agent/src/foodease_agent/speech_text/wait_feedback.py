"""Truthful wait feedback — one honest status after ~1.5s; never success wording."""

from __future__ import annotations

import re

WAIT_THRESHOLD_SECONDS = 1.5

_FORBIDDEN_SUCCESS = re.compile(
    r"\b(done|added|removed|success|successful|placed|confirmed|complete[d]?|"
    r"all set|ready in (?:your )?cart|order(?:ed)?)\b",
    re.I,
)

_ALLOWED_STATUSES = (
    "Still checking the cart.",
    "Still working on that.",
    "Still waiting for the app.",
)


def is_safe_wait_message(text: str) -> bool:
    if not text.strip():
        return False
    if _FORBIDDEN_SUCCESS.search(text):
        return False
    return True


def wait_feedback_line(*, variant: int = 0) -> str:
    line = _ALLOWED_STATUSES[variant % len(_ALLOWED_STATUSES)]
    assert is_safe_wait_message(line)
    return line


class WaitFeedbackGate:
    """Emit at most one wait line per pending action."""

    def __init__(self, threshold_s: float = WAIT_THRESHOLD_SECONDS) -> None:
        self.threshold_s = threshold_s
        self._emitted = False

    def reset(self) -> None:
        self._emitted = False

    def maybe_line(self, elapsed_s: float) -> str | None:
        if self._emitted or elapsed_s < self.threshold_s:
            return None
        self._emitted = True
        return wait_feedback_line()
