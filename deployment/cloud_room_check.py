"""Disposable Cloud room/dispatch check; no microphone, provider call or purchase.

The production worker deliberately refuses jobs until its Render callback is set.
This checks RTC and dispatch infrastructure without claiming conversation acceptance.
"""

from __future__ import annotations

import asyncio
import json
import secrets
import time
from pathlib import Path
from uuid import uuid4

from cloud import local_environment
from foodease_contract.startup import StartupBinding
from livekit import api, rtc

ROOT = Path(__file__).resolve().parents[1]


async def main():
    env = local_environment()
    suffix = uuid4().hex[:16]
    name = "foodease-deploy-check-" + suffix
    user_identity = "user-" + suffix
    client = api.LiveKitAPI(env["LIVEKIT_URL"], env["LIVEKIT_API_KEY"], env["LIVEKIT_API_SECRET"])
    room = rtc.Room()
    result = {
        "room": name,
        "dispatch_name": "foodease",
        "conversation_tested": False,
        "microphone_used": False,
        "backend_callback_configured": False,
    }
    try:
        await client.room.create_room(
            api.CreateRoomRequest(
                name=name, empty_timeout=60, departure_timeout=10, max_participants=3
            )
        )
        token = (
            api.AccessToken(env["LIVEKIT_API_KEY"], env["LIVEKIT_API_SECRET"])
            .with_identity(user_identity)
            .with_grants(api.VideoGrants(room_join=True, room=name, can_publish=False))
            .to_jwt()
        )
        started = time.perf_counter()
        await asyncio.wait_for(room.connect(env["LIVEKIT_URL"], token), timeout=25)
        result["rtc_connected"] = room.local_participant.identity == user_identity
        result["rtc_connect_ms"] = round((time.perf_counter() - started) * 1000, 2)
        startup = StartupBinding.model_validate(
            {
                "schema_version": "2.0",
                "transport": "website",
                "consent": True,
                "generation": suffix,
                "request_id": suffix,
                "worker_proof": secrets.token_urlsafe(32),
                "binding": {
                    "session_id": "check-" + suffix,
                    "user_identity": user_identity,
                    "app_identity": "app-" + suffix,
                    "agent_identity": "agent-" + suffix,
                },
            }
        )
        dispatch = await client.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name="foodease", room=name, metadata=startup.model_dump_json()
            )
        )
        result["dispatch_created"] = bool(dispatch.id)
        result["dispatch_id"] = dispatch.id
        # Read only after the single create; never retry a possibly submitted dispatch.
        await asyncio.sleep(3)
        dispatches = await client.agent_dispatch.list_dispatch(name)
        result["dispatch_found"] = any(item.id == dispatch.id for item in dispatches)
        await client.agent_dispatch.delete_dispatch(dispatch.id, name)
        result["dispatch_cleaned"] = True
    finally:
        await room.disconnect()
        try:
            await client.room.delete_room(api.DeleteRoomRequest(room=name))
            result["room_cleaned"] = True
        finally:
            await client.aclose()
            output = ROOT / "deployment/evidence/cloud-room-check.json"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(json.dumps(result), flush=True)


if __name__ == "__main__":
    asyncio.run(asyncio.wait_for(main(), timeout=60))
