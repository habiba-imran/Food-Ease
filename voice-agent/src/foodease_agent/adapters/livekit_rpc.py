"""LiveKitRpcAdapter — AppAdapter over RPC / data topics (contract v1)."""

from __future__ import annotations

import logging
from typing import Any

from foodease_agent.adapters.base import (
    ContextCallback,
    ControlCallback,
    TextInputCallback,
)
from foodease_agent.adapters.transport import InProcessRoom, PayloadTooLargeError
from foodease_agent.contract.enums import (
    ActionResultStatus,
    EventType,
    Operation,
    UserSafeErrorCode,
)
from foodease_agent.contract.models import (
    ActionRequestPayload,
    ActionResultPayload,
    AppControlPayload,
    AppTextInputPayload,
    ContextSnapshot,
    Envelope,
)
from foodease_agent.faults import FAULTS

logger = logging.getLogger(__name__)

ACTION_RPC = "foodease.action"
TEXT_RPC = "foodease.text_input"
CONTEXT_TOPIC = "foodease.context"
CONTROL_TOPIC = "foodease.control"


class LiveKitRpcAdapter:
    """P0 adapter. Destination: foodease.role=app, else first non-agent participant."""

    def __init__(
        self,
        room: InProcessRoom,
        *,
        default_timeout_s: float = 5.0,
    ) -> None:
        self._room = room
        self._default_timeout_s = default_timeout_s
        self._context_cbs: list[ContextCallback] = []
        self._control_cbs: list[ControlCallback] = []
        self._text_cbs: list[TextInputCallback] = []
        self._latest: ContextSnapshot | None = None
        self._room.subscribe_data(CONTEXT_TOPIC, self._on_context_data)
        self._room.subscribe_data(CONTROL_TOPIC, self._on_control_data)

    def _destination(self) -> str:
        dest = self._room.resolve_app_identity()
        if dest is None:
            raise RuntimeError("no app participant in room")
        return dest

    async def get_snapshot(self) -> ContextSnapshot:
        if self._latest is not None:
            return self._latest
        await self.submit_action(
            ActionRequestPayload(
                action_id="snapshot-probe",
                operation=Operation.GET_CURRENT_CONTEXT,
                arguments={},
            )
        )
        if self._latest is None:
            raise RuntimeError("no context snapshot available yet")
        return self._latest

    async def submit_action(
        self,
        request: ActionRequestPayload,
        *,
        timeout_s: float | None = None,
    ) -> ActionResultPayload:
        if FAULTS.drop_connection:
            return ActionResultPayload(
                action_id=request.action_id,
                status=ActionResultStatus.TIMEOUT_UNKNOWN,
                error_code=UserSafeErrorCode.TIMEOUT,
                error_message="Connection dropped (dev fault).",
            )
        timeout = self._default_timeout_s if timeout_s is None else timeout_s
        payload = request.model_dump(mode="json")
        try:
            raw = await self._room.perform_rpc(
                destination=self._destination(),
                method=ACTION_RPC,
                payload=payload,
                timeout_s=timeout,
            )
        except TimeoutError:
            return ActionResultPayload(
                action_id=request.action_id,
                status=ActionResultStatus.TIMEOUT_UNKNOWN,
                error_code=UserSafeErrorCode.TIMEOUT,
                error_message="The app did not reply in time.",
            )
        except PayloadTooLargeError:
            return ActionResultPayload(
                action_id=request.action_id,
                status=ActionResultStatus.REJECTED,
                error_code=UserSafeErrorCode.INVALID_ARGUMENTS,
                error_message="Request too large.",
            )
        return ActionResultPayload.model_validate(raw)

    def subscribe_context(self, callback: ContextCallback) -> None:
        self._context_cbs.append(callback)

    def subscribe_control(self, callback: ControlCallback) -> None:
        self._control_cbs.append(callback)

    def subscribe_text_input(self, callback: TextInputCallback) -> None:
        self._text_cbs.append(callback)

    async def _on_context_data(self, payload: dict[str, Any]) -> None:
        if "type" in payload and "payload" in payload:
            env = Envelope.model_validate(payload)
            snap = ContextSnapshot.model_validate(env.payload)
        else:
            snap = ContextSnapshot.model_validate(payload)
        self._latest = snap
        for cb in self._context_cbs:
            result = cb(snap)
            if result is not None and hasattr(result, "__await__"):
                await result  # type: ignore[misc]

    async def _on_control_data(self, payload: dict[str, Any]) -> None:
        if "type" in payload and payload.get("type") == EventType.APP_CONTROL.value:
            ctrl = AppControlPayload.model_validate(payload["payload"])
        else:
            ctrl = AppControlPayload.model_validate(payload)
        for cb in self._control_cbs:
            result = cb(ctrl)
            if result is not None and hasattr(result, "__await__"):
                await result  # type: ignore[misc]

    async def send_text_input(self, text: str) -> None:
        tip = AppTextInputPayload(text=text)
        await self._room.perform_rpc(
            destination=self._destination(),
            method=TEXT_RPC,
            payload=tip.model_dump(mode="json"),
            timeout_s=self._default_timeout_s,
        )
        for cb in self._text_cbs:
            result = cb(tip)
            if result is not None and hasattr(result, "__await__"):
                await result  # type: ignore[misc]
