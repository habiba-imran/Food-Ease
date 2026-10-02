"""AppAdapter interface — voice code imports only this module from adapters/."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol, runtime_checkable

from foodease_agent.contract.models import (
    ActionRequestPayload,
    ActionResultPayload,
    AppControlPayload,
    AppTextInputPayload,
    ContextSnapshot,
)

ContextCallback = Callable[[ContextSnapshot], Awaitable[None] | None]
ControlCallback = Callable[[AppControlPayload], Awaitable[None] | None]
TextInputCallback = Callable[[AppTextInputPayload], Awaitable[None] | None]


@runtime_checkable
class AppAdapter(Protocol):
    """Application boundary. Wire format lives in LiveKitRpcAdapter (later)."""

    async def get_snapshot(self) -> ContextSnapshot:
        """Return the current authoritative context snapshot."""

    async def submit_action(
        self,
        request: ActionRequestPayload,
        *,
        timeout_s: float | None = None,
    ) -> ActionResultPayload:
        """Submit a validated action; correlate result by action_id.

        Per-operation timeout: if the app never replies, return
        ``timeout_unknown`` (never invent success).
        """

    def subscribe_context(self, callback: ContextCallback) -> None:
        """Subscribe to context updates (including GUI-driven changes)."""

    def subscribe_control(self, callback: ControlCallback) -> None:
        """Subscribe to app.control events."""

    def subscribe_text_input(self, callback: TextInputCallback) -> None:
        """Subscribe to typed user input."""
