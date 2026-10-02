"""STT confidence gate for consequential intents (Phase 8.3)."""

from __future__ import annotations

from dataclasses import dataclass

from foodease_agent.controls import match_control
from foodease_agent.recovery import Va17Situation, recover

# Below this → clarify before quantity / remove / checkout
DEFAULT_MIN_CONFIDENCE = 0.55

_CONSEQUENTIAL_HINTS = (
    "add ",
    "remove ",
    "checkout",
    "place ",
    "make it ",
    "set quantity",
    "two",
    "three",
    "delete",
)


@dataclass
class ConfidenceGate:
    min_confidence: float = DEFAULT_MIN_CONFIDENCE

    def needs_clarification(self, utterance: str, confidence: float | None) -> bool:
        if confidence is None:
            return False
        if confidence >= self.min_confidence:
            return False
        # Controls are high-precision patterns — allow even if STT confidence low
        if match_control(utterance) is not None:
            return False
        low = utterance.strip().lower()
        return any(h in low for h in _CONSEQUENTIAL_HINTS)

    def clarify_line(self) -> str:
        return recover(Va17Situation.LOW_CONFIDENCE).assistant_text
