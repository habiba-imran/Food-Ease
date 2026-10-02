"""Phase 7 — EventBus, states, LiveKitRpcAdapter ↔ MockApp, metrics, inject."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from mock_app.participant import MockAppParticipant, start_dev_control_server

from foodease_agent.adapters.livekit_rpc import LiveKitRpcAdapter
from foodease_agent.adapters.transport import InProcessRoom
from foodease_agent.contract.enums import (
    ActionResultStatus,
    AssistantTranscriptPhase,
    EventType,
    Operation,
    ProductState,
)
from foodease_agent.contract.models import ActionRequestPayload
from foodease_agent.dialogue_planner import DialogueSuitePlanner
from foodease_agent.engine import ConversationEngine
from foodease_agent.events import EnvelopeValidationError, EventBus
from foodease_agent.faults import FAULTS
from foodease_agent.inbound import InboundHandler
from foodease_agent.product_state import ProductStateMachine

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.asyncio
async def test_v71_scripted_session_events_validate() -> None:
    bus = EventBus(session_id="s7")
    await bus.publish(
        EventType.AGENT_STATUS,
        {"state": ProductState.CONNECTING, "detail": "boot"},
    )
    await bus.publish(
        EventType.AGENT_STATUS,
        {"state": ProductState.READY_LISTENING},
    )
    await bus.publish(
        EventType.TRANSCRIPT_USER_PARTIAL,
        {"text": "show bur", "is_final": False},
        turn_id="t1",
    )
    await bus.publish(
        EventType.TRANSCRIPT_USER_FINAL,
        {"text": "show burgers", "is_final": True},
        turn_id="t1",
    )
    await bus.publish(
        EventType.TRANSCRIPT_ASSISTANT,
        {"text": "Here are burgers.", "phase": AssistantTranscriptPhase.COMPLETED},
        turn_id="t1",
    )
    await bus.publish(
        EventType.AGENT_ACTION_REQUEST,
        {
            "action_id": "a1",
            "operation": Operation.NAVIGATE,
            "arguments": {"target": "burgers"},
        },
    )
    assert all(e.schema_version == "1.0" for e in bus.history)
    # final replaced partial for turn
    partials = [
        e
        for e in bus.history
        if e.type == EventType.TRANSCRIPT_USER_PARTIAL and e.turn_id == "t1"
    ]
    assert partials == []


def test_v71_rejects_invalid_payload() -> None:
    bus = EventBus(session_id="s7")
    with pytest.raises(EnvelopeValidationError):
        bus.build(EventType.AGENT_STATUS, {"state": "not-a-real-state"})


def test_v72_state_machine_covers_va07() -> None:
    sm = ProductStateMachine()
    path = [
        (ProductState.CONNECTING, "start"),
        (ProductState.READY_LISTENING, "ready"),
        (ProductState.USER_SPEAKING, "speech"),
        (ProductState.THINKING, "llm"),
        (ProductState.WAITING_FOR_ACTION_RESULT, "rpc"),
        (ProductState.ASSISTANT_SPEAKING, "tts"),
        (ProductState.IDLE, "idle"),
        (ProductState.MUTED_PAUSED, "mute"),
        (ProductState.READY_LISTENING, "unmute"),
        (ProductState.RECONNECTING, "net"),
        (ProductState.READY_LISTENING, "back"),
        (ProductState.ERROR, "fatal"),
        (ProductState.ENDED, "bye"),
    ]
    # RECONNECTING from READY may be forced — still logged
    for st, reason in path:
        sm.transition(st, reason=reason)
    required = set(ProductState)
    # OFF_AWAITING_CONSENT is initial
    assert ProductState.OFF_AWAITING_CONSENT in sm.covered_states()
    missing = required - sm.covered_states()
    assert missing == set(), f"missing states: {missing}"


@pytest.mark.asyncio
async def test_v74_typed_input_same_route() -> None:
    room = InProcessRoom()
    room.register_participant("agent")
    mock = MockAppParticipant(room)
    await mock.start()
    adapter = LiveKitRpcAdapter(room, default_timeout_s=2.0)
    engine = ConversationEngine(adapter=adapter, planner=DialogueSuitePlanner())
    # typed path: text_input RPC then engine
    await adapter.send_text_input("show burgers")
    result = await engine.handle_text("show burgers")
    assert result.assistant_text
    assert "action_id" not in result.assistant_text.lower()


@pytest.mark.asyncio
async def test_v75_interim_final_replacement() -> None:
    bus = EventBus(session_id="s")
    await bus.publish(
        EventType.TRANSCRIPT_USER_PARTIAL,
        {"text": "hel", "is_final": False},
        turn_id="x",
    )
    await bus.publish(
        EventType.TRANSCRIPT_USER_FINAL,
        {"text": "hello", "is_final": True},
        turn_id="x",
    )
    texts = [e.payload["text"] for e in bus.history if e.type.value.startswith("transcript.user")]
    assert texts == ["hello"]


def test_v76_no_secrets_in_events() -> None:
    bus = EventBus(session_id="s")
    env = bus.build(
        EventType.AGENT_ERROR,
        {"code": "internal", "message": "Something went wrong.", "fatal": False},
    )
    blob = env.model_dump_json()
    assert "api_key" not in blob.lower()
    assert "Bearer" not in blob


@pytest.mark.asyncio
async def test_v77_conformance_livekit_rpc_mockapp() -> None:
    room = InProcessRoom()
    room.register_participant("agent")
    mock = MockAppParticipant(room)
    await mock.start()
    adapter = LiveKitRpcAdapter(room, default_timeout_s=1.0)

    a = await adapter.submit_action(
        ActionRequestPayload(
            action_id="idemp",
            operation=Operation.CART_ADD_ITEM,
            arguments={"item_id": "drink-cola", "quantity": 1},
        )
    )
    b = await adapter.submit_action(
        ActionRequestPayload(
            action_id="idemp",
            operation=Operation.CART_ADD_ITEM,
            arguments={"item_id": "drink-cola", "quantity": 1},
        )
    )
    assert a.model_dump(mode="json") == b.model_dump(mode="json")

    r0 = (await adapter.get_snapshot()).revision
    await adapter.submit_action(
        ActionRequestPayload(
            action_id="rev1",
            operation=Operation.CART_ADD_ITEM,
            arguments={"item_id": "side-salad", "quantity": 1},
        )
    )
    r1 = (await adapter.get_snapshot()).revision
    assert r1 > r0

    mock.set_scenario("never_reply")
    # never_reply on mock adapter — need short timeout
    adapter._default_timeout_s = 0.05  # noqa: SLF001
    # Reset scenario operations - NEVER_REPLY waits forever; use timeout on adapter side
    # MockAdapter NEVER_REPLY sleeps past timeout inside submit — MockApp awaits that
    to = await adapter.submit_action(
        ActionRequestPayload(
            action_id="to-1",
            operation=Operation.CART_ADD_ITEM,
            arguments={"item_id": "wrap-veg", "quantity": 1},
        ),
        timeout_s=0.05,
    )
    assert to.status == ActionResultStatus.TIMEOUT_UNKNOWN
    assert to.action_id == "to-1"


@pytest.mark.asyncio
async def test_v78_dialogue_over_transport() -> None:
    room = InProcessRoom()
    room.register_participant("agent")
    mock = MockAppParticipant(room)
    await mock.start()
    adapter = LiveKitRpcAdapter(room)
    engine = ConversationEngine(adapter=adapter, planner=DialogueSuitePlanner())
    # DS-06 style repair
    r1 = await engine.handle_text("show wraps")
    assert r1.assistant_text
    r2 = await engine.handle_text("no, I meant the wrap")
    assert r2.assistant_text
    # DS-17 style — checkout then change mind
    await engine.handle_text("add 1 Cola Can")
    r3 = await engine.handle_text("checkout")
    assert "demo" in r3.assistant_text.lower() or "total" in r3.assistant_text.lower()
    r4 = await engine.handle_text("wait, change the quantity")
    assert "demo order placed" not in r4.assistant_text.lower()


def test_v79_inject_metrics_jsonl(tmp_path: Path) -> None:
    out = tmp_path / "metrics.jsonl"
    import subprocess
    import sys

    subprocess.check_call(
        [sys.executable, str(ROOT / "tools" / "inject.py"), "--dry-run", "--out", str(out)],
        cwd=str(ROOT),
    )
    line = out.read_text(encoding="utf-8").strip().splitlines()[-1]
    row = json.loads(line)
    for key in (
        "turn_id",
        "session_id",
        "config_hash",
        "end_of_turn_delay_ms",
        "llm_first_token_ms",
        "tts_first_byte_ms",
        "audible_ttfa_ms",
    ):
        assert key in row


def test_dev_control_localhost_only() -> None:
    room = InProcessRoom()
    mock = MockAppParticipant(room)
    with pytest.raises(ValueError, match="localhost"):
        start_dev_control_server(mock, host="0.0.0.0")


@pytest.mark.asyncio
async def test_inbound_stale_revision() -> None:
    from foodease_agent.adapters.mock import MockAdapter

    handler = InboundHandler(last_revision=5)
    bus = EventBus(session_id="s")
    snap = await MockAdapter().get_snapshot()
    data = snap.model_dump(mode="json")
    data["revision"] = 3
    env = bus.build(EventType.APP_CONTEXT_UPDATED, data)
    handler.handle(env)
    assert 3 in handler.stale_ignored


@pytest.mark.asyncio
async def test_fault_drop_connection() -> None:
    room = InProcessRoom()
    room.register_participant("agent")
    mock = MockAppParticipant(room)
    await mock.start()
    adapter = LiveKitRpcAdapter(room)
    FAULTS.drop_connection = True
    try:
        r = await adapter.submit_action(
            ActionRequestPayload(
                action_id="f1",
                operation=Operation.GET_CART,
                arguments={},
            )
        )
        assert r.status == ActionResultStatus.TIMEOUT_UNKNOWN
    finally:
        FAULTS.reset()
