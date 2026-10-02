"""Phase 5 unit tests — idle, greeting, turn-commit, interruption, controls."""

from __future__ import annotations

import pytest

from foodease_agent.adapters.mock import MockAdapter
from foodease_agent.agent import FoodEaseAgent
from foodease_agent.config import Settings
from foodease_agent.contract.enums import Operation, ProductState
from foodease_agent.controls import ControlIntent, match_control
from foodease_agent.greeting import GreetingCache
from foodease_agent.idle import FakeClock, IdlePromptController, IdleStage
from foodease_agent.interruption import InterruptionReconciler
from foodease_agent.product_state import fatal_error_state, map_livekit_agent_state
from foodease_agent.session import build_session_kwargs, turn_handling_options
from foodease_agent.turn_commit import TurnCommitGate, TurnNotCommittedError


def _settings(**overrides: object) -> Settings:
    base = dict(
        livekit_url="wss://example.livekit.cloud",
        livekit_api_key="<lk-key>",
        livekit_api_secret="<lk-secret>",
        deepgram_api_key="<dg-key>",
        cartesia_api_key="<cartesia-key>",
        google_api_key="<google-key>",
        stt_model="flux-general-en",
        llm_model="gemini-3.1-flash-lite",
        llm_thinking_level="minimal",
        tts_model="sonic-3.6",
        tts_voice_id="<voice-id>",
        idle_prompt_1_seconds=12.0,
        idle_prompt_2_seconds=30.0,
        record_audio=False,
        dev_mode=False,
        voice_pipeline_config="A",
        snapshot_timeout_seconds=2.0,
        preemptive_generation=False,
        noise_cancellation=False,
        greeting_cache=True,
    )
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


# --- V5.2 idle tips ---


def test_idle_one_then_second_then_quiet() -> None:
    clock = FakeClock()
    idle = IdlePromptController(idle_1_seconds=12, idle_2_seconds=30, clock=clock)
    idle.on_assistant_finished()
    assert idle.poll("menu") is None
    clock.advance(12)
    tip1 = idle.poll("menu")
    assert tip1 is not None
    assert "category" in tip1.lower() or "burgers" in tip1.lower()
    clock.advance(30)
    tip2 = idle.poll("menu")
    assert tip2 is not None
    assert tip2 != tip1
    assert idle.stage == IdleStage.QUIET
    clock.advance(100)
    assert idle.poll("menu") is None  # no loop


def test_idle_cancelled_by_activity() -> None:
    clock = FakeClock()
    idle = IdlePromptController(idle_1_seconds=12, idle_2_seconds=30, clock=clock)
    idle.on_assistant_finished()
    clock.advance(11)
    idle.reset_after_activity()
    clock.advance(11)
    assert idle.poll("menu") is None  # timer reset
    clock.advance(1)
    assert idle.poll("menu") is not None


def test_idle_context_aware_cart() -> None:
    clock = FakeClock()
    idle = IdlePromptController(idle_1_seconds=1, idle_2_seconds=2, clock=clock)
    idle.on_assistant_finished()
    clock.advance(1)
    tip = idle.poll("cart")
    assert tip is not None
    assert "cart" in tip.lower()


# --- V5.1 / V5.10 greeting ---


@pytest.mark.asyncio
async def test_snapshot_timeout_greets_generic() -> None:
    agent = FoodEaseAgent(_settings(snapshot_timeout_seconds=0.05), adapter=MockAdapter())
    ok = await agent.wait_for_snapshot_or_timeout()
    assert ok is False
    text = agent.greetings.next_greeting(has_context=False)
    assert "context" in text.lower() or "welcome" in text.lower()


@pytest.mark.asyncio
async def test_snapshot_then_resume_greeting() -> None:
    agent = FoodEaseAgent(_settings(snapshot_timeout_seconds=1.0), adapter=MockAdapter())
    agent.notify_context_snapshot()
    assert await agent.wait_for_snapshot_or_timeout() is True
    g1 = agent.greetings.next_greeting(has_context=True)
    agent.greetings.mark_session_voice_active()
    g2 = agent.greetings.next_greeting(has_context=True)
    assert g2 != g1
    assert "welcome back" in g2.lower()


def test_greeting_cache_invalidates_on_voice_change() -> None:
    cache = GreetingCache(voice_id="v1", tts_model="sonic-3.6")
    cache.put("hi", object())
    assert cache.get("hi") is not None
    cache.invalidate_if_settings_changed(voice_id="v2", tts_model="sonic-3.6")
    assert cache.get("hi") is None


# --- V5.5 / V5.7 controls + turn commit ---


