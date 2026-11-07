"""Phase 6 deterministic onboarding; no providers or microphone recordings."""

import asyncio

import pytest

from foodease_agent.integrated.agent import IntegratedFoodEaseAgent
from foodease_agent.integrated.runtime import LiveConversationRuntime
from test_integrated_runtime import Session, Speech, WebsiteAdapter, control


@pytest.fixture
async def opening():
    adapter, session = WebsiteAdapter(), Session()
    runtime = LiveConversationRuntime(IntegratedFoodEaseAgent(), session, adapter)
    await runtime.prepare()
    await runtime.open_mode_choice()
    yield runtime
    await runtime.close()


@pytest.mark.parametrize(
    "text",
    [
        "manual please",
        "I'll order myself",
        "browse myself",
        "I want to order manually.",
        "I'd like to order manually",
        "I'll order manually",
        "I want to order by myself",
        "Please switch to manual ordering",
    ],
)
async def test_manual_choice_closes_without_shopping(opening, text):
    await control(opening, "manual", text)
    assert opening.closed
    assert not opening.session.input.enabled
    assert not opening.adapter.requests
    assert opening.adapter.controls == [("switch_mode", "manual")]


@pytest.mark.parametrize(
    "text",
    [
        "use voice",
        "talk me through it",
        "voice please",
        "I'd like to order using voice.",
        "I want to order by voice",
        "Use the voice assistant",
        "I'd like to use the voice assistant",
        "Please switch to voice ordering",
    ],
)
async def test_voice_choice_enables_once(opening, text):
    await control(opening, "voice", text)
    assert opening.mode == "voice"
    assert len(opening.session.spoken) == 2
    assert len(opening.session.generated) == 1
    assert not opening.adapter.requests


async def test_ambiguous_order_and_silence_have_one_clarification(opening):
    for i, text in enumerate(
        [
            "add a wrap",
            "yes",
            "voice or manual",
            "not manual",
            "don't use voice",
            "I want manual or voice",
            "I don't want to order manually",
        ]
    ):
        await opening.input_text(text, str(i), opening.snapshot.revision, source="audio")
    await opening.choice_timeout()
    await opening.choice_timeout()
    assert opening.mode == "choosing"
    assert len(opening.session.spoken) == 2
    assert len(opening.session.generated) == 7
    assert all(call["tools"] == ["conversation_control"] for call in opening.session.generated)
    assert not opening.adapter.requests
    assert await opening.poll_idle() is None


async def test_duplicate_open_and_direct_resume_have_no_double_greeting(opening):
    await opening.open_mode_choice()
    assert len(opening.session.spoken) == 1
    await opening.activate_mode("typed", resuming=True)
    await opening.activate_mode("typed", resuming=True)
    assert len(opening.session.spoken) == 2
    assert "Welcome back" in opening.session.spoken[-1]
    assert not opening.session.input.enabled
    assert not opening.session.output.enabled


async def test_typed_audio_is_explicit_and_never_enables_microphone(opening):
    await opening.activate_mode("typed")
    assert not opening.session.output.enabled
    await opening.handle_control("unmute")
    assert opening.session.output.enabled
    assert not opening.session.input.enabled
    await opening.handle_control("mute")
    assert not opening.session.output.enabled
    opening.say("Text still works.")
    assert opening.session.spoken[-1] == "Text still works."


async def test_manual_interrupts_unfinished_opening_and_prevents_late_welcome(monkeypatch):
    session, adapter = Session(), WebsiteAdapter()
    speech = Speech("opening still playing")
    session.handles.append(speech)
    monkeypatch.setattr(session, "say", lambda *args, **kwargs: speech)
    runtime = LiveConversationRuntime(IntegratedFoodEaseAgent(), session, adapter)
    await runtime.prepare()
    await runtime.open_mode_choice()
    await control(runtime, "manual", "manual please")
    await runtime.activate_mode("voice")
    await asyncio.sleep(0)
    assert speech.interrupted and runtime.closed
    assert not session.output.enabled and not adapter.requests
    await runtime.close()


async def test_idle_scheduler_clarifies_silence_once_without_shopping(opening):
    opening._choice_deadline = asyncio.get_running_loop().time() - 1
    opening._idle_task = asyncio.create_task(opening._idle_loop())
    await asyncio.sleep(0.3)
    assert len(opening.session.spoken) == 2
    await asyncio.sleep(0.3)
    assert len(opening.session.spoken) == 2
    assert not opening.adapter.requests and not opening.session.generated
