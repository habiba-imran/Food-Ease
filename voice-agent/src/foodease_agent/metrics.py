"""Per-turn metrics JSONL (Phase 7.6)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def config_hash(parts: dict[str, Any]) -> str:
    blob = json.dumps(parts, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


@dataclass
class TurnMetrics:
    turn_id: str
    session_id: str
    config_hash: str
    end_of_turn_delay_ms: float | None = None
    llm_first_token_ms: float | None = None
    tts_first_byte_ms: float | None = None
    audible_ttfa_ms: float | None = None  # client-measured
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    extra: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        data = asdict(self)
        extra = data.pop("extra", {})
        data.update(extra)
        return json.dumps(data, default=str)


@dataclass
class MetricsLogger:
    path: Path
    config: dict[str, Any]

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._hash = config_hash(self.config)

    @property
    def hash(self) -> str:
        return self._hash

    def write(self, metrics: TurnMetrics) -> None:
        metrics.config_hash = self._hash
        with self.path.open("a", encoding="utf-8") as f:
            f.write(metrics.to_json() + "\n")
