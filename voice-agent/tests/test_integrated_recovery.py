"""Phase 8 faults enter production runtime hooks; authority is the real website."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from livekit.agents import llm, stt, tts
from livekit.agents._exceptions import APIStatusError
from livekit.agents.voice.events import ErrorEvent

from test_integrated_runtime import call, turn

pytest_plugins = ("test_integrated_runtime",)


@pytest.mark.asyncio
@pytest.mark.parametrize("error_type", [stt.STTError, tts.TTSError])
async def test_exhausted_speech_provider_degrades_to_silent_typing(runtime, error_type):
    await call(runtime, "cart_add_item", item_id="wrap-hot-chicken")
    error = error_type(
        timestamp=1, label="offline-provider", error=TimeoutError(), recoverable=False
    )
    runtime.session.handlers["error"](ErrorEvent(error=error, source=object()))
    await asyncio.sleep(0)
    assert runtime.mode == "typed" and not runtime.closed
    assert not runtime.session.input.enabled and not runtime.session.output.enabled
    assert error.recoverable  # SDK must not close the surviving text pipeline.
    assert ("switch_mode", "typed") in runtime.adapter.controls
    context = await turn(runtime, "read cart", source="text")
    result = await runtime.agent.get_cart(context)
    assert result["facts"]["lines"][0]["quantity"] == 1
    await runtime.select_mode("voice")
    assert runtime.mode == "typed"  # Explicit new generation required for broken speech.


@pytest.mark.asyncio
async def test_llm_outage_ends_assistance_and_keeps_manual_cart(runtime):
    await call(runtime, "cart_add_item", item_id="wrap-hot-chicken")
    error = llm.LLMError(timestamp=1, label="offline", error=TimeoutError(), recoverable=False)
    runtime.session.handlers["error"](ErrorEvent(error=error, source=object()))
    await asyncio.sleep(0)
    assert runtime.closed
    assert ("switch_mode", "manual") in runtime.adapter.controls
    assert (await runtime.adapter.get_snapshot()).cart.lines[0].quantity == 1


@pytest.mark.asyncio
async def test_transient_provider_error_has_no_mode_change(runtime):
    error = tts.TTSError(timestamp=1, label="offline", error=TimeoutError(), recoverable=True)
    runtime.session.handlers["error"](ErrorEvent(error=error, source=object()))
    assert runtime.mode == "voice" and not runtime.closed


@pytest.mark.asyncio
@pytest.mark.parametrize("language", ["en", "ur"])
async def test_llm_rate_limit_stops_only_the_reply_without_replaying_cart_actions(
    runtime, language,
):
    runtime.language = language
    await call(runtime, "cart_add_item", item_id="wrap-hot-chicken")
    failed_turn = runtime.active_turn
    error = llm.LLMError(
        timestamp=1, label="offline", error=APIStatusError("rate limit", status_code=429),
        recoverable=False,
    )
    runtime.session.handlers["error"](ErrorEvent(error=error, source=object()))
    await asyncio.sleep(0)
    assert error.recoverable and runtime.mode == "voice" and not runtime.closed
    assert failed_turn.discarded and not runtime.authorized(failed_turn)
    assert ("switch_mode", "manual") not in runtime.adapter.controls
    expected = "check your cart" if language == "en" else "اپنی ٹوکری دیکھ لیں"
    assert expected in runtime.session.spoken[-1].lower()
    assert len(runtime.adapter.requests) == 1
    assert (await runtime.adapter.get_snapshot()).cart.lines[0].quantity == 1


@pytest.mark.asyncio
async def test_resume_refreshes_even_same_revision_and_never_reuses_summary(runtime):
    await call(runtime, "cart_add_item", item_id="wrap-hot-chicken")
    await call(runtime, "checkout_get_summary", text="checkout")
    assert runtime.confirmation.summary_spoken
    await runtime.handle_control("pause")
    revision = runtime.snapshot.revision
    await runtime.handle_control("resume")
    assert runtime.snapshot.revision == revision
    assert not runtime.confirmation.summary_spoken and not runtime.references.items
    result = await call(runtime, "checkout_submit_demo_order", text="yes")
    assert result["status"] == "confirmation_required"


@pytest.mark.asyncio
async def test_failed_resume_stays_paused_and_silent(runtime):
    await runtime.handle_control("pause")

    async def offline():
        raise TimeoutError()

    runtime.adapter.get_snapshot = offline
    before = len(runtime.session.spoken)
    await runtime.handle_control("resume")
    assert runtime.paused and len(runtime.session.spoken) == before


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["not_seen", "pending", "expired"])
async def test_unknown_lookup_states_remain_owned_and_are_distinguished(runtime, state):
    async def lost(_request):
        raise TimeoutError()

    async def lookup(_action):
        return SimpleNamespace(state=state, result=None)

    runtime.adapter.submit, runtime.adapter.lookup = lost, lookup
    result = await call(runtime, "cart_add_item", item_id="wrap-hot-chicken")
    assert result["status"] == "timeout_unknown"
    assert result["recovery"]["state"] == state
    assert result["recovery"]["replay_allowed"] is False
    assert len(runtime.pending) == 1
    assert (await runtime.adapter.get_snapshot()).cart.lines == []


@pytest.mark.asyncio
async def test_end_during_write_drains_commit_without_late_speech(runtime):
    context = await turn(runtime)
    runtime.adapter.release.clear()
    task = asyncio.create_task(runtime.agent.cart_add_item(context, item_id="wrap-hot-chicken"))
    await runtime.adapter.started.wait()
    runtime.end_local()
    before = len(runtime.session.spoken)
    runtime.adapter.release.set()
    assert (await task)["status"] == "inactive_turn"
    assert (await runtime.adapter.get_snapshot()).cart.lines[0].quantity == 1
    assert len(runtime.adapter.requests) == 1 and len(runtime.session.spoken) == before


@pytest.mark.asyncio
async def test_false_interruption_never_recommits_old_business_turn(runtime):
    await turn(runtime)
    runtime.on_user_state(SimpleNamespace(new_state="speaking"))
    runtime.session.handlers["agent_false_interruption"](SimpleNamespace(resumed=True))
    assert not runtime.active_turn.committed
    assert runtime.recovery.observations[-1]["kind"] == "false_interruption"
    assert runtime.recovery.observations[-1]["resumed"] is True
    assert runtime.adapter.requests == []


@pytest.mark.asyncio
async def test_lost_checkout_response_is_recovered_once_after_real_commit(runtime):
    await call(runtime, "cart_add_item", item_id="wrap-hot-chicken")
    await call(runtime, "checkout_get_summary", text="checkout")
    runtime.adapter.lose_reply = True
    result = await call(runtime, "checkout_submit_demo_order", text="yes")
    assert result["status"] == "success" and result["facts"]["demo_order_id"].startswith("DEMO-")
    orders = [
        r for r in runtime.adapter.requests if r.payload.operation == "checkout.submit_demo_order"
    ]
    assert len(orders) == 1
    receipt = runtime.broker.results[orders[0].payload.action_id]
    lookup = await runtime.adapter.lookup(orders[0].payload.action_id)
    assert lookup.result == receipt and not runtime.snapshot.cart.lines


@pytest.mark.asyncio
async def test_worker_room_reconnect_refreshes_and_end_during_refresh_cannot_revive(runtime):
    runtime.recovery.room_reconnecting()
    assert runtime.paused and not runtime.session.input.enabled
    release = asyncio.Event()
    snapshot = runtime.snapshot

    async def delayed():
        await release.wait()
        return snapshot

    runtime.adapter.get_snapshot = delayed
    runtime.recovery.room_reconnected()
    await asyncio.sleep(0)
    runtime.end_local()
    release.set()
    await asyncio.sleep(0)
    assert runtime.closed and runtime.paused and not runtime.session.output.enabled


@pytest.mark.asyncio
async def test_actual_sdk_llm_stream_failure_reaches_runtime_without_fault_flags():
    from livekit.agents import AgentSession, APIConnectionError
    from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS, APIConnectOptions

    from foodease_agent.integrated.agent import IntegratedFoodEaseAgent
    from foodease_agent.integrated.runtime import LiveConversationRuntime
    from test_integrated_runtime import WebsiteAdapter

    class UnavailableLLM(llm.LLM):
        def chat(self, *, chat_ctx, tools=None, conn_options=DEFAULT_API_CONNECT_OPTIONS, **kwargs):
            return FailedStream(
                self,
                chat_ctx=chat_ctx,
                tools=tools or [],
                conn_options=APIConnectOptions(max_retry=0),
            )

    class FailedStream(llm.LLMStream):
        async def _run(self):
            raise APIConnectionError("offline fixture provider unavailable")

    session, adapter = AgentSession(llm=UnavailableLLM()), WebsiteAdapter()
    runtime = LiveConversationRuntime(IntegratedFoodEaseAgent(), session, adapter)
    await runtime.prepare()
    await runtime.select_mode("typed")
    try:
        await session.start(agent=runtime.agent)
        handle = await runtime.input_text(
            "Describe my order so far", "outage", runtime.snapshot.revision
        )
        await asyncio.wait_for(handle.wait_for_playout(), 5)
        await asyncio.sleep(0)
        assert runtime.closed and ("switch_mode", "manual") in adapter.controls
        assert adapter.requests == []
        assert runtime.recovery.observations[-1]["component"] == "llm_error"
    finally:
        await runtime.close()
        await session.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("component", ["stt", "tts"])
async def test_provider_interface_failure_is_forwarded_by_actual_sdk_and_text_survives(component):
    from livekit.agents import AgentSession, APIConnectionError, TurnHandlingOptions
    from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS, APIConnectOptions

    from foodease_agent.integrated.agent import IntegratedFoodEaseAgent
    from foodease_agent.integrated.runtime import LiveConversationRuntime
    from test_integrated_runtime import WebsiteAdapter

    class LocalSTT(stt.STT):
        def __init__(self):
            super().__init__(
                capabilities=stt.STTCapabilities(streaming=True, interim_results=False)
            )

        async def _recognize_impl(self, buffer, *, language=None, conn_options):
            raise APIConnectionError("offline speech recognition failure")

        def stream(self, *, language=None, conn_options=DEFAULT_API_CONNECT_OPTIONS):
            return QuietStream(stt=self, conn_options=conn_options)

    class QuietStream(stt.RecognizeStream):
        async def _run(self):
            async for _ in self._input_ch:
                pass

    class LocalTTS(tts.TTS):
        def __init__(self):
            super().__init__(
                capabilities=tts.TTSCapabilities(streaming=False), sample_rate=24000, num_channels=1
            )

        def synthesize(self, text, *, conn_options=DEFAULT_API_CONNECT_OPTIONS):
            return FailedAudio(tts=self, input_text=text, conn_options=conn_options)

    class FailedAudio(tts.ChunkedStream):
        async def _run(self, output_emitter):
            raise APIConnectionError("offline speech synthesis failure")

    class LocalLLM(llm.LLM):
        def chat(self, *, chat_ctx, tools=None, conn_options=DEFAULT_API_CONNECT_OPTIONS, **kwargs):
            return TextStream(self, chat_ctx=chat_ctx, tools=tools or [], conn_options=conn_options)

    class TextStream(llm.LLMStream):
        async def _run(self):
            self._event_ch.send_nowait(
                llm.ChatChunk(
                    id="local", delta=llm.ChoiceDelta(content="What would you like to eat?")
                )
            )

    recognizer, speaker = LocalSTT(), LocalTTS()
    session = AgentSession(
        llm=LocalLLM(),
        stt=recognizer,
        tts=speaker,
        turn_handling=TurnHandlingOptions(turn_detection="manual"),
    )
    runtime = LiveConversationRuntime(IntegratedFoodEaseAgent(), session, WebsiteAdapter())
    await runtime.prepare()
    await runtime.select_mode("voice")
    try:
        await session.start(agent=runtime.agent)
        with pytest.raises(APIConnectionError):
            if component == "stt":
                await recognizer.recognize([], conn_options=APIConnectOptions(max_retry=0))
            else:
                async with speaker.synthesize(
                    "hello", conn_options=APIConnectOptions(max_retry=0)
                ) as stream:
                    async for _ in stream:
                        pass
        await asyncio.sleep(0)
        assert runtime.mode == "typed" and not runtime.closed
        handle = await runtime.input_text(
            "help me choose", "after-error", runtime.snapshot.revision
        )
        await asyncio.wait_for(handle.wait_for_playout(), 5)
        assert handle.exception() is None
        assert any(
            isinstance(i, llm.ChatMessage) and "eat" in (i.text_content or "")
            for i in handle.chat_items
        )
    finally:
        await runtime.close()
        await session.aclose()


@pytest.mark.asyncio
async def test_manual_edit_wins_over_a_delayed_committed_result(runtime):
    committed, released = asyncio.Event(), asyncio.Event()
    submit = runtime.adapter.submit

    async def delayed(request):
        result = await submit(request)
        committed.set()
        await released.wait()
        return result

    runtime.adapter.submit = delayed
    context = await turn(runtime)
    task = asyncio.create_task(
        runtime.agent.cart_add_item(context, item_id="wrap-hot-chicken", quantity=2)
    )
    await committed.wait()
    await runtime.adapter.manual(
        "cart.set_quantity", {"item_id": "wrap-hot-chicken", "quantity": 1}
    )
    runtime.on_context(await runtime.adapter.get_snapshot(), source_turn="manual")
    before = len(runtime.session.spoken)
    released.set()
    assert (await task)["status"] == "inactive_turn"
    assert runtime.snapshot.cart.lines[0].quantity == 1
    assert len(runtime.session.spoken) == before and not runtime.pending


@pytest.mark.asyncio
async def test_bound_app_seat_loss_revokes_worker_and_late_events_cannot_resume():
    from foodease_agent.adapters.integrated import IntegratedRpcAdapter
    from foodease_agent.adapters.integrated_startup import IntegratedRoomGate
    from foodease_agent.integrated.agent import IntegratedFoodEaseAgent
    from foodease_agent.integrated.runtime import LiveConversationRuntime
    from test_integrated_rpc_worker import Room
    from test_integrated_runtime import Session

    room = Room()
    gate = IntegratedRoomGate(room, room.startup)
    runtime = LiveConversationRuntime(
        IntegratedFoodEaseAgent(), Session(), IntegratedRpcAdapter(gate), gate=gate
    )
    await runtime.prepare()
    await runtime.select_mode("voice")
    try:
        room.handlers["participant_disconnected"](room.person("foreign"))
        assert not runtime.closed
        room.handlers["participant_disconnected"](room.person("app"))
        assert runtime.closed and gate.closed
        assert not runtime.session.input.enabled and not runtime.session.output.enabled
        runtime.recovery.room_reconnected()
        assert not await runtime.recovery.resume()
    finally:
        await runtime.close()
