"""Urdu interruption is driven by speech onset, not delayed Whisper words."""

import asyncio

from foodease_agent import session as factory
from foodease_agent.integrated.agent import IntegratedFoodEaseAgent
from foodease_agent.integrated.runtime import LiveConversationRuntime
from test_integrated_runtime import Session, WebsiteAdapter, turn
from test_phase5_voice import _settings


def test_urdu_uses_vad_onset_even_with_older_cloud_thresholds(monkeypatch):
    marker = object()
    for name in ("build_stt", "build_tts", "build_llm"):
        monkeypatch.setattr(factory, name, lambda *args: marker)
    bundle = factory.build_session_kwargs(
        _settings(assistant_language="ur", interruption_min_duration=1.2, interruption_min_words=1),
        prewarmed_vad=marker,
    )
    options = bundle.session_kwargs["turn_handling"]["interruption"]
    assert options["enabled"] is True
    assert options["mode"] == "vad"
    assert options["min_duration"] == 0 and options["min_words"] == 0
    assert options["resume_false_interruption"] is False


def test_english_preserves_existing_interruption_policy(monkeypatch):
    marker = object()
    for name in ("build_stt", "build_tts", "build_llm"):
        monkeypatch.setattr(factory, name, lambda *args: marker)
    bundle = factory.build_session_kwargs(_settings(assistant_language="en"), prewarmed_vad=marker)
    options = bundle.session_kwargs["turn_handling"]["interruption"]
    assert options["mode"] == "adaptive"
    assert options["min_duration"] == 0.5 and options["min_words"] == 0


async def test_speech_onset_interrupts_greeting_without_a_committed_shopping_turn():
    class CountingSession(Session):
        interrupts = 0

        def interrupt(self, **kwargs):
            self.interrupts += 1
            return super().interrupt(**kwargs)

    session = CountingSession()
    adapter = WebsiteAdapter()
    runtime = LiveConversationRuntime(
        IntegratedFoodEaseAgent(language="ur"), session, adapter
    )
    await runtime.prepare()
    await runtime.select_mode("voice")
    try:
        before = session.interrupts
        assert runtime.active_turn is None
        session.emit("user_state_changed", new_state="speaking")
        assert session.interrupts == before + 1
        assert not adapter.requests
    finally:
        await runtime.close()


async def test_barge_in_stops_turn_but_retains_one_already_submitted_cart_action():
    adapter = WebsiteAdapter()
    runtime = LiveConversationRuntime(IntegratedFoodEaseAgent(language="ur"), Session(), adapter)
    await runtime.prepare()
    await runtime.select_mode("voice")
    try:
        context = await turn(runtime, "ایک کولا شامل کرو")
        adapter.release.clear()
        task = asyncio.create_task(runtime.agent.cart_add_item(context, "drink-cola", 1))
        await adapter.started.wait()
        runtime.session.emit("user_state_changed", new_state="speaking")
        assert context.speech_handle.interrupted
        assert runtime.active_turn is not None and not runtime.active_turn.committed
        assert runtime.pending
        adapter.release.set()
        assert (await task)["status"] != "success"  # old turn cannot speak a late success
        assert len(adapter.requests) == 1
        assert (await adapter.get_snapshot()).cart.lines[0].quantity == 1
        assert not runtime.pending and not runtime.session.spoken
    finally:
        adapter.release.set()
        await runtime.close()
