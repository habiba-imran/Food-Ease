"""Actual production v2 adapter and worker factory over a local fake RTC seat."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest
from foodease_contract.startup import StartupBinding

from foodease_agent.adapters.integrated import IntegratedRpcAdapter, action_request
from foodease_agent.adapters.integrated_startup import IntegratedRoomGate
from foodease_agent.integrated.agent import IntegratedFoodEaseAgent
from foodease_agent.integrated.runtime import LiveConversationRuntime
from test_integrated_runtime import Session, WebsiteAdapter, call, turn


class Room:
    def __init__(self):
        self.website = WebsiteAdapter()
        self.startup = StartupBinding.model_validate(
            {
                "schema_version": "2.0",
                "transport": "website",
                "consent": True,
                "generation": "generation",
                "request_id": "request",
                "worker_proof": "private-proof",
                "binding": {
                    "session_id": self.website.session_id,
                    "user_identity": "user",
                    "app_identity": "app",
                    "agent_identity": "agent",
                },
            }
        )
        self.local_participant = self.person("agent")
        self.local_participant.perform_rpc = self.perform_rpc
        self.local_participant.publish_data = self.publish_data
        self.remote_participants = {role: self.person(role) for role in ("app", "user")}
        self.handlers = {}
        self.calls = []
        self.published = []
        self.corrupt = None
        self.lost = False
        self.receipt = "good"

    def person(self, role):
        return SimpleNamespace(
            identity=role,
            attributes={
                "foodease.role": role,
                "foodease.session": self.website.session_id,
                "foodease.generation": "generation",
            },
        )

    def on(self, name, callback):
        self.handlers[name] = callback
        if name == "data_received":
            self.context()

    def off(self, name, callback):
        self.handlers.pop(name, None)

    def context(self, turn_id=None):
        snapshot = self.website.store.context(self.website.owner, self.website.session_id)
        self.send(
            {
                "schema_version": "2.0",
                "session_id": self.website.session_id,
                "event_id": f"context-{snapshot['revision']}",
                "turn_id": turn_id,
                "timestamp": "2026-10-17T12:00:00Z",
                "context_revision": snapshot["revision"],
                "type": "app.context_updated",
                "payload": snapshot,
            },
            "foodease.context.v2",
            "app",
        )

    def send(self, event, topic, sender="user"):
        callback = self.handlers.get("data_received")
        if callback:
            callback(
                SimpleNamespace(
                    topic=topic, participant=self.person(sender), data=json.dumps(event).encode()
                )
            )

    async def perform_rpc(self, *, destination_identity, method, payload, response_timeout):
        assert destination_identity == "app" and response_timeout == 5
        request = json.loads(payload)
        self.calls.append((method, request))
        if method == "foodease.action.v2":
            result = self.website.store.submit(self.website.owner, self.website.session_id, request)
            value = result.model_dump(mode="json")
            if request["payload"]["operation"] != "get_current_context":
                self.context(request["turn_id"])
                if self.lost:
                    raise TimeoutError("committed but reply lost")
        elif method == "foodease.action_status.v2":
            value = self.website.store.lookup(
                self.website.owner,
                self.website.session_id,
                request["action_id"],
                request["event_id"],
            ).model_dump(mode="json")
        elif method == "foodease.present_summary.v2":
            value = {k: v for k, v in request.items() if k != "text"}
            value["delivered"] = True
            if self.receipt == "wrong":
                value["summary_id"] = "other-summary"
            elif self.receipt == "missing":
                raise TimeoutError("no renderer acknowledgement")
        else:
            raise AssertionError(method)
        if self.corrupt:
            value[self.corrupt] = "foreign"
        return json.dumps(value)

    async def publish_data(self, raw, **kwargs):
        self.published.append((json.loads(raw), kwargs))

    def control(self, intent, mode=None, *, sender="user", event_id="control"):
        self.send(
            {
                "schema_version": "2.0",
                "session_id": self.website.session_id,
                "event_id": event_id,
                "timestamp": "2026-10-17T12:00:00Z",
                "type": "app.control",
                "payload": {"intent": intent, "mode": mode},
            },
            "foodease.control.v2",
            sender,
        )


@pytest.mark.asyncio
async def test_production_rpc_adapter_real_authority_context_push_and_lost_reply():
    room = Room()
    gate = IntegratedRoomGate(room, room.startup)
    adapter = IntegratedRpcAdapter(gate)
    runtime = LiveConversationRuntime(IntegratedFoodEaseAgent(), Session(), adapter, gate=gate)
    await runtime.prepare()
    runtime._started = True  # Fake session is already usable; real startup tested below.
    await runtime.select_mode("voice")
    try:
        room.lost = True
        item = runtime.snapshot.visible_items[0].item_id
        result = await call(runtime, "cart_add_item", item_id=item, quantity=2)
        assert result["status"] == "success"
        assert runtime.snapshot.cart.lines[0].quantity == 2
        mutations = [
            req
            for method, req in room.calls
            if method == "foodease.action.v2" and req["payload"]["operation"] == "cart.add_item"
        ]
        assert len(mutations) == 1 and not runtime.pending
        assert any(method == "foodease.action_status.v2" for method, _ in room.calls)
        context = await turn(runtime)
        await room.website.manual("search_menu", {"query": "pizza"})
        room.context("manual")
        assert context.speech_handle.interrupted
        assert runtime.snapshot.search_query == "pizza"
        room.control("switch_mode", "typed", sender="app")
        assert runtime.mode == "voice"
        room.control("switch_mode", "typed")
        assert runtime.mode == "typed" and not runtime.session.input.enabled
        assert (await runtime.agent.cart_add_item(context, item))["status"] != "success"
        await asyncio.sleep(0)
        room.control("switch_mode", "manual", event_id="manual")
        assert runtime.closed and gate.closed
        assert not runtime.session.output.enabled
    finally:
        gate.close()
        await runtime.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["session_id", "reply_to", "turn_id"])
async def test_uncorrelated_rpc_results_are_rejected(field):
    room = Room()
    gate = IntegratedRoomGate(room, room.startup)
    adapter = IntegratedRpcAdapter(gate)
    try:
        snapshot = await adapter.get_snapshot()
        room.corrupt = field
        request = action_request(room.website.session_id, "turn", snapshot.revision, "get_cart", {})
        with pytest.raises(ValueError):
            await adapter.submit(request)
    finally:
        gate.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "receipt, expected", [("good", True), ("wrong", False), ("missing", False)]
)
async def test_typed_summary_receipt_is_exact_and_fails_closed(receipt, expected):
    room = Room()
    gate = IntegratedRoomGate(room, room.startup)
    adapter = IntegratedRpcAdapter(gate)
    try:
        room.receipt = receipt
        delivered = await adapter.present_summary(
            turn_id="turn",
            summary_id="summary",
            summary_revision=3,
            summary_hash="hash",
            text="Your total is 100 rupees. Place this demo order?",
        )
        assert delivered is expected
    finally:
        gate.close()


@pytest.mark.asyncio
async def test_actual_worker_entrypoint_attaches_runtime_and_waits_for_ready(monkeypatch):
    from foodease_agent import worker
    from foodease_agent.integrated import factory
    from foodease_agent.session import SessionBundle
    from test_phase5_voice import _settings

    room, session = Room(), Session()
    order = []
    monkeypatch.setenv("FOODEASE_APP_TRANSPORT", "website")
    monkeypatch.setattr(factory, "load_config", lambda: _settings(preemptive_generation=True))

    def bundle(settings):
        assert settings.preemptive_generation is False
        order.append("providers_prepared")
        return SessionBundle({}, "A", False)

    monkeypatch.setattr(factory, "build_session_kwargs", bundle)
    monkeypatch.setattr(factory, "AgentSession", lambda **kwargs: session)

    async def ready(*args, **kwargs):
        assert kwargs["runtime_ready"] is True
        assert not hasattr(session, "started") and not session.spoken
        assert not session.input.enabled
        order.append("ready_ack")
        return {"greeting_allowed": True}

    monkeypatch.setattr(worker, "report_worker_ready", ready)
    callbacks = []

    async def connect(**kwargs):
        order.append("connect")

    ctx = SimpleNamespace(
        room=room,
        job=SimpleNamespace(metadata=room.startup.model_dump_json()),
        proc=SimpleNamespace(userdata={}),
        connect=connect,
        add_shutdown_callback=callbacks.append,
        shutdown=lambda reason: order.append(reason),
    )
    await worker.entrypoint(ctx)  # type: ignore[arg-type]
    try:
        assert order == ["connect", "providers_prepared", "ready_ack"]
        assert isinstance(session.started["agent"], IntegratedFoodEaseAgent)
        assert session.started["record"] is False
        assert session.started["session_host"] is False
        options = session.started["room_options"]
        assert options.text_input is False and options.participant_identity == "user"
        runtime = session.started["agent"].runtime
        assert runtime.mode is None and not session.spoken
        room.control("switch_mode", "voice")
        await asyncio.sleep(0)
        assert runtime.mode == "voice" and session.input.enabled
        await call(runtime, "get_cart")
        room.handlers["participant_disconnected"](room.person("user"))
        assert runtime.closed and not session.input.enabled
    finally:
        await callbacks[0]()
        assert session.closed
