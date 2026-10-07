"""MockApp LiveKit mode — join room as foodease.role=app (topology rehearsal)."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import httpx
from livekit import rtc

from foodease_agent.adapters.livekit_room import LiveKitRoom
from mock_app.participant import IDENTITY, MockAppParticipant, start_dev_control_server

logger = logging.getLogger("foodease.mock_app.livekit")

SESSION_API = os.environ.get("SESSION_API_URL", "http://127.0.0.1:8090").rstrip("/")


async def _mint_app_token(*, room: str, identity: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.post(
            f"{SESSION_API}/v1/token",
            json={"role": "app", "room": room, "identity": identity},
        )
        res.raise_for_status()
        return res.json()


def main_livekit(room_name: str) -> None:
    async def _boot() -> None:
        token_body = await _mint_app_token(room=room_name, identity=IDENTITY)
        url = token_body["livekit_url"]
        token = token_body["participant"]["token"]

        room = rtc.Room()
        await room.connect(url, token)
        room.local_participant.set_attributes({"foodease.role": "app"})

        bridge = LiveKitRoom(room)
        mock = MockAppParticipant(bridge, session_id=f"mock-live-{room_name}")
        await mock.start()
        start_dev_control_server(mock)
        print(
            f"MockApp LIVEKIT room={room_name!r} identity={IDENTITY} "
            f"DEV control :8765 | session={SESSION_API}"
        )
        logger.info("mock_app live connected room=%s", room_name)

        disconnected = asyncio.Event()

        def _on_disconnected(_: Any = None) -> None:
            disconnected.set()

        room.on("disconnected", _on_disconnected)
        await disconnected.wait()

    try:
        asyncio.run(_boot())
    except KeyboardInterrupt:
        print("bye")
