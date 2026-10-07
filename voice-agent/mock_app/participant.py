"""MockApp participant — website stand-in over transport (Phase 7.5)."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Any
from urllib.parse import urlparse

from foodease_agent.adapters.livekit_rpc import ACTION_RPC, CONTEXT_TOPIC, TEXT_RPC
from foodease_agent.adapters.mock import MockAdapter, ScenarioConfig, ScenarioMode
from foodease_agent.adapters.room_protocol import RoomTransport
from foodease_agent.adapters.transport import InProcessRoom
from foodease_agent.contract.models import (
    ActionRequestPayload,
    AppTextInputPayload,
    ContextSnapshot,
)
from foodease_agent.faults import FAULTS

logger = logging.getLogger("foodease.mock_app")

IDENTITY = "mock-app"


class MockAppParticipant:
    """Joins a room as foodease.role=app; owns MockAdapter cart/pages."""

    def __init__(self, room: RoomTransport, *, session_id: str = "mock-session") -> None:
        self.room = room
        self.adapter = MockAdapter(session_id=session_id)
        register = getattr(self.room, "register_participant", None)
        if callable(register):
            register(IDENTITY, role="app")
        self.room.register_rpc(ACTION_RPC, self._handle_action)
        self.room.register_rpc(TEXT_RPC, self._handle_text)

    async def start(self) -> ContextSnapshot:
        snap = await self.adapter.get_snapshot()
        await self.push_context(snap)
        return snap

    async def push_context(self, snap: ContextSnapshot | None = None) -> None:
        if snap is None:
            snap = await self.adapter.get_snapshot()
        await self.room.publish_data(CONTEXT_TOPIC, snap.model_dump(mode="json"))

    async def _handle_action(self, payload: dict[str, Any]) -> dict[str, Any]:
        req = ActionRequestPayload.model_validate(payload)
        result = await self.adapter.submit_action(req)
        await self.push_context()
        return result.model_dump(mode="json")

    async def _handle_text(self, payload: dict[str, Any]) -> dict[str, Any]:
        tip = AppTextInputPayload.model_validate(payload)
        await self.adapter.inject_text_input(tip.text)
        return {"ok": True}

    async def gui_navigate(self, page: str) -> None:
        await self.adapter.simulate_gui_navigation(page)
        await self.push_context()

    def set_scenario(self, mode: str, **kwargs: Any) -> None:
        self.adapter.set_scenario(ScenarioConfig(mode=ScenarioMode(mode), **kwargs))


def start_dev_control_server(
    mock: MockAppParticipant,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
) -> ThreadingHTTPServer:
    """Localhost-only control plane. Caller must ensure DEV_MODE=true."""

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: object) -> None:  # noqa: A003
            logger.info("%s %s", self.command, self.path.split("?", 1)[0])

        def _json(self, code: int, body: dict[str, Any]) -> None:
            data = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:  # noqa: N802
            if urlparse(self.path).path == "/health":
                self._json(200, {"ok": True, "faults": dict(FAULTS.__dict__)})
                return
            self._json(404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b"{}"
            try:
                body = json.loads(raw.decode() or "{}")
            except json.JSONDecodeError:
                self._json(400, {"error": "bad json"})
                return
            if path == "/scenario":
                mock.set_scenario(str(body.get("mode", "success")))
                self._json(200, {"ok": True})
                return
            if path == "/faults":
                for key in ("fail_stt", "fail_llm", "fail_tts", "drop_connection"):
                    if key in body:
                        setattr(FAULTS, key, bool(body[key]))
                self._json(200, {"ok": True, "faults": dict(FAULTS.__dict__)})
                return
            if path == "/navigate":
                page = str(body.get("page", "home"))
                asyncio.run(mock.gui_navigate(page))
                self._json(200, {"ok": True, "page": page})
                return
            self._json(404, {"error": "not found"})

    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("dev control must bind to localhost")
    server = ThreadingHTTPServer((host, port), Handler)
    Thread(target=server.serve_forever, daemon=True).start()
    logger.info("dev control on http://%s:%s", host, port)
    return server


def main() -> None:
    import os

    from dotenv import load_dotenv

    load_dotenv()
    if os.environ.get("DEV_MODE", "false").lower() not in {"1", "true", "yes", "on"}:
        raise SystemExit("Refusing to start MockApp control: set DEV_MODE=true")
    room = InProcessRoom()
    room.register_participant("agent-worker")
    mock = MockAppParticipant(room)
    asyncio.run(mock.start())
    start_dev_control_server(mock)
    print("MockApp running (in-process room). Ctrl+C to stop.")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("bye")


if __name__ == "__main__":
    main()
