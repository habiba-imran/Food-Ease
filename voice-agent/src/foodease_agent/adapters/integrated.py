"""Website v2 boundary. RPC envelopes and delivery receipts stay in adapters."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4

from foodease_contract.models import (
    ActionRequestEvent,
    ActionResultEvent,
    AgentControlEvent,
    ContextSnapshot,
    LookupRequest,
    LookupResponse,
    assert_correlated,
    assert_lookup_correlated,
    decode_event,
    encode_event,
    wire_bytes,
)

from foodease_agent.adapters.integrated_startup import IntegratedRoomGate


def new_id() -> str:
    return uuid4().hex


def now() -> datetime:
    return datetime.now(UTC)


def action_request(
    session_id: str, turn_id: str, revision: int, operation: str, arguments: dict[str, Any]
) -> ActionRequestEvent:
    return ActionRequestEvent.model_validate(
        {
            "schema_version": "2.0",
            "session_id": session_id,
            "event_id": new_id(),
            "turn_id": turn_id,
            "timestamp": now(),
            "context_revision": revision,
            "type": "agent.action_request",
            "payload": {
                "action_id": new_id(),
                "operation": operation,
                "arguments": arguments,
            },
        }
    )


class IntegratedAppAdapter(Protocol):
    async def get_snapshot(self) -> ContextSnapshot: ...
    async def submit(self, request: ActionRequestEvent) -> ActionResultEvent: ...
    async def lookup(self, action_id: str) -> LookupResponse: ...
    async def publish_control(self, intent: str, mode: str | None = None) -> None: ...
    async def publish_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        *,
        turn_id: str | None = None,
        revision: int | None = None,
    ) -> None: ...
    async def present_summary(
        self, *, turn_id: str, summary_id: str, text: str, summary_revision: int, summary_hash: str
    ) -> bool: ...


class IntegratedRpcAdapter:
    """Exact bound app seat only; no legacy probes, fallback seats or write retries."""

    def __init__(self, gate: IntegratedRoomGate, *, timeout: float = 5):
        self.gate, self.timeout = gate, timeout
        self.session_id = gate.startup.binding.session_id

    async def _rpc(self, method: str, payload: dict[str, Any], *, reconcile=False) -> str:
        destination = self.gate.resolve_app_identity()
        if destination is None or self.gate.closed and not reconcile:
            raise RuntimeError("application connection unavailable")
        raw = wire_bytes(payload).decode()
        response = await self.gate.room.local_participant.perform_rpc(
            destination_identity=destination,
            method=method,
            payload=raw,
            response_timeout=self.timeout,
        )
        # Do not accept a response from an attachment that disappeared mid-flight.
        if self.gate.resolve_app_identity() != destination:
            raise RuntimeError("application attachment changed")
        if len(response.encode()) > 14 * 1024:
            raise ValueError("payload_too_large")
        return response

    async def submit(self, request: ActionRequestEvent) -> ActionResultEvent:
        raw = await self._rpc("foodease.action.v2", json.loads(encode_event(request)))
        result = decode_event(raw)
        if not isinstance(result, ActionResultEvent):
            raise ValueError("action result required")
        assert_correlated(request, result)
        if result.context_revision < request.context_revision:
            raise ValueError("regressive action result")
        return result

    async def get_snapshot(self) -> ContextSnapshot:
        request = action_request(
            self.session_id,
            new_id(),
            self.gate.latest.revision if self.gate.latest else 0,
            "get_current_context",
            {},
        )
        result = await self.submit(request)
        if result.payload.status != "success":
            raise RuntimeError("fresh application context unavailable")
        snapshot = ContextSnapshot.model_validate((result.payload.verified_state or {})["snapshot"])
        if self.gate.latest and snapshot.revision < self.gate.latest.revision:
            raise ValueError("regressive context")
        self.gate.latest = snapshot
        return snapshot

    async def lookup(self, action_id: str) -> LookupResponse:
        request = LookupRequest(
            schema_version="2.0",
            session_id=self.session_id,
            event_id=new_id(),
            timestamp=now(),
            action_id=action_id,
        )
        result = LookupResponse.model_validate_json(
            await self._rpc(
                "foodease.action_status.v2",
                request.model_dump(mode="json"),
                reconcile=True,
            )
        )
        assert_lookup_correlated(request.model_dump(mode="json"), result)
        return result

    async def publish_control(self, intent: str, mode: str | None = None) -> None:
        event = AgentControlEvent.model_validate(
            {
                "schema_version": "2.0",
                "session_id": self.session_id,
                "event_id": new_id(),
                "timestamp": now(),
                "type": "agent.control",
                "payload": {"intent": intent, "mode": mode},
            }
        )
        await self.gate.room.local_participant.publish_data(
            encode_event(event),
            reliable=True,
            topic="foodease.events.v2",
            destination_identities=[
                self.gate.startup.binding.user_identity,
                self.gate.startup.binding.app_identity,
            ],
        )

    async def publish_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        *,
        turn_id: str | None = None,
        revision: int | None = None,
    ) -> None:
        event = decode_event(
            {
                "schema_version": "2.0",
                "session_id": self.session_id,
                "event_id": new_id(),
                "timestamp": now().isoformat(),
                "type": event_type,
                "turn_id": turn_id,
                "context_revision": revision,
                "payload": payload,
            }
        )
        await self.gate.room.local_participant.publish_data(
            encode_event(event),
            reliable=True,
            topic="foodease.events.v2",
            destination_identities=[
                self.gate.startup.binding.user_identity,
                self.gate.startup.binding.app_identity,
            ],
        )

    async def present_summary(
        self, *, turn_id: str, summary_id: str, text: str, summary_revision: int, summary_hash: str
    ) -> bool:
        """Typed checkout requires an explicit post-render receipt, not publish success.

        Phase 5 must implement this app-seat RPC. Missing/old/mismatched receipts
        fail closed; the model never sees or supplies the confirmation token.
        """
        request = {
            "schema_version": "2.0",
            "session_id": self.session_id,
            "turn_id": turn_id,
            "summary_id": summary_id,
            "summary_revision": summary_revision,
            "summary_hash": summary_hash,
            "text": text,
        }
        try:
            receipt = json.loads(await self._rpc("foodease.present_summary.v2", request))
            expected = {key: value for key, value in request.items() if key != "text"}
            return (
                isinstance(receipt, dict)
                and receipt.get("delivered") is True
                and receipt == {**expected, "delivered": True}
                and all(type(receipt.get(key)) is type(value) for key, value in expected.items())
            )
        except Exception:
            return False
