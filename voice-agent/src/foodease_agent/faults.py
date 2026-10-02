"""Dev-only fault injection toggles (Phase 7.9)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FaultToggles:
    fail_stt: bool = False
    fail_llm: bool = False
    fail_tts: bool = False
    drop_connection: bool = False

    def reset(self) -> None:
        self.fail_stt = False
        self.fail_llm = False
        self.fail_tts = False
        self.drop_connection = False


# Process-wide for localhost control endpoint when DEV_MODE=true
FAULTS = FaultToggles()
