"""Inbound app.* envelope handling — stale revisions logged, not used for decisions."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from foodease_agent.contract.enums import EventType
from foodease_agent.contract.models import (
    ActionResultPayload,
    AppControlPayload,
    AppTextInputPayload,
    ContextSnapshot,
    Envelope,
)

logger = logging.getLogger(__name__)


@dataclass
class InboundHandler:
    """Applies inbound app events; ignores stale context for decisions."""

    last_revision: int = 0
    latest_snapshot: ContextSnapshot | None = None
    pending_results: dict[str, ActionResultPayload] = field(default_factory=dict)
    stale_ignored: list[int] = field(default_factory=list)
    text_inputs: list[str] = field(default_factory=list)
    controls: list[AppControlPayload] = field(default_factory=list)

    def handle(self, envelope: Envelope) -> None:
        if envelope.type in {
            EventType.APP_CONTEXT_SNAPSHOT,
            EventType.APP_CONTEXT_UPDATED,
        }:
            snap = ContextSnapshot.model_validate(envelope.payload)
            if snap.revision < self.last_revision:
                self.stale_ignored.append(snap.revision)
                logger.info(
                    "ignored stale context revision=%s (have %s)",
                    snap.revision,
                    self.last_revision,
                )
                return
            self.last_revision = snap.revision
            self.latest_snapshot = snap
            return

        if envelope.type == EventType.APP_ACTION_RESULT:
            result = ActionResultPayload.model_validate(envelope.payload)
            self.pending_results[result.action_id] = result
            return

        if envelope.type == EventType.APP_CONTROL:
            self.controls.append(AppControlPayload.model_validate(envelope.payload))
            return

        if envelope.type == EventType.APP_TEXT_INPUT:
            tip = AppTextInputPayload.model_validate(envelope.payload)
            self.text_inputs.append(tip.text)
            return
