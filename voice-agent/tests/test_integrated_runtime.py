"""Final Phase 4: real SDK tools/callbacks, real website authority, fake media only."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from foodease_contract.models import ActionRequestEvent, ContextSnapshot
from foodease_website.catalog import load_catalog
from foodease_website.sessions import SessionStore
from livekit.agents import StopResponse, llm

from foodease_agent.integrated.agent import IntegratedFoodEaseAgent
from foodease_agent.integrated.runtime import LiveConversationRuntime


class Speech:
    def __init__(self, text="", *, complete=False, interrupted=False, error=None):
        self.id = uuid4().hex
        self.text = text
        self.interrupted = interrupted
        self.error = error
        self.chat_items = [llm.ChatMessage(role="assistant", content=[text])] if text else []
        self.future = asyncio.get_running_loop().create_future()
        if complete:
            self.future.set_result(None)

    def __await__(self):
        return self.future.__await__()

    async def wait_for_playout(self):
        await self.future

    def done(self):
        return self.future.done()

    def exception(self):
        return self.error

    def add_done_callback(self, callback):
        self.future.add_done_callback(lambda _: callback(self))

    def interrupt(self, **kwargs):
        self.interrupted = True
        if not self.future.done():
            self.future.set_result(None)


class Audio:
    enabled = True
    audio = object()  # fake attached audio sink, with completion driven by Speech

    @property
    def audio_enabled(self):
        return self.enabled

    def set_audio_enabled(self, enabled):
        self.enabled = enabled


class Session:
    def __init__(self):
        self.handlers = {}
        self.spoken = []
        self.generated = []
        self.handles = []
        self.input, self.output = Audio(), Audio()
        self.next_interrupted = False
        self.next_error = None
        self.closed = False
        self.tts = SimpleNamespace(update_options=self.speed)
        self.speeds = []

    def speed(self, **kwargs):
        self.speeds.append(kwargs)

    def on(self, event, cb):
        self.handlers[event] = cb

    def off(self, event, cb):
        self.handlers.pop(event, None)

    def emit(self, event, **kwargs):
        if event in self.handlers:
            self.handlers[event](SimpleNamespace(**kwargs))

    def say(self, text, **kwargs):
        speech = Speech(
            text, complete=True, interrupted=self.next_interrupted, error=self.next_error
        )
        self.next_interrupted, self.next_error = False, None
        self.spoken.append(text)
        self.handles.append(speech)
        self.emit("speech_created", speech_handle=speech, source="say", user_initiated=True)
        return speech

    def generate_reply(self, **kwargs):
        speech = Speech()
        self.generated.append(kwargs)
        self.handles.append(speech)
        self.emit(
            "speech_created", speech_handle=speech, source="generate_reply", user_initiated=True
        )
        return speech

    def interrupt(self, **kwargs):
        for handle in self.handles:
            if not handle.done():
                handle.interrupt()
        future = asyncio.get_running_loop().create_future()
        future.set_result(None)
        return future

    async def start(self, **kwargs):
        self.started = kwargs

    async def aclose(self):
        self.closed = True


class WebsiteAdapter:
    """Test adapter uses Phase 2 copy/validate/commit, never MockAdapter."""

    def __init__(self):
        root = Path(__file__).resolve().parents[2]
        self.store = SessionStore(load_catalog(root / "zainab-pack/catalog-seed.json"))
        self.owner = self.store.new_owner()
        self.session_id = self.store.create(self.owner).session_id
        self.requests = []
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.release.set()
        self.lose_reply = False
        self.text_delivery = False
        self.controls = []
        self.events = []

    async def get_snapshot(self):
        return ContextSnapshot.model_validate(self.store.context(self.owner, self.session_id))

    async def submit(self, request):
        self.requests.append(request)
        self.started.set()
        await self.release.wait()
        result = self.store.submit(self.owner, self.session_id, request.model_dump(mode="json"))
        if self.lose_reply:
            raise TimeoutError("reply lost after commit")
        return result

    async def lookup(self, action_id):
        return self.store.lookup(self.owner, self.session_id, action_id, uuid4().hex)

    async def present_summary(self, **kwargs):
        return self.text_delivery

    async def publish_control(self, intent, mode=None):
        self.controls.append((intent, mode))

    async def publish_event(self, event_type, payload, **kwargs):
        self.events.append((event_type, payload, kwargs))

    async def manual(self, operation, arguments):
        snapshot = await self.get_snapshot()
        request = ActionRequestEvent.model_validate(
            {
                "schema_version": "2.0",
                "session_id": self.session_id,
                "event_id": uuid4().hex,
                "turn_id": "manual",
                "type": "agent.action_request",
                "timestamp": "2026-10-17T12:00:00Z",
                "context_revision": snapshot.revision,
                "payload": {
                    "action_id": uuid4().hex,
                    "operation": operation,
                    "arguments": arguments,
                },
            }
        )
        return self.store.submit(self.owner, self.session_id, request.model_dump(mode="json"))


@pytest.fixture
async def runtime():
    adapter, session = WebsiteAdapter(), Session()
    agent = IntegratedFoodEaseAgent()
    runtime = LiveConversationRuntime(agent, session, adapter, speech_controls=frozenset({"speed"}))
    await runtime.prepare()
    await runtime.select_mode("voice")
    yield runtime
    adapter.release.set()
    await runtime.close()


async def turn(runtime, text="show the menu", *, source="audio"):
    message = llm.ChatMessage(role="user", content=[text])
    if source == "audio":
        with pytest.raises(StopResponse):
            await runtime.agent.on_user_turn_completed(llm.ChatContext(), message)
    else:
        await runtime.input_text(text, message.id, runtime.snapshot.revision)
    assert runtime.session.generated
    handle = runtime.session.handles[-1]
    return SimpleNamespace(session=runtime.session, speech_handle=handle)


async def call(runtime, name, text="help me order", **arguments):
    context = await turn(runtime, text)
    return await getattr(runtime.agent, name)(context, **arguments)


@pytest.mark.asyncio
async def test_thirteen_actual_tools_return_real_facts_and_cart_math(runtime):
    agent = runtime.agent
    assert len(agent.tools) == 13
    assert (await call(runtime, "navigate", target="menu"))["status"] == "success"
    filtered = await call(runtime, "filter_menu", vegetarian=True, max_price_pkr=500.0)
    assert filtered["facts"]["items"]
    assert all(
        i["price"] <= 500 and "vegetarian" in i["descriptors"] for i in filtered["facts"]["items"]
    )
    await call(runtime, "filter_menu", clear=True)
    found = await call(runtime, "search_menu", query="burger")
    item = found["facts"]["items"][0]
    assert (await call(runtime, "select_item", item_id=item["item_id"]))["status"] == "success"
    details = await call(runtime, "get_item_details", item_id=item["item_id"])
    assert details["facts"]["name"] == item["name"]
    assert "ingredients_available" in details["facts"]
    added = await call(runtime, "cart_add_item", item_id=item["item_id"], quantity=2)
    assert added["facts"]["subtotal"] == item["price"] * 2
    assert "2" in added["say"] and str(int(added["facts"]["total"])) in added["say"]
    changed = await call(runtime, "cart_set_quantity", item_id=item["item_id"], quantity=3)
    assert changed["facts"]["lines"][0]["quantity"] == 3
    assert (await call(runtime, "get_cart"))["facts"] == changed["facts"]
    assert (await call(runtime, "get_current_context"))["facts"]["snapshot"]["cart"] == changed[
        "facts"
    ]
    assert (await call(runtime, "cart_remove_item", item_id=item["item_id"]))["facts"][
        "lines"
    ] == []
    assert (await call(runtime, "undo_last_reversible_action"))["facts"]["lines"][0][
        "quantity"
    ] == 3
    summary = await call(runtime, "checkout_get_summary", text="check out")
    assert "confirmation_token" not in json.dumps(summary)
    receipt = await call(runtime, "checkout_submit_demo_order", text="yes")
    assert receipt["status"] == "success" and receipt["facts"]["demo"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "answer", ["yes, but change it to two", "yes please remove the burger", "yesterday", "no"]
)
async def test_corrections_and_casual_yes_never_authorize_checkout(runtime, answer):
    item = runtime.snapshot.visible_items[0].item_id
    await call(runtime, "cart_add_item", item_id=item)
    await call(runtime, "checkout_get_summary", text="check out")
    result = await call(runtime, "checkout_submit_demo_order", text=answer)
    assert result["status"] != "success"
    assert not any(
        r.payload.operation == "checkout.submit_demo_order" for r in runtime.adapter.requests
    )
    result = await call(runtime, "checkout_submit_demo_order", text="yes")
    assert result["status"] != "success", "a correction must invalidate the previous summary"


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["interrupt", "error"])
async def test_summary_must_finish_playout_before_confirmation(runtime, failure):
    await call(runtime, "cart_add_item", item_id=runtime.snapshot.visible_items[0].item_id)
    if failure == "interrupt":
        runtime.session.next_interrupted = True
    else:
        runtime.session.next_error = RuntimeError("TTS failed")
    await call(runtime, "checkout_get_summary", text="check out")
    result = await call(runtime, "checkout_submit_demo_order", text="yes")
    assert result["status"] != "success"
    assert not any(
        r.payload.operation == "checkout.submit_demo_order" for r in runtime.adapter.requests
    )


@pytest.mark.asyncio
async def test_stale_discarded_uncommitted_and_late_turns_cannot_mutate(runtime):
    old = await turn(runtime, "add the first one")
    runtime.uncommit_turn(runtime.active_turn.id)
    assert (await runtime.agent.cart_add_item(old, runtime.snapshot.visible_items[0].item_id))[
        "status"
    ] != "success"
    await turn(runtime, "show me more")
    assert (await runtime.agent.cart_add_item(old, runtime.snapshot.visible_items[0].item_id))[
        "status"
    ] != "success"
    current = await turn(runtime)
    runtime.discard_turn(runtime.active_turn.id)
    assert (await runtime.agent.navigate(current, "cart"))["status"] != "success"
    current = await turn(runtime)
    await runtime.adapter.manual("navigate", {"target": "cart"})
    runtime.on_context(await runtime.adapter.get_snapshot())
    assert (await runtime.agent.cart_add_item(current, runtime.snapshot.visible_items[0].item_id))[
        "status"
    ] != "success"
    assert runtime.adapter.requests == []


@pytest.mark.asyncio
async def test_owned_pending_task_survives_tool_cancellation_and_manual_mode(runtime):
    context = await turn(runtime, "add one")
    runtime.adapter.release.clear()
    task = asyncio.create_task(
        runtime.agent.cart_add_item(context, runtime.snapshot.visible_items[0].item_id)
    )
    await runtime.adapter.started.wait()
    assert len(runtime.pending) == 1
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await runtime.select_mode("manual")
    runtime.adapter.release.set()
    await runtime.drain()
    assert len((await runtime.adapter.get_snapshot()).cart.lines) == 1
    assert len(runtime.adapter.requests) == 1
    assert not runtime.pending
    assert runtime.session.spoken == [], "late result cannot resume audio after manual"


@pytest.mark.asyncio
async def test_lost_mutation_reply_reconciles_original_result_without_resubmitting(runtime):
    runtime.adapter.lose_reply = True
    result = await call(runtime, "cart_add_item", item_id=runtime.snapshot.visible_items[0].item_id)
    assert result["status"] == "success"
    assert len(runtime.adapter.requests) == 1
    assert not runtime.pending


@pytest.mark.asyncio
async def test_controls_are_real_effects_and_modes_enforce_input_source(runtime):
    await turn(runtime, "tell me about the menu")
    old = runtime.session.handles[-1]
    generated = len(runtime.session.generated)
    await runtime.input_text("stop", "stop-turn", runtime.snapshot.revision, source="audio")
    assert old.interrupted and len(runtime.session.generated) == generated
    runtime.on_delivered("Here is the menu.", runtime.snapshot.revision)
    await runtime.input_text("repeat", "repeat-turn", runtime.snapshot.revision, source="audio")
    assert runtime.session.spoken[-1] == "Here is the menu."
    await runtime.input_text("go back", "back-turn", runtime.snapshot.revision, source="audio")
    assert runtime.adapter.requests[-1].payload.arguments == {"target": "back"}
    await runtime.input_text("slower", "speed-turn", runtime.snapshot.revision, source="audio")
    assert runtime.session.speeds[-1]["speed"] < 1
    await runtime.input_text("louder", "volume-turn", runtime.snapshot.revision, source="audio")
    assert "device" in runtime.session.spoken[-1].lower()
    await runtime.input_text("manual", "manual-turn", runtime.snapshot.revision, source="audio")
    assert runtime.mode == "manual" and not runtime.session.input.enabled
    await runtime.input_text("add one", "late-audio", runtime.snapshot.revision, source="audio")
    assert len(runtime.session.generated) == generated


@pytest.mark.asyncio
async def test_context_reaches_llm_and_manual_change_invalidates_reference_and_speech(runtime):
    await call(runtime, "search_menu", query="burger")
    await turn(runtime)
    handle = runtime.session.handles[-1]
    ctx = llm.ChatContext()
    runtime.agent.reasoning_context(ctx)
    text = json.dumps(ctx.to_dict())
    assert runtime.snapshot.visible_items[0].name in text
    assert "UNTRUSTED_APPLICATION_DATA" in text
    await runtime.adapter.manual("search_menu", {"query": "pizza"})
    runtime.on_context(await runtime.adapter.get_snapshot())
    assert handle.interrupted
    assert not runtime.references.items
    ctx = llm.ChatContext()
    runtime.agent.reasoning_context(ctx)
    assert "pizza" in json.dumps(ctx.to_dict()).lower()


@pytest.mark.asyncio
async def test_typed_summary_requires_render_ack_and_cart_changes_invalidate(runtime):
    await runtime.select_mode("typed")
    item = runtime.snapshot.visible_items[0].item_id
    with pytest.raises(StopResponse):
        await runtime.agent.on_user_turn_completed(
            llm.ChatContext(), llm.ChatMessage(role="user", content=["add one"])
        )
    assert runtime.adapter.requests == []
    context = await turn(runtime, "add one", source="text")
    await runtime.agent.cart_add_item(context, item)
    context = await turn(runtime, "check out", source="text")
    await runtime.agent.checkout_get_summary(context)
    context = await turn(runtime, "yes", source="text")
    assert (await runtime.agent.checkout_submit_demo_order(context))["status"] != "success"
    runtime.adapter.text_delivery = True
    context = await turn(runtime, "check out", source="text")
    await runtime.agent.checkout_get_summary(context)
    await runtime.adapter.manual("cart.set_quantity", {"item_id": item, "quantity": 2})
    runtime.on_context(await runtime.adapter.get_snapshot())
    context = await turn(runtime, "yes", source="text")
    assert (await runtime.agent.checkout_submit_demo_order(context))["status"] != "success"


@pytest.mark.asyncio
async def test_actual_user_speech_lifecycle_preserves_only_delivered_confirmation(runtime):
    await call(runtime, "cart_add_item", item_id=runtime.snapshot.visible_items[0].item_id)
    await call(runtime, "checkout_get_summary", text="check out")
    runtime.session.emit("user_state_changed", new_state="speaking")
    runtime.session.emit("user_state_changed", new_state="listening")
    context = await turn(runtime, "yes")
    assert (await runtime.agent.checkout_submit_demo_order(context))["status"] == "success"


@pytest.mark.asyncio
async def test_queued_unheard_summary_cannot_confirm_even_if_completion_arrives_late(runtime):
    await call(runtime, "cart_add_item", item_id=runtime.snapshot.visible_items[0].item_id)
    original_say = runtime.session.say
    queued = Speech()

    def delayed(text, **kwargs):
        queued.text = text
        runtime.session.handles.append(queued)
        runtime.session.emit(
            "speech_created", speech_handle=queued, source="say", user_initiated=True
        )
        return queued

    runtime.session.say = delayed
    await call(runtime, "checkout_get_summary", text="check out")
    assert not runtime.confirmation.summary_spoken
    runtime.session.say = original_say
    runtime.session.emit("user_state_changed", new_state="speaking")
    context = await turn(runtime, "yes")
    assert (await runtime.agent.checkout_submit_demo_order(context))["status"] != "success"
    await asyncio.sleep(0)
    assert not runtime.confirmation.summary_spoken


@pytest.mark.asyncio
async def test_idle_is_finite_and_tracks_real_activity_modes_and_disconnect(runtime):
    from foodease_agent.idle import FakeClock, IdlePromptController

    clock = FakeClock()
    runtime.idle = IdlePromptController(clock=clock)
    runtime.mode = None
    runtime.idle.on_assistant_finished()
    clock.advance(100)
    assert await runtime.poll_idle() is None
    await runtime.select_mode("voice")
    runtime.session.emit("user_state_changed", new_state="speaking")
    clock.advance(100)
    assert await runtime.poll_idle() is None
    runtime.session.emit("user_state_changed", new_state="listening")
    clock.advance(12)
    assert await runtime.poll_idle()
    await asyncio.sleep(0)
    clock.advance(30)
    assert await runtime.poll_idle()
    await asyncio.sleep(0)
    clock.advance(1000)
    assert await runtime.poll_idle() is None
    assert len(runtime.session.spoken) == 2
    await runtime.select_mode("manual")
    assert await runtime.poll_idle() is None
    runtime.end_local()
    assert not runtime.session.input.enabled and not runtime.session.output.enabled
    assert await runtime.poll_idle() is None


@pytest.mark.asyncio
async def test_pause_resume_undo_and_tips_controls(runtime):
    item = runtime.snapshot.visible_items[0].item_id
    await call(runtime, "cart_add_item", item_id=item)
    await runtime.input_text("undo", "undo-turn", runtime.snapshot.revision, source="audio")
    assert not (await runtime.adapter.get_snapshot()).cart.lines
    await runtime.input_text("pause", "pause-turn", runtime.snapshot.revision, source="audio")
    assert runtime.paused and not runtime.session.output.enabled
    generated = len(runtime.session.generated)
    await runtime.input_text("find pizza", "paused-turn", runtime.snapshot.revision, source="audio")
    assert len(runtime.session.generated) == generated
    await runtime.input_text("resume", "resume-turn", runtime.snapshot.revision, source="audio")
    assert not runtime.paused and runtime.session.output.enabled
    await runtime.input_text("pause tips", "tips-turn", runtime.snapshot.revision, source="audio")
    assert runtime.tips_paused
    await runtime.input_text(
        "resume tips", "tips-resume", runtime.snapshot.revision, source="audio"
    )
    assert not runtime.tips_paused


@pytest.mark.asyncio
async def test_pending_unknown_blocks_new_actions_and_never_uses_old_success(runtime):
    from foodease_contract.models import LookupResponse

    runtime.adapter.lose_reply = True

    async def pending(action_id):
        return LookupResponse.model_validate(
            {
                "schema_version": "2.0",
                "session_id": runtime.snapshot.session_id,
                "event_id": "lookup-result",
                "reply_to": "lookup",
                "timestamp": "2026-10-17T12:00:00Z",
                "action_id": action_id,
                "state": "pending",
            }
        )

    runtime.adapter.lookup = pending
    result = await call(runtime, "cart_add_item", item_id=runtime.snapshot.visible_items[0].item_id)
    assert result["status"] == "timeout_unknown"
    assert len(runtime.pending) == 1 and len(runtime.reconciler.pending) == 1
    result = await call(runtime, "cart_add_item", item_id=runtime.snapshot.visible_items[0].item_id)
    assert result["status"] == "pending"
    assert len(runtime.adapter.requests) == 1


@pytest.mark.asyncio
async def test_actual_sdk_streaming_llm_and_tool_continuation_use_current_context():
    from livekit.agents import AgentSession
    from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS

    class LocalLLM(llm.LLM):
        def __init__(self):
            super().__init__()
            self.contexts = []

        def chat(self, *, chat_ctx, tools=None, conn_options=DEFAULT_API_CONNECT_OPTIONS, **kwargs):
            self.contexts.append(chat_ctx.copy())
            return LocalStream(
                self, chat_ctx=chat_ctx, tools=tools or [], conn_options=conn_options
            )

    class LocalStream(llm.LLMStream):
        async def _run(self):
            if not any(isinstance(i, llm.FunctionCallOutput) for i in self._chat_ctx.items):
                delta = llm.ChoiceDelta(
                    tool_calls=[
                        llm.FunctionToolCall(name="get_cart", arguments="{}", call_id=uuid4().hex)
                    ]
                )
            else:
                delta = llm.ChoiceDelta(content="Your cart is empty. What would you like to order?")
            self._event_ch.send_nowait(llm.ChatChunk(id=uuid4().hex, delta=delta))

    provider = LocalLLM()
    session = AgentSession(llm=provider)
    adapter = WebsiteAdapter()
    agent = IntegratedFoodEaseAgent()
    runtime = LiveConversationRuntime(agent, session, adapter)
    await runtime.prepare()
    await runtime.select_mode("typed")
    try:
        await session.start(agent=agent)
        handle = await runtime.input_text("read my cart", "sdk-turn", runtime.snapshot.revision)
        await asyncio.wait_for(handle.wait_for_playout(), timeout=10)
        assert handle.exception() is None
        assert len(adapter.requests) == 1
        assert adapter.requests[0].payload.operation == "get_cart"
        assert len(provider.contexts) == 2
        assert all(
            "UNTRUSTED_APPLICATION_DATA" in json.dumps(ctx.to_dict()) for ctx in provider.contexts
        )
        assert len(agent.tools) == 13
        assert any(
            isinstance(item, llm.ChatMessage)
            and item.role == "assistant"
            and "cart is empty" in (item.text_content or "")
            for item in handle.chat_items
        )
    finally:
        await runtime.close()
        await session.aclose()


@pytest.mark.asyncio
async def test_ambiguous_references_and_invalid_quantities_do_not_reach_authority(runtime):
    item = runtime.snapshot.visible_items[0].item_id
    result = await call(runtime, "cart_add_item", text="add the second one", item_id=item)
    assert result["status"] != "success" and not runtime.adapter.requests
    result = await call(runtime, "cart_add_item", item_id=item, quantity=0)
    assert result["status"] == "invalid_arguments" and not runtime.adapter.requests
    listed = await call(runtime, "search_menu", query="burger")
    runtime.on_delivered(listed["say"], runtime.snapshot.revision)
    expected = runtime.references.items[1].item_id
    result = await call(runtime, "cart_add_item", text="add the second one", item_id=item)
    assert result["status"] == "success"
    assert runtime.adapter.requests[-1].payload.arguments["item_id"] == expected


@pytest.mark.asyncio
async def test_no_audio_sink_cannot_mark_voice_summary_delivered(runtime):
    await call(runtime, "cart_add_item", item_id=runtime.snapshot.visible_items[0].item_id)
    runtime.session.output.audio = None
    await call(runtime, "checkout_get_summary", text="check out")
    assert not runtime.confirmation.summary_spoken
    assert (await call(runtime, "checkout_submit_demo_order", text="yes"))["status"] != "success"


@pytest.mark.asyncio
async def test_output_guard_needs_current_operation_witness_and_preserves_tool_chunks(runtime):
    from foodease_agent.integrated.output import checked_sentence, guarded_output

    context = await turn(runtime, "add one")
    active = runtime.active_turn
    assert "haven’t verified" in checked_sentence(runtime, active, "I added that to your cart.")
    await runtime.agent.cart_add_item(context, runtime.snapshot.visible_items[0].item_id)
    assert "haven’t verified" not in checked_sentence(runtime, active, "I added that to your cart.")
    assert "haven’t verified" in checked_sentence(runtime, active, "Your order has been placed.")
    tool_chunk = llm.ChatChunk(
        id="chunk",
        delta=llm.ChoiceDelta(
            tool_calls=[llm.FunctionToolCall(name="get_cart", arguments="{}", call_id="call")]
        ),
    )

    async def stream():
        yield tool_chunk
        yield "Take your time. "
        yield "Your order has been "
        yield "placed."

    output = [chunk async for chunk in guarded_output(stream(), runtime, active)]
    assert output[0] is tool_chunk
    spoken = " ".join(chunk for chunk in output if isinstance(chunk, str))
    assert "Take your time" in spoken and "haven’t verified" in spoken
    runtime.discard_turn(active.id)
    assert not checked_sentence(runtime, active, "I added it.")


@pytest.mark.asyncio
async def test_output_and_turn_replays_cannot_reopen_old_work(runtime):
    handle = await runtime.input_text("show the menu", "same-turn", runtime.snapshot.revision)
    generated = len(runtime.session.generated)
    assert await runtime.input_text("add one", "same-turn", runtime.snapshot.revision) is None
    assert len(runtime.session.generated) == generated
    runtime.session.emit("user_state_changed", new_state="speaking")
    runtime.session.emit("agent_state_changed", new_state="listening")
    from foodease_agent.idle import FakeClock

    runtime.idle.clock = FakeClock(1000)
    assert await runtime.poll_idle() is None
    assert (
        await runtime.agent.navigate(
            SimpleNamespace(session=runtime.session, speech_handle=handle), "cart"
        )
    )["status"] != "success"


@pytest.mark.asyncio
async def test_shutdown_retains_accepted_action_until_result_arrives(runtime):
    context = await turn(runtime, "add one")
    runtime.adapter.release.clear()
    action = asyncio.create_task(
        runtime.agent.cart_add_item(context, runtime.snapshot.visible_items[0].item_id)
    )
    await runtime.adapter.started.wait()
    closing = asyncio.create_task(runtime.close())
    await asyncio.sleep(0)
    assert runtime.closed and len(runtime.pending) == 1 and not runtime.session.input.enabled
    runtime.adapter.release.set()
    await closing
    await action
    assert len((await runtime.adapter.get_snapshot()).cart.lines) == 1
    assert not runtime.pending and len(runtime.broker.results) == 1


@pytest.mark.asyncio
async def test_typed_confirmed_exact_rendered_summary_submits_once(runtime):
    await runtime.select_mode("typed")
    runtime.adapter.text_delivery = True
    context = await turn(runtime, "add one", source="text")
    await runtime.agent.cart_add_item(context, runtime.snapshot.visible_items[0].item_id)
    context = await turn(runtime, "check out", source="text")
    await runtime.agent.checkout_get_summary(context)
    assert runtime.confirmation.summary_spoken
    context = await turn(runtime, "yes", source="text")
    assert (await runtime.agent.checkout_submit_demo_order(context))["status"] == "success"
    assert (await runtime.agent.checkout_submit_demo_order(context))["status"] != "success"
    assert (
        sum(r.payload.operation == "checkout.submit_demo_order" for r in runtime.adapter.requests)
        == 1
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("revoke", ["discard", "speech_interrupt"])
async def test_revocation_between_admission_and_first_transport_await_sends_nothing(
    runtime, revoke
):
    context = await turn(runtime, "add one")
    original = runtime.adapter.get_snapshot

    async def fresh():
        snapshot = await original()
        callback = (
            (lambda: runtime.discard_turn(runtime.active_turn.id))
            if revoke == "discard"
            else context.speech_handle.interrupt
        )
        asyncio.get_running_loop().call_soon(callback)
        return snapshot

    runtime.adapter.get_snapshot = fresh
    result = await runtime.agent.cart_add_item(context, runtime.snapshot.visible_items[0].item_id)
    assert result["status"] == "inactive_turn"
    assert not runtime.adapter.requests and not runtime.pending and not runtime.reconciler.pending
