"""Urdu interruption filters brief activity without waiting for Whisper words."""

import asyncio
from types import SimpleNamespace
from typing import Any, cast

import numpy as np
import pytest
from livekit import rtc
from livekit.agents import vad
from livekit.agents.voice.agent_activity import AgentActivity

from foodease_agent import session as factory
from foodease_agent.integrated.agent import IntegratedFoodEaseAgent
from foodease_agent.integrated.runtime import LiveConversationRuntime
from test_integrated_runtime import Session, Speech, WebsiteAdapter, turn
from test_phase5_voice import _settings


def test_urdu_uses_short_speech_gate_even_with_older_cloud_thresholds(monkeypatch):
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
    assert options["min_duration"] == 0.35 and options["min_words"] == 0
    assert options["resume_false_interruption"] is False


def test_english_preserves_existing_interruption_policy(monkeypatch):
    marker = object()
    for name in ("build_stt", "build_tts", "build_llm"):
        monkeypatch.setattr(factory, name, lambda *args: marker)
    bundle = factory.build_session_kwargs(_settings(assistant_language="en"), prewarmed_vad=marker)
    options = bundle.session_kwargs["turn_handling"]["interruption"]
    assert options["mode"] == "adaptive"
    assert options["min_duration"] == 0.5 and options["min_words"] == 0


async def test_brief_speech_detection_does_not_force_interrupt_greeting():
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
        assert session.interrupts == before
        session.emit("user_state_changed", new_state="listening")
        assert session.interrupts == before
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
        assert not context.speech_handle.interrupted
        # The SDK confirms sustained speech; raw user-state onset is insufficient.
        context.speech_handle.interrupt()
        await asyncio.sleep(0)
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


@pytest.mark.parametrize("windows", [(0,), (2,), (5,), (8,), (5, 5, 5), (12,), (20,)])
@pytest.mark.parametrize("greeting", [False, True])
async def test_real_vad_segmentation_and_sdk_gate_filter_brief_activity(windows, greeting):
    """Real Silero stream/SDK gate; model probabilities are scripted, NOT real audio accuracy."""
    detector = factory.build_vad("ur")
    stream = detector.stream()

    class Probabilities:
        window_size_samples = 512
        sample_rate = 16000

        def __call__(self, data):
            return 0.99 if np.max(data) > 0 else 0.01

        def reset(self):
            pass

    # Pin only acoustic inference. Exercise the installed stream's smoothing,
    # speech/silence segmentation and published-duration handling unchanged.
    stream._model = Probabilities()
    session = Session()
    adapter = WebsiteAdapter()
    runtime = LiveConversationRuntime(IntegratedFoodEaseAgent(language="ur"), session, adapter)
    await runtime.prepare()
    await runtime.select_mode("voice")
    if greeting:
        def queued_say(text, **kw):
            handle = Speech(text)
            session.handles.append(handle)
            session.emit("speech_created", speech_handle=handle, source="say")
            return handle

        session.say = queued_say
        context = SimpleNamespace(speech_handle=runtime.say("السلام علیکم، میں زارا ہوں۔"))
    else:
        context = await turn(runtime, "برگر دکھاؤ")
    activity = SimpleNamespace(
        _turn_detection="vad",
        _session=SimpleNamespace(options=SimpleNamespace(interruption={"min_duration": 0.35})),
        _stt_eos_received=False,
        min_endpointing_delay=0.45,
        _user_silence_event=asyncio.Event(),
        _interrupt_by_audio_activity=session.interrupt,
    )
    onsets = 0
    try:
        for length in windows:
            for value, count in [(0, 20), (1000, length), (0, 24)]:
                for _ in range(count):
                    stream.push_frame(rtc.AudioFrame(
                        data=np.full(512, value, dtype=np.int16).tobytes(),
                        sample_rate=16000, num_channels=1, samples_per_channel=512,
                    ))
        stream.end_input()
        async for event in stream:
            if event.type == vad.VADEventType.START_OF_SPEECH:
                onsets += 1
                session.emit("user_state_changed", new_state="speaking")
            elif event.type == vad.VADEventType.END_OF_SPEECH:
                session.emit("user_state_changed", new_state="listening")
            elif event.type == vad.VADEventType.INFERENCE_DONE:
                AgentActivity.on_vad_inference_done(cast(Any, activity), event)
        await asyncio.sleep(0)
        expected = max(windows) >= 12
        assert bool(onsets) == expected
        assert context.speech_handle.interrupted == expected
        if runtime.active_turn is not None:
            assert runtime.active_turn.committed != expected
        assert not adapter.requests
    finally:
        await stream.aclose()
        await runtime.close()


def test_prewarm_and_fallback_share_urdu_speech_gate(monkeypatch):
    from foodease_agent import worker

    calls = []
    marker = object()
    monkeypatch.setattr(factory.silero.VAD, "load", lambda **kw: calls.append(kw) or marker)
    monkeypatch.setenv("ASSISTANT_LANGUAGE", "ur")
    proc = SimpleNamespace(userdata={})
    worker.prewarm(cast(Any, proc))
    assert proc.userdata["vad"] is marker
    assert factory.build_vad("ur") is marker
    assert calls == [{"min_speech_duration": 0.35}] * 2
    factory.build_vad("en")
    assert calls[-1] == {}


async def test_confirmed_interruption_of_independent_reply_revokes_turn_before_done_callback():
    runtime = LiveConversationRuntime(
        IntegratedFoodEaseAgent(language="ur"), Session(), WebsiteAdapter()
    )
    await runtime.prepare()
    await runtime.select_mode("voice")
    try:
        await turn(runtime, "کارٹ دکھاؤ")
        active = runtime.active_turn
        assert active is not None

        def queued_say(text, **kw):
            handle = Speech(text)
            runtime.session.handles.append(handle)
            runtime.session.emit("speech_created", speech_handle=handle, source="say")
            return handle

        runtime.session.say = queued_say
        reply = runtime.say("آپ کا کارٹ خالی ہے۔")
        reply.interrupt()
        # Authorization must fail synchronously, before the async done callback.
        assert not runtime.authorized(active)
        await turn(runtime, "برگر دکھاؤ")
        replacement = runtime.active_turn
        assert replacement is not None
        await asyncio.sleep(0)
        assert replacement.committed  # the late old callback cannot revoke it
    finally:
        await runtime.close()
