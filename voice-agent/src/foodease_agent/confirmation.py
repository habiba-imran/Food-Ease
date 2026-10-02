"""Confirmation machine (code, not prompt)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ConfirmState(StrEnum):
    NONE = "none"
    AWAITING = "awaiting"
    CONFIRMED = "confirmed"
    SUBMITTED = "submitted"


@dataclass
class ConfirmationMachine:
    """none → awaiting(summary_hash, revision) → confirmed → submitted."""

    state: ConfirmState = ConfirmState.NONE
    summary_hash: str | None = None
    revision: int | None = None
    confirmation_token: str | None = None
    summary_text: str | None = None
    summary_spoken: bool = False

    @staticmethod
    def hash_summary(payload: dict[str, Any]) -> str:
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]

    def begin_awaiting(
        self,
        *,
        summary: dict[str, Any],
        revision: int,
        summary_text: str,
        confirmation_token: str | None = None,
    ) -> None:
        self.state = ConfirmState.AWAITING
        self.summary_hash = self.hash_summary(summary)
        self.revision = revision
        self.summary_text = summary_text
        self.confirmation_token = confirmation_token
        self.summary_spoken = False

    def mark_summary_delivered(self) -> None:
        if self.state == ConfirmState.AWAITING:
            self.summary_spoken = True

    def invalidate(self) -> None:
        self.state = ConfirmState.NONE
        self.summary_hash = None
        self.revision = None
        self.confirmation_token = None
        self.summary_text = None
        self.summary_spoken = False

    def on_cart_or_revision_change(self, revision: int) -> bool:
        """Return True if a pending confirmation was invalidated."""
        if self.state in {ConfirmState.AWAITING, ConfirmState.CONFIRMED}:
            if self.revision is None or revision != self.revision:
                self.invalidate()
                return True
        return False

    def try_confirm(self, utterance: str, *, current_revision: int) -> bool:
        """Explicit yes only; silence/stop never confirm; summary must be delivered."""
        if self.state != ConfirmState.AWAITING:
            return False
        if not self.summary_spoken:
            return False
        if self.revision is not None and current_revision != self.revision:
            self.invalidate()
            return False
        text = utterance.strip().lower()
        if text in {"stop", "cancel", "never mind", "no"}:
            return False
        affirmatives = {
            "yes",
            "yeah",
            "yep",
            "confirm",
            "confirmed",
            "place it",
            "place the order",
            "submit",
            "go ahead",
            "do it",
        }
        if text in affirmatives or text.startswith("yes"):
            self.state = ConfirmState.CONFIRMED
            return True
        return False

    def mark_submitted(self) -> None:
        self.state = ConfirmState.SUBMITTED
