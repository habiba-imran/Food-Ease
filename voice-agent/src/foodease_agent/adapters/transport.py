"""In-process transport for LiveKitRpcAdapter ↔ MockApp (tests / local rehearsal)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

Handler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]
DataHandler = Callable[[dict[str, Any]], Awaitable[None] | None]

MAX_PAYLOAD_BYTES = 15360


class PayloadTooLargeError(ValueError):
    pass


@dataclass
class InProcessRoom:
    """Minimal stand-in for a LiveKit room: RPC methods + data topics."""

    rpc_handlers: dict[str, Handler] = field(default_factory=dict)
    data_handlers: dict[str, list[DataHandler]] = field(default_factory=dict)
    attributes: dict[str, dict[str, str]] = field(default_factory=dict)
    identities: list[str] = field(default_factory=list)

    def register_participant(self, identity: str, *, role: str | None = None) -> None:
        if identity not in self.identities:
            self.identities.append(identity)
        attrs = self.attributes.setdefault(identity, {})
        if role:
            attrs["foodease.role"] = role

    def register_rpc(self, method: str, handler: Handler) -> None:
        self.rpc_handlers[method] = handler

    def subscribe_data(self, topic: str, handler: DataHandler) -> None:
        self.data_handlers.setdefault(topic, []).append(handler)

    async def perform_rpc(
        self,
        *,
        destination: str,
        method: str,
        payload: dict[str, Any],
        timeout_s: float = 5.0,
    ) -> dict[str, Any]:
        raw = json.dumps(payload).encode()
        if len(raw) > MAX_PAYLOAD_BYTES:
            raise PayloadTooLargeError(f"payload {len(raw)} > {MAX_PAYLOAD_BYTES}")
        handler = self.rpc_handlers.get(method)
        if handler is None:
            raise KeyError(f"no RPC handler for {method}")
        return await asyncio.wait_for(handler(payload), timeout=timeout_s)

    async def publish_data(self, topic: str, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload).encode()
        if len(raw) > MAX_PAYLOAD_BYTES:
            raise PayloadTooLargeError(f"payload {len(raw)} > {MAX_PAYLOAD_BYTES}")
        for h in self.data_handlers.get(topic, []):
            result = h(payload)
            if result is not None and hasattr(result, "__await__"):
                await result  # type: ignore[misc]

    def resolve_app_identity(self) -> str | None:
        for ident, attrs in self.attributes.items():
            if attrs.get("foodease.role") == "app":
                return ident
        # else first non-agent
        for ident in self.identities:
            if not ident.startswith("agent"):
                return ident
        return None
