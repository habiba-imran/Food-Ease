"""Cartesia character-credit ledger (1 credit ≈ 1 character). Cap = 8000 for Phase 1."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

LEDGER_PATH = Path(__file__).resolve().parents[1] / "evidence" / "phase-1" / "cartesia_credits.json"
PHASE_CAP = 8000


@dataclass
class CreditState:
    used: int
    cap: int = PHASE_CAP

    @property
    def remaining(self) -> int:
        return self.cap - self.used


def _empty() -> dict:
    return {"cap": PHASE_CAP, "used": 0, "entries": []}


def load_state() -> CreditState:
    if not LEDGER_PATH.exists():
        return CreditState(used=0)
    data = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    return CreditState(used=int(data.get("used", 0)), cap=int(data.get("cap", PHASE_CAP)))


def save_charge(purpose: str, text: str, *, voice_id: str | None = None) -> CreditState:
    """Record a charge equal to len(text). Raises if over cap."""
    chars = len(text)
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = _empty()
    if LEDGER_PATH.exists():
        data = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    used = int(data.get("used", 0))
    cap = int(data.get("cap", PHASE_CAP))
    if used + chars > cap:
        raise RuntimeError(
            f"Cartesia credit cap would be exceeded: need {chars}, used {used}, "
            f"cap {cap}, remaining {cap - used}. Ask the human before continuing."
        )
    entry = {
        "ts": datetime.now(UTC).isoformat(),
        "purpose": purpose,
        "chars": chars,
        "voice_id": voice_id,
        "text_preview": text[:80],
    }
    data.setdefault("entries", []).append(entry)
    data["used"] = used + chars
    data["cap"] = cap
    LEDGER_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    state = CreditState(used=data["used"], cap=cap)
    print(
        f"[cartesia credits] +{chars} for {purpose} | running total {state.used}/{state.cap} "
        f"(remaining {state.remaining})"
    )
    return state


def plan_cost(texts: list[str]) -> int:
    return sum(len(t) for t in texts)
