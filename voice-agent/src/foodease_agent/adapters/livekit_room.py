"""LiveKit rtc.Room bridge matching InProcessRoom methods for LiveKitRpcAdapter."""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from livekit import rtc

from foodease_agent.adapters.transport import MAX_PAYLOAD_BYTES, PayloadTooLargeError

logger = logging.getLogger(__name__)

Handler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]
DataHandler = Callable[[dict[str, Any]], Awaitable[None] | None]


class LiveKitRoom:
    """Wrap a connected ``rtc.Room`` so LiveKitRpcAdapter can use real transport."""

    def __init__(self, room: rtc.Room) -> None:
        self._room = room
        self._data_handlers: dict[str, list[DataHandler]] = {}
        self._rpc_registered: set[str] = set()
        self._data_hooked = False

    @property
    def rtc_room(self) -> rtc.Room:
        return self._room

    def _ensure_data_hook(self) -> None:
        if self._data_hooked:
            return

        def _on_data(packet: rtc.DataPacket) -> None:
            topic = packet.topic or ""
            handlers = self._data_handlers.get(topic, [])
            if not handlers:
                return
            try:
                payload = json.loads(packet.data.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                logger.warning("livekit_room: non-json data on topic=%s", topic)
                return

            async def _run() -> None:
                for h in handlers:
                    result = h(payload)
                    if result is not None and hasattr(result, "__await__"):
                        await result  # type: ignore[misc]

            try:
                import asyncio

                loop = asyncio.get_running_loop()
                loop.create_task(_run())
            except RuntimeError:
                logger.warning("livekit_room: no running loop for data topic=%s", topic)

        self._room.on("data_received", _on_data)
        self._data_hooked = True

    def register_participant(self, identity: str, *, role: str | None = None) -> None:
        """Set local attributes when identity matches local participant."""
        local = self._room.local_participant
        if local is None:
            return
        if identity and local.identity != identity:
            logger.debug(
                "register_participant identity=%s local=%s (attrs applied to local)",
                identity,
                local.identity,
            )
        if role:
            local.set_attributes({"foodease.role": role})

    def register_rpc(self, method: str, handler: Handler) -> None:
        if method in self._rpc_registered:
            return

        async def _rpc_handler(data: rtc.RpcInvocationData) -> str:
            try:
                payload = json.loads(data.payload) if data.payload else {}
            except json.JSONDecodeError:
                payload = {}
            result = await handler(payload)
            raw = json.dumps(result).encode()
            if len(raw) > MAX_PAYLOAD_BYTES:
                raise PayloadTooLargeError(f"payload {len(raw)} > {MAX_PAYLOAD_BYTES}")
            return raw.decode("utf-8")

        self._room.local_participant.register_rpc_method(method, _rpc_handler)
        self._rpc_registered.add(method)

    def subscribe_data(self, topic: str, handler: DataHandler) -> None:
        self._ensure_data_hook()
        self._data_handlers.setdefault(topic, []).append(handler)

    async def perform_rpc(
        self,
        *,
        destination: str,
        method: str,
        payload: dict[str, Any],
        timeout_s: float = 5.0,
    ) -> dict[str, Any]:
        raw_bytes = json.dumps(payload).encode()
        if len(raw_bytes) > MAX_PAYLOAD_BYTES:
            raise PayloadTooLargeError(f"payload {len(raw_bytes)} > {MAX_PAYLOAD_BYTES}")
        response = await self._room.local_participant.perform_rpc(
            destination_identity=destination,
            method=method,
            payload=raw_bytes.decode("utf-8"),
            response_timeout=timeout_s,
        )
        return json.loads(response) if response else {}

    async def publish_data(self, topic: str, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload).encode()
        if len(raw) > MAX_PAYLOAD_BYTES:
            raise PayloadTooLargeError(f"payload {len(raw)} > {MAX_PAYLOAD_BYTES}")
        await self._room.local_participant.publish_data(
            raw,
            reliable=True,
            topic=topic,
        )

    def resolve_app_identity(self) -> str | None:
        for p in self._room.remote_participants.values():
            attrs = dict(p.attributes or {})
            if attrs.get("foodease.role") == "app":
                return p.identity
        for p in self._room.remote_participants.values():
            ident = p.identity or ""
            if not ident.startswith("agent") and "agent" not in ident.lower():
                return ident
        return None

    async def wait_for_app(self, *, timeout_s: float = 15.0) -> str:
        """Block until an app participant appears (topology rehearsal)."""
        import asyncio

        deadline = asyncio.get_running_loop().time() + timeout_s
        while asyncio.get_running_loop().time() < deadline:
            dest = self.resolve_app_identity()
            if dest:
                return dest
            await asyncio.sleep(0.25)
        raise TimeoutError("no foodease.role=app participant in room")
