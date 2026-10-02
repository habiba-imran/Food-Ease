"""EventBus — validate envelopes against contract v1 before emit (Phase 7.1)."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from foodease_agent.contract.enums import SCHEMA_VERSION, EventType
from foodease_agent.contract.models import Envelope

Sink = Callable[[Envelope], Awaitable[None] | None]


class EnvelopeValidationError(ValueError):
    """Outgoing event failed contract validation — must not be sent."""


@dataclass
class EventBus:
    session_id: str
    sinks: list[Sink] = field(default_factory=list)
    history: list[Envelope] = field(default_factory=list)
    _user_partial_active: bool = False

    def add_sink(self, sink: Sink) -> None:
        self.sinks.append(sink)

    def build(
        self,
        event_type: EventType,
        payload: dict[str, Any],
        *,
        turn_id: str | None = None,
        context_revision: int | None = None,
        event_id: str | None = None,
        timestamp: datetime | None = None,
    ) -> Envelope:
        raw = {
            "schema_version": SCHEMA_VERSION,
            "session_id": self.session_id,
            "event_id": event_id or f"event-{uuid.uuid4().hex[:12]}",
            "turn_id": turn_id,
            "timestamp": timestamp or datetime.now(UTC),
            "context_revision": context_revision,
            "type": event_type,
            "payload": payload,
        }
        try:
            return Envelope.model_validate(raw)
        except Exception as exc:  # noqa: BLE001
            raise EnvelopeValidationError(str(exc)) from exc

    async def emit(self, envelope: Envelope) -> Envelope:
        # Final user transcript replaces interim (VA-08 / V7.5)
        if envelope.type == EventType.TRANSCRIPT_USER_PARTIAL:
            self._user_partial_active = True
        elif envelope.type == EventType.TRANSCRIPT_USER_FINAL:
            if self._user_partial_active:
                # Drop prior partials from history for this turn (replace semantics)
                self.history = [
                    e
                    for e in self.history
                    if not (
                        e.type == EventType.TRANSCRIPT_USER_PARTIAL
                        and e.turn_id == envelope.turn_id
                    )
                ]
            self._user_partial_active = False

        self.history.append(envelope)
        for sink in self.sinks:
            result = sink(envelope)
            if result is not None and hasattr(result, "__await__"):
                await result  # type: ignore[misc]
        return envelope

    async def publish(
        self,
        event_type: EventType,
        payload: dict[str, Any],
        **kwargs: Any,
    ) -> Envelope:
        env = self.build(event_type, payload, **kwargs)
        return await self.emit(env)