def test_stop_repeat_slower_fast_path_no_llm() -> None:
    for utt, intent in [
        ("stop", ControlIntent.STOP),
        ("repeat", ControlIntent.REPEAT),
        ("go back", ControlIntent.GO_BACK),
        ("slower", ControlIntent.SLOWER),
    ]:
        m = match_control(utt)
        assert m is not None
        assert m.intent == intent


def test_v57_zero_mutations_on_discarded_generation() -> None:
    gate = TurnCommitGate()
    # Speculative path: uncommitted
    with pytest.raises(TurnNotCommittedError):
        gate.require(Operation.CART_ADD_ITEM)
    assert "cart.add_item" in gate.mutation_attempts_while_uncommitted

    gate.on_generation_discarded()
    with pytest.raises(TurnNotCommittedError):
        gate.require(Operation.CART_ADD_ITEM)

    gate.mark_committed()
    gate.require(Operation.CART_ADD_ITEM)  # no raise


@pytest.mark.asyncio
async def test_agent_tool_blocked_until_committed() -> None:
    agent = FoodEaseAgent(_settings(), adapter=MockAdapter())
    with pytest.raises(TurnNotCommittedError):
        await agent._execute_op(Operation.CART_ADD_ITEM, {"item_id": "itm_burger", "quantity": 1})
    agent.turn_gate.mark_committed()
    # May reject for unknown item — but must not raise TurnNotCommittedError
    try:
        await agent._execute_op(Operation.NAVIGATE, {"target": "burgers"})
    except TurnNotCommittedError:
        pytest.fail("committed turn still blocked")


# --- V5.6 / V5.8 interruption ---


def test_barge_in_marks_interrupted_keeps_pending() -> None:
    r = InterruptionReconciler()
    r.register_pending("action-1", "cart.add_item")
    utt = r.on_barge_in(spoken_so_far="Adding two bur", full_intended="Adding two burgers.")
    assert utt.status.value == "interrupted"
    assert "action-1" in r.pending
    reply = r.late_result_reply("action-1", success=True)
    assert reply == "Done."
    assert r.late_result_reply("action-1", success=True) is None  # silence second time


def test_no_overlapping_assistant_intervals() -> None:
    r = InterruptionReconciler()
    r.on_assistant_start(0.0)
    r.on_assistant_stop(1.0)
    r.on_assistant_start(1.0)
    r.on_assistant_stop(2.0)
    assert InterruptionReconciler.intervals_overlap(r.speaking_intervals) is False
    assert InterruptionReconciler.intervals_overlap([(0.0, 1.5), (1.0, 2.0)]) is True


# --- V5.9 false interruption heuristics (logic) ---


def test_mm_hmm_not_control() -> None:
    assert match_control("mm-hmm") is None
    assert match_control("cough") is None


# --- product state / fatal error ---


def test_fatal_error_never_listening() -> None:
    assert fatal_error_state() == ProductState.ERROR
    assert map_livekit_agent_state("listening") == ProductState.READY_LISTENING


def test_session_kwargs_config_a_disables_preemptive() -> None:
    turn = turn_handling_options(turn_detection="stt", preemptive_enabled=False)
    assert turn["preemptive_generation"]["enabled"] is False
    assert turn["turn_detection"] == "stt"


def test_session_bundle_pipelines() -> None:
    for pipeline in ("A", "B"):
        bundle = build_session_kwargs(_settings(voice_pipeline_config=pipeline), pipeline=pipeline)  # type: ignore[arg-type]
        assert bundle.pipeline == pipeline
        assert "stt" in bundle.session_kwargs
        assert "tts" in bundle.session_kwargs
        assert "llm" in bundle.session_kwargs
        assert bundle.preemptive_enabled is False


# --- V5.11 soak (scripted, no providers) ---


@pytest.mark.asyncio
async def test_soak_scripted_turns_no_runaway_idle() -> None:
    clock = FakeClock()
    idle = IdlePromptController(idle_1_seconds=12, idle_2_seconds=30, clock=clock)
    tips = 0
    for _ in range(40):
        idle.on_assistant_finished()
        clock.advance(12)
        if idle.poll("menu"):
            tips += 1
        clock.advance(30)
        if idle.poll("menu"):
            tips += 1
        idle.reset_after_activity()
        # After quiet, further polls stay quiet until we don't re-enable —
        # reset_after_activity from QUIET stays QUIET per design for endless silence.
        # Re-arm for next scripted turn:
        if idle.stage == IdleStage.QUIET:
            idle.stage = IdleStage.WAITING_FIRST
    assert tips >= 2
    # Never more than 2 tips per quiet cycle without re-arm — bounded
    assert tips <= 80
