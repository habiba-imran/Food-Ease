"""Latency work removes round trips without relaxing application/turn validation."""

import asyncio
import json
from uuid import uuid4

import pytest
from livekit.agents import AgentSession, StopResponse, llm
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS

from foodease_agent.adapters.integrated import IntegratedRpcAdapter
from foodease_agent.adapters.integrated_startup import IntegratedRoomGate
from foodease_agent.integrated.agent import IntegratedFoodEaseAgent
from foodease_agent.integrated.runtime import LiveConversationRuntime
from test_integrated_rpc_worker import Room
from test_integrated_runtime import Session, WebsiteAdapter, call, turn


@pytest.mark.parametrize("finish_turn,expected_generations", [(False, 2), (True, 1)])
async def test_native_sdk_verified_cart_reply_can_skip_second_model_request(
    finish_turn, expected_generations
):
    class LocalLLM(llm.LLM):
        calls = 0

        def chat(self, *, chat_ctx, tools=None, conn_options=DEFAULT_API_CONNECT_OPTIONS, **kw):
            self.calls += 1
            return Stream(self, chat_ctx=chat_ctx, tools=tools or [], conn_options=conn_options)

    class Stream(llm.LLMStream):
        async def _run(self):
            if not any(isinstance(i, llm.FunctionCallOutput) for i in self._chat_ctx.items):
                delta = llm.ChoiceDelta(
                    tool_calls=[
                        llm.FunctionToolCall(
                            name="get_cart",
                            arguments=json.dumps({"finish_turn": finish_turn}),
                            call_id=uuid4().hex,
                        )
                    ]
                )
            else:
                delta = llm.ChoiceDelta(content="آپ کا کارٹ خالی ہے۔")
            self._event_ch.send_nowait(llm.ChatChunk(id=uuid4().hex, delta=delta))

    provider = LocalLLM()
    session = AgentSession(llm=provider)
    adapter = WebsiteAdapter()
    runtime = LiveConversationRuntime(IntegratedFoodEaseAgent(language="ur"), session, adapter)
    await runtime.prepare()
    await runtime.select_mode("typed")
    try:
        await session.start(agent=runtime.agent)
        handle = await runtime.input_text(
            "کارٹ میں کیا ہے؟", "latency-turn", runtime.snapshot.revision
        )
        await asyncio.wait_for(handle.wait_for_playout(), 10)
        # say() is scheduled independently of the tool's original generation handle.
        for _ in range(100):
            if runtime._last_completed:
                break
            await asyncio.sleep(0.01)
        assert provider.calls == expected_generations
        assert len(adapter.requests) == 1
        assert runtime._last_completed and "خالی" in runtime._last_completed[0]
    finally:
        await runtime.close()


async def test_direct_unknown_outcome_is_spoken_without_success_or_mutation_retry():
    adapter = WebsiteAdapter()
    original_lookup = adapter.lookup
    attempts = 0

    async def lost(request):
        nonlocal attempts
        attempts += 1
        raise TimeoutError()

    async def lookup(action_id):
        return (await original_lookup(action_id)).model_copy(update={"state": "pending"})

    runtime = LiveConversationRuntime(IntegratedFoodEaseAgent(language="ur"), Session(), adapter)
    await runtime.prepare()
    await runtime.select_mode("voice")
    adapter.submit, adapter.lookup = lost, lookup
    try:
        context = await turn(runtime, "کولا شامل کرو")
        with pytest.raises(StopResponse):
            await runtime.agent.cart_add_item(context, "drink-cola", 1, finish_turn=True)
        assert attempts == 1 and runtime.pending and not runtime.snapshot.cart.lines
        assert "دوبارہ نہیں" in runtime.session.spoken[-1]
        assert "شامل کر دیا" not in runtime.session.spoken[-1]
    finally:
        await runtime.close()


async def test_bound_post_action_context_removes_only_the_redundant_rpc():
    room = Room()
    gate = IntegratedRoomGate(room, room.startup)
    adapter = IntegratedRpcAdapter(gate)
    runtime = LiveConversationRuntime(IntegratedFoodEaseAgent(), Session(), adapter, gate=gate)
    await runtime.prepare()
    await runtime.select_mode("voice")
    room.calls.clear()
    try:
        result = await call(runtime, "cart_add_item", item_id="drink-cola", quantity=2)
        assert result["status"] == "success"
        assert runtime.snapshot.cart.lines[0].quantity == 2
        assert [request["payload"]["operation"] for _, request in room.calls] == [
            "get_current_context",
            "cart.add_item",
        ]
    finally:
        await runtime.close()
        gate.close()


async def test_missing_published_context_falls_back_to_read_without_replaying_write():
    room = Room()
    gate = IntegratedRoomGate(room, room.startup)
    adapter = IntegratedRpcAdapter(gate)
    runtime = LiveConversationRuntime(IntegratedFoodEaseAgent(), Session(), adapter, gate=gate)
    await runtime.prepare()
    await runtime.select_mode("voice")
    room.calls.clear()
    room.context = lambda turn_id=None: None
    try:
        result = await call(runtime, "cart_add_item", item_id="drink-cola", quantity=1)
        assert result["status"] == "success"
        assert [request["payload"]["operation"] for _, request in room.calls] == [
            "get_current_context",
            "cart.add_item",
            "get_current_context",
        ]
        assert runtime.snapshot.cart.lines[0].quantity == 1
    finally:
        await runtime.close()
        gate.close()


async def test_direct_replies_keep_stock_and_delivery_guards_and_emit_no_late_success():
    adapter = WebsiteAdapter()
    runtime = LiveConversationRuntime(IntegratedFoodEaseAgent(language="ur"), Session(), adapter)
    await runtime.prepare()
    await runtime.select_mode("voice")
    try:
        domain = adapter.store._sessions[adapter.session_id].domain
        domain.menu_by_id["drink-cola"].available = False
        context = await turn(runtime, "دو کولا شامل کرو")
        with pytest.raises(StopResponse):
            await runtime.agent.cart_add_item(context, "drink-cola", 2, finish_turn=True)
        assert not runtime.snapshot.cart.lines
        assert "دستیاب نہیں" in runtime.session.spoken[-1]

        adapter.store._sessions[adapter.session_id].domain.menu_by_id["drink-cola"].available = True
        context = await turn(runtime, "دو کولا شامل کرو")
        with pytest.raises(StopResponse):
            await runtime.agent.cart_add_item(context, "drink-cola", 2, finish_turn=True)
        assert runtime.snapshot.cart.lines[0].quantity == 2
        before = len(runtime.session.spoken)
        context = await turn(runtime, "کارٹ خالی کرو")
        with pytest.raises(StopResponse):
            await runtime.agent.cart_get_clear_summary(context, finish_turn=True)
        await asyncio.sleep(0)
        assert len(runtime.session.spoken) == before + 1
        assert "خالی" in runtime.session.spoken[-1] and runtime.snapshot.cart.lines
        assert runtime.confirmation.summary_spoken

        assert runtime.active_turn is not None
        runtime.discard_turn(runtime.active_turn.id)
        runtime.finish_response(context, "cart.add_item", {"status": "success", "say": "wrong"})
        assert len(runtime.session.spoken) == before + 1
    finally:
        await runtime.close()
