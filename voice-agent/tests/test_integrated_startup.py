"""Phase 3 trusted room startup. No providers or microphone."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from foodease_contract.startup import StartupBinding

from foodease_agent.adapters.integrated_startup import IntegratedRoomGate


def binding():
    return StartupBinding.model_validate(
        {
            "schema_version": "2.0",
            "transport": "website",
            "consent": True,
            "generation": "generation",
            "request_id": "request",
            "worker_proof": "private-proof",
            "binding": {
                "session_id": "shop",
                "app_identity": "app",
                "user_identity": "user",
                "agent_identity": "agent",
            },
        }
    )


def person(role, identity=None):
    return SimpleNamespace(
        identity=identity or role,
        attributes={
            "foodease.role": role,
            "foodease.session": "shop",
            "foodease.generation": "generation",
        },
    )


class Room:
    def __init__(self):
        self.local_participant = person("agent")
        self.remote_participants = {"a": person("app"), "u": person("user")}
        self.handlers = {}

    def on(self, name, callback):
        self.handlers[name] = callback

    def off(self, name, callback):
        self.handlers.pop(name, None)


def context_event():
    path = Path(__file__).resolve().parents[1] / "contract/v2/examples/context_0.json"
    event = json.loads(path.read_text(encoding="utf-8"))
    event["session_id"] = event["payload"]["session_id"] = "shop"
    return event


def packet(event, sender=None, topic="foodease.context.v2"):
    return SimpleNamespace(
        topic=topic, data=json.dumps(event).encode(), participant=sender or person("app")
    )


@pytest.mark.asyncio
async def test_only_bound_role_and_sender_can_supply_fresh_context():
    room = Room()
    gate = IntegratedRoomGate(room, binding())
    gate.receive(packet(context_event(), person("user")))
    gate.receive(packet(context_event(), person("app", "intruder")))
    assert gate.latest is None
    event = context_event()
    event["session_id"] = "foreign"
    gate.receive(packet(event))
    assert gate.latest is None
    gate.receive(packet(context_event()))
    assert (await gate.wait_ready(timeout=0.1)).session_id == "shop"
    old = context_event()
    old["context_revision"] = old["payload"]["revision"] = 0
    gate.receive(packet(old))
    assert gate.latest is not None
    assert gate.latest.revision == 1
    gate.close()
    assert not room.handlers


@pytest.mark.asyncio
async def test_no_fallback_to_arbitrary_non_agent_or_wrong_generation():
    room = Room()
    room.remote_participants["a"] = person("user", "random-browser")
    gate = IntegratedRoomGate(room, binding())
    gate.receive(packet(context_event()))
    with pytest.raises(TimeoutError):
        await gate.wait_ready(timeout=0.02)
    assert gate.resolve_app_identity() is None
    gate.close()


@pytest.mark.asyncio
async def test_control_and_text_require_bound_user_not_app_or_foreign_session():
    gate = IntegratedRoomGate(Room(), binding())
    event = {
        "schema_version": "2.0",
        "session_id": "shop",
        "event_id": "event",
        "type": "app.control",
        "timestamp": "2026-10-17T12:00:00Z",
        "payload": {"intent": "switch_mode", "mode": "manual"},
    }
    gate.receive(packet(event, person("app"), "foodease.control.v2"))
    assert gate.events == []
    text = {
        **event,
        "type": "app.text_input",
        "turn_id": "turn",
        "context_revision": 1,
        "payload": {"text": "show wraps"},
    }
    gate.receive(packet(text, person("app"), "foodease.text_input.v2"))
    assert gate.events == []
    gate.receive(
        packet({**text, "session_id": "foreign"}, person("user"), "foodease.text_input.v2")
    )
    assert gate.events == []
    gate.receive(packet(text, person("user"), "foodease.text_input.v2"))
    assert len(gate.events) == 1
    gate.receive(packet(event, person("user"), "foodease.control.v2"))
    assert len(gate.events) == 2
    assert gate.closed
    gate.close()


def test_integrated_transport_never_falls_back_to_mock(monkeypatch):
    from foodease_agent.adapters.dev_wiring import app_transport_mode, create_dev_adapter

    monkeypatch.setenv("FOODEASE_APP_TRANSPORT", "misspelled")
    with pytest.raises(ValueError):
        app_transport_mode()
    monkeypatch.setenv("FOODEASE_APP_TRANSPORT", "website")
    with pytest.raises(RuntimeError, match="integrated"):
        create_dev_adapter()


@pytest.mark.asyncio
async def test_worker_identity_is_fixed_by_dispatch_not_client(monkeypatch):
    from foodease_agent.worker import accept_job

    monkeypatch.setenv("FOODEASE_APP_TRANSPORT", "website")

    class Request:
        job = SimpleNamespace(metadata=binding().model_dump_json())
        accepted: dict[str, Any] | None = None
        rejected = False

        async def accept(self, **kwargs):
            self.accepted = kwargs

        async def reject(self):
            self.rejected = True

    request = Request()
    await accept_job(request)  # type: ignore[arg-type]
    assert request.accepted is not None
    assert request.accepted["identity"] == "agent"
    assert request.accepted["attributes"]["foodease.generation"] == "generation"
    request = Request()
    request.job = SimpleNamespace(metadata="{}")
    await accept_job(request)  # type: ignore[arg-type]
    assert request.rejected and request.accepted is None


@pytest.mark.asyncio
@pytest.mark.parametrize("allowed", [True, False])
async def test_actual_job_gate_never_starts_runtime_before_authorized_ready(monkeypatch, allowed):
    from foodease_agent import worker

    room = Room()
    original_on = room.on

    def publish_context(name, callback):
        original_on(name, callback)
        if name == "data_received":
            callback(packet(context_event()))

    room.on = publish_context
    order, shutdown = [], []

    class Runtime:
        async def start(self):
            order.append("runtime-start")

        async def close(self):
            order.append("runtime-close")

    async def factory(*args):
        order.append("runtime-prepared")
        return Runtime()

    async def acknowledge(*args, **kwargs):
        assert "runtime-start" not in order
        order.append("authorized-ready")
        return {"greeting_allowed": allowed}

    class Context:
        room: Room

        async def connect(self, **kwargs):
            order.append("connect")

        def add_shutdown_callback(self, callback):
            self.cleanup = callback

        def shutdown(self, reason):
            shutdown.append(reason)

    ctx = Context()
    ctx.room = room
    monkeypatch.setattr(worker, "report_worker_ready", acknowledge)
    await worker.run_integrated_job(ctx, binding(), runtime_factory=factory)
    assert order.index("authorized-ready") > order.index("runtime-prepared")
    if allowed:
        assert order[-1] == "runtime-start"
        await ctx.cleanup()
    else:
        assert "runtime-start" not in order and shutdown


@pytest.mark.asyncio
async def test_missing_phase4_runtime_reports_unavailable_without_provider_start(monkeypatch):
    from foodease_agent import worker

    room = Room()

    def on(name, callback):
        room.handlers[name] = callback
        if name == "data_received":
            callback(packet(context_event()))

    room.on = on
    reported = []

    async def report(*args, **kwargs):
        reported.append(kwargs["runtime_ready"])
        return {"greeting_allowed": False}

    async def connect(**kwargs):
        pass

    ctx = SimpleNamespace(
        room=room,
        connect=connect,
        add_shutdown_callback=lambda cb: None,
        shutdown=lambda reason: reported.append(reason),
    )
    monkeypatch.setattr(worker, "report_worker_ready", report)
    monkeypatch.setattr(
        worker, "build_session_kwargs", lambda *args: pytest.fail("provider started")
    )
    await worker.run_integrated_job(ctx, binding())
    assert reported == [False, "integrated_startup_failed"]
