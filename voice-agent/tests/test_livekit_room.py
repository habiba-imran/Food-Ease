"""Unit tests for LiveKitRoom bridge (no LiveKit Cloud)."""

from __future__ import annotations

from typing import Any

import pytest

from foodease_agent.adapters.livekit_room import LiveKitRoom
from foodease_agent.adapters.livekit_rpc import LiveKitRpcAdapter
from foodease_agent.adapters.transport import InProcessRoom
from foodease_agent.contract.enums import Operation
from foodease_agent.contract.models import ActionRequestPayload


class _FakeRemote:
    def __init__(self, identity: str, attributes: dict[str, str]) -> None:
        self.identity = identity
        self.attributes = attributes


class _FakeLocal:
    def __init__(self) -> None:
        self.identity = "agent-job"
        self.attrs: dict[str, str] = {}
        self.rpc: dict[str, Any] = {}
        self.published: list[tuple[str, bytes]] = []

    def set_attributes(self, attributes: dict[str, str]) -> None:
        self.attrs.update(attributes)

    def register_rpc_method(self, method: str, handler: Any) -> None:
        self.rpc[method] = handler

    async def perform_rpc(
        self,
        *,
        destination_identity: str,
        method: str,
        payload: str,
        response_timeout: float | None = None,
    ) -> str:
        assert destination_identity == "mock-app"
        assert method == "foodease.action"
        return '{"action_id":"a1","status":"success"}'

    async def publish_data(
        self,
        payload: bytes,
        *,
        reliable: bool = True,
        destination_identities: list[str] | None = None,
        topic: str = "",
    ) -> None:
        self.published.append((topic, payload))


class _FakeRoom:
    def __init__(self) -> None:
        self.local_participant = _FakeLocal()
        self.remote_participants = {
            "p1": _FakeRemote("mock-app", {"foodease.role": "app"}),
        }
        self._handlers: dict[str, Any] = {}

    def on(self, event: str, callback: Any = None) -> Any:
        self._handlers[event] = callback
        return callback


def test_resolve_app_identity() -> None:
    bridge = LiveKitRoom(_FakeRoom())  # type: ignore[arg-type]
    assert bridge.resolve_app_identity() == "mock-app"


@pytest.mark.asyncio
async def test_perform_rpc_and_publish() -> None:
    fake = _FakeRoom()
    bridge = LiveKitRoom(fake)  # type: ignore[arg-type]
    out = await bridge.perform_rpc(
        destination="mock-app",
        method="foodease.action",
        payload={"action_id": "a1", "operation": "get_current_context", "arguments": {}},
    )
    assert out["status"] == "success"
    await bridge.publish_data("foodease.context", {"revision": 1})
    assert fake.local_participant.published[0][0] == "foodease.context"


@pytest.mark.asyncio
async def test_adapter_still_works_with_inprocess() -> None:
    room = InProcessRoom()
    room.register_participant("mock-app", role="app")

    async def handler(payload: dict) -> dict:
        return {
            "action_id": payload["action_id"],
            "status": "success",
            "verified_state": {},
        }

    room.register_rpc("foodease.action", handler)
    adapter = LiveKitRpcAdapter(room)
    result = await adapter.submit_action(
        ActionRequestPayload(
            action_id="t1",
            operation=Operation.GET_CART,
            arguments={},
        )
    )
    assert result.status.value == "success"
