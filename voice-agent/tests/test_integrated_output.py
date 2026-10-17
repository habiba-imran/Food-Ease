"""Phase 5 canonical browser output; final captions follow actual handle outcome."""

import asyncio
import json
from types import SimpleNamespace

import pytest
from foodease_contract.models import decode_event

from foodease_agent.adapters.integrated import IntegratedRpcAdapter
from foodease_agent.adapters.integrated_startup import IntegratedRoomGate
from test_integrated_rpc_worker import Room
from test_integrated_runtime import turn

pytest_plugins = ("test_integrated_runtime",)


@pytest.mark.asyncio
async def test_publisher_uses_canonical_events_topic_and_valid_wire_timestamp():
    room = Room()
    gate = IntegratedRoomGate(room, room.startup)
    adapter = IntegratedRpcAdapter(gate)
    await adapter.publish_event(
        "transcript.assistant",
        {
            "utterance_id": "utterance",
            "text": "Your current cart is empty.",
            "phase": "completed",
        },
        turn_id="turn",
        revision=1,
    )
    event, options = room.published[-1]
    assert decode_event(event).type == "transcript.assistant"
    assert options["topic"] == "foodease.events.v2"
    await adapter.publish_control("switch_mode", "typed")
    assert room.published[-1][1]["topic"] == "foodease.events.v2"
    assert "worker_proof" not in json.dumps(room.published)
    gate.close()


@pytest.mark.asyncio
async def test_partial_user_captions_have_one_identity_without_provider_ids(runtime):
    runtime.on_user_transcript(SimpleNamespace(transcript="show", is_final=False, item_id=None))
    runtime.on_user_transcript(
        SimpleNamespace(transcript="show burgers", is_final=True, item_id=None)
    )
    await asyncio.sleep(0)
    events = [entry for entry in runtime.adapter.events if entry[0].startswith("transcript.user.")]
    assert [entry[0] for entry in events] == ["transcript.user.partial", "transcript.user.final"]
    assert events[0][1]["utterance_id"] == events[1][1]["utterance_id"]


@pytest.mark.asyncio
async def test_assistant_interruption_replaces_intended_caption_with_actual_partial(runtime):
    from livekit.agents import llm

    context = await turn(runtime)
    handle = context.speech_handle
    runtime.on_caption_fragment(handle.id, "Your cart has two wraps and the total is")
    handle.chat_items = [llm.ChatMessage(role="assistant", content=["Your cart has two wraps"])]
    handle.interrupt()
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    events = [entry for entry in runtime.adapter.events if entry[0] == "transcript.assistant"]
    assert events[-1][1]["phase"] == "interrupted"
    assert events[-1][1]["text"] == "Your cart has two wraps"
