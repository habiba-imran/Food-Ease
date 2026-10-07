"""Shared room surface for InProcessRoom and LiveKitRoom."""

from __future__ import annotations

from typing import Any, Protocol

from foodease_agent.adapters.transport import DataHandler, Handler


class RoomTransport(Protocol):
    """Minimal room API used by LiveKitRpcAdapter."""

    def register_rpc(self, method: str, handler: Handler) -> None: ...

    def subscribe_data(self, topic: str, handler: DataHandler) -> None: ...

    async def perform_rpc(
        self,
        *,
        destination: str,
        method: str,
        payload: dict[str, Any],
        timeout_s: float = 5.0,
    ) -> dict[str, Any]: ...

    async def publish_data(self, topic: str, payload: dict[str, Any]) -> None: ...

    def resolve_app_identity(self) -> str | None: ...
