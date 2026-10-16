"""Role-bound Phase 3 startup gate; business tool runtime belongs to Phase 4."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
from foodease_contract.models import (
    AppControlEvent,
    ContextEvent,
    ContextSnapshot,
    assert_authorized,
    decode_event,
)
from foodease_contract.startup import StartupBinding


class IntegratedRoomGate:
    def __init__(self, room: Any, startup: StartupBinding):
        self.room, self.startup = room, startup
        self.latest: ContextSnapshot | None = None
        self.events: list[Any] = []
        self.closed = False
        self._callback = self.receive
        self._disconnect_callback = lambda *args: self.close()
        self._participant_callback = self._participant_left
        room.on("data_received", self._callback)
        room.on("disconnected", self._disconnect_callback)
        room.on("participant_disconnected", self._participant_callback)

    def _participant_left(self, participant: Any) -> None:
        if participant.identity in {
            self.startup.binding.app_identity,
            self.startup.binding.user_identity,
        }:
            self.close()

    def _bound(self, participant: Any, role: str) -> bool:
        if participant is None:
            return False
        attrs = participant.attributes or {}
        return (
            participant.identity == getattr(self.startup.binding, f"{role}_identity")
            and attrs.get("foodease.role") == role
            and attrs.get("foodease.session") == self.startup.binding.session_id
            and attrs.get("foodease.generation") == self.startup.generation
        )

    def resolve_app_identity(self) -> str | None:
        for participant in self.room.remote_participants.values():
            if self._bound(participant, "app"):
                return participant.identity
        return None

    def receive(self, packet: Any) -> None:
        if self.closed:
            return
        allowed = {
            "foodease.context.v2": {"app.context_snapshot", "app.context_updated"},
            "foodease.control.v2": {"app.control"},
            "foodease.text_input.v2": {"app.text_input"},
        }
        if packet.topic not in allowed:
            return
        try:
            event = decode_event(packet.data)
            if event.type not in allowed[packet.topic]:
                return
            role = "app" if isinstance(event, ContextEvent) else "user"
            sender = getattr(packet, "participant", None)
            if sender is None or not self._bound(sender, role):
                return
            assert_authorized(event, self.startup.binding, sender_identity=sender.identity)
            if isinstance(event, ContextEvent):
                if self.latest is None or event.payload.revision > self.latest.revision:
                    self.latest = event.payload
            else:
                self.events.append(event)
                del self.events[:-64]
                if isinstance(event, AppControlEvent) and (
                    event.payload.intent == "end"
                    or event.payload.intent == "switch_mode"
                    and event.payload.mode == "manual"
                ):
                    self.close()
        except (ValueError, TypeError, AttributeError):
            return

    async def wait_ready(self, *, timeout: float = 15) -> ContextSnapshot:
        async with asyncio.timeout(timeout):
            while not self.closed:
                people = list(self.room.remote_participants.values())
                if (
                    self.resolve_app_identity() is not None
                    and any(self._bound(p, "user") for p in people)
                    and self._bound(self.room.local_participant, "agent")
                    and self.latest is not None
                ):
                    return self.latest
                await asyncio.sleep(0.01)
        raise RuntimeError("integrated startup closed")

    def close(self) -> None:
        if not self.closed:
            self.closed = True
            self.room.off("data_received", self._callback)
            self.room.off("disconnected", self._disconnect_callback)
            self.room.off("participant_disconnected", self._participant_callback)


async def report_worker_ready(
    base_url: str, startup: StartupBinding, revision: int, *, runtime_ready: bool
) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=5, trust_env=False, follow_redirects=False) as client:
        response = await client.post(
            base_url.rstrip("/") + "/v2/assist/worker-ready",
            headers={"X-FoodEase-Worker-Proof": startup.worker_proof},
            json={
                "session_id": startup.binding.session_id,
                "generation": startup.generation,
                "context_revision": revision,
                "runtime_ready": runtime_ready,
            },
        )
        response.raise_for_status()
        return response.json()
