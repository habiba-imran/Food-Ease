"""Dev session wiring — MockAdapter or LiveKitRpcAdapter (topology rehearsal)."""

from __future__ import annotations

import logging
import os
from typing import Any

from foodease_agent.adapters.base import AppAdapter
from foodease_agent.adapters.livekit_room import LiveKitRoom
from foodease_agent.adapters.livekit_rpc import LiveKitRpcAdapter
from foodease_agent.adapters.mock import MockAdapter

logger = logging.getLogger(__name__)


def app_transport_mode() -> str:
    raw = (os.environ.get("FOODEASE_APP_TRANSPORT") or "mock").strip().lower()
    return raw if raw in {"mock", "livekit"} else "mock"


def create_dev_adapter(*, rtc_room: Any | None = None) -> AppAdapter:
    """Build the app adapter for the voice worker.

    - ``FOODEASE_APP_TRANSPORT=mock`` (default): in-process MockAdapter.
    - ``livekit``: LiveKitRpcAdapter over the job room (MockApp / Zainab seat).
    """
    mode = app_transport_mode()
    if mode == "livekit":
        if rtc_room is None:
            raise RuntimeError(
                "FOODEASE_APP_TRANSPORT=livekit requires the LiveKit job room"
            )
        bridge = LiveKitRoom(rtc_room)
        logger.info("dev_wiring: LiveKitRpcAdapter (topology rehearsal)")
        return LiveKitRpcAdapter(bridge)
    logger.info("dev_wiring: MockAdapter (in-process)")
    return MockAdapter()


async def wait_for_livekit_app(adapter: AppAdapter, *, timeout_s: float = 15.0) -> None:
    """When using LiveKitRpcAdapter, wait until foodease.role=app is present."""
    room = getattr(adapter, "_room", None)
    if isinstance(room, LiveKitRoom):
        identity = await room.wait_for_app(timeout_s=timeout_s)
        logger.info("app participant ready identity=%s", identity)
