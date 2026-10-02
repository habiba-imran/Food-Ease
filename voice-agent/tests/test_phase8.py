"""Phase 8 — VA-17 recovery, reconnect, confidence, chaos, fallbacks."""

from __future__ import annotations

import random

import pytest

from foodease_agent.adapters.mock import MockAdapter, ScenarioConfig, ScenarioMode
from foodease_agent.confidence import ConfidenceGate
from foodease_agent.confirmation import ConfirmState
from foodease_agent.contract.enums import ActionResultStatus, Operation, ProductState
from foodease_agent.contract.models import ActionRequestPayload
from foodease_agent.dialogue_planner import DialogueSuitePlanner
from foodease_agent.engine import ConversationEngine, ToolCall
from foodease_agent.fallback import FallbackChain
from foodease_agent.faults import FAULTS
from foodease_agent.planner import ScriptedPlanner
from foodease_agent.product_state import ProductStateMachine
from foodease_agent.reconnect import ReconnectManager, guard_resubmit
from foodease_agent.recovery import ALL_VA17, Va17Situation, apply_recovery, recover


@pytest.fixture(autouse=True)
def _reset_faults():
    FAULTS.reset()
    yield
    FAULTS.reset()


# --- V8.2: every VA-17 row ---


@pytest.mark.parametrize("situation", list(ALL_VA17))
def test_v82_each_va17_row_has_recovery(situation: Va17Situation) -> None:
    r = recover(situation)
    assert r.situation == situation
    assert r.may_retry_mutation is False
    sm = ProductStateMachine()
    apply_recovery(sm, situation)
    # STT down must not leave listening
    if situation == Va17Situation.STT_DOWN:
        assert sm.state == ProductState.ERROR
        assert "listening" not in sm.state.value or sm.state == ProductState.ERROR


# --- V8.1 acceptance behaviors ---


@pytest.mark.asyncio
async def test_t08_failed_add_no_false_success() -> None:
    app = MockAdapter()
    app.set_scenario(ScenarioConfig(mode=ScenarioMode.FAILED))
    engine = ConversationEngine(
        adapter=app,
        planner=ScriptedPlanner(
            {
                "add cola": [
                    ToolCall(Operation.CART_ADD_ITEM, {"item_id": "drink-cola", "quantity": 1})
                ]
            }
        ),
    )
    r = await engine.handle_text("add cola")
    assert "added" not in r.assistant_text.lower() or "not" in r.assistant_text.lower()
    assert "updated" not in r.assistant_text.lower()
    assert r.tool_results[0].status == ActionResultStatus.FAILED


@pytest.mark.asyncio
async def test_t11_silence_no_checkout_submit() -> None:
    app = MockAdapter()
    await app.submit_action(
        ActionRequestPayload(
            action_id="pre",
            operation=Operation.CART_ADD_ITEM,
            arguments={"item_id": "drink-cola", "quantity": 1},
        )
    )
    engine = ConversationEngine(adapter=app, planner=DialogueSuitePlanner())
    r = await engine.handle_text("checkout")
    assert "shall i" in r.assistant_text.lower() or "total" in r.assistant_text.lower()
    # silence
    r2 = await engine.handle_text("")
    assert engine.confirmation.state != ConfirmState.SUBMITTED
    assert not any(
        getattr(t, "operation", None) == Operation.CHECKOUT_SUBMIT_DEMO_ORDER for t in r2.tool_results
    )
    # silence must not flip to submitted via confirm path
    assert engine.confirmation.state.value != "submitted"


@pytest.mark.asyncio
async def test_mic_denied_and_tts_down() -> None:
    engine = ConversationEngine(adapter=MockAdapter(), planner=DialogueSuitePlanner())
    FAULTS.mic_denied = True
    r = await engine.handle_text("show burgers")
    assert r.state == ProductState.MUTED_PAUSED
    assert "type" in r.assistant_text.lower() or "browse" in r.assistant_text.lower()
    FAULTS.reset()
    FAULTS.fail_tts = True
    r2 = await engine.handle_text("where am i")
    assert "text" in r2.assistant_text.lower() or "speak" in r2.assistant_text.lower()
    assert r2.assistant_text  # text retained


@pytest.mark.asyncio
async def test_t12_one_demo_submit() -> None:
    app = MockAdapter()
    await app.submit_action(
        ActionRequestPayload(
            action_id="pre",
            operation=Operation.CART_ADD_ITEM,
            arguments={"item_id": "drink-cola", "quantity": 1},
        )
    )
    engine = ConversationEngine(adapter=app, planner=DialogueSuitePlanner())
    await engine.handle_text("checkout")
    r = await engine.handle_text("yes")
    assert "demo" in r.assistant_text.lower()
    submits = [t for t in r.tool_results if t.status == ActionResultStatus.SUCCESS]
    assert len(submits) >= 1


@pytest.mark.asyncio
async def test_t13_cart_change_invalidates_confirmation() -> None:
    app = MockAdapter()
    await app.submit_action(
        ActionRequestPayload(
            action_id="pre",
            operation=Operation.CART_ADD_ITEM,
            arguments={"item_id": "drink-cola", "quantity": 1},
        )
    )
    engine = ConversationEngine(adapter=app, planner=DialogueSuitePlanner())
    await engine.handle_text("checkout")
    assert engine.confirmation.state.value == "awaiting"
    await app.simulate_cart_change("drink-cola", quantity=2)
    snap = await app.get_snapshot()
    engine.confirmation.on_cart_or_revision_change(snap.revision)
    assert engine.confirmation.state.value == "none"
    r = await engine.handle_text("yes")
    assert "demo order placed" not in r.assistant_text.lower()


@pytest.mark.asyncio
async def test_t14_timeout_no_duplicate_no_false_success() -> None:
    app = MockAdapter(default_timeout_s=0.05)
    app.set_scenario(ScenarioConfig(mode=ScenarioMode.NEVER_REPLY))
    engine = ConversationEngine(
        adapter=app,
        planner=ScriptedPlanner(
            {
                "add cola": [
                    ToolCall(Operation.CART_ADD_ITEM, {"item_id": "drink-cola", "quantity": 1})
                ]
            }
        ),
    )
    r = await engine.handle_text("add cola")
    assert "success" not in r.assistant_text.lower()
    assert "added" not in r.assistant_text.lower() or "not sure" in r.assistant_text.lower()
    assert r.tool_results[0].status == ActionResultStatus.TIMEOUT_UNKNOWN
    assert not engine.reconnect.may_resend(r.tool_results[0].action_id)


@pytest.mark.asyncio
async def test_t17_provider_failures_honest() -> None:
    engine = ConversationEngine(adapter=MockAdapter(), planner=DialogueSuitePlanner())
    FAULTS.fail_stt = True
    r = await engine.handle_text("show burgers")
    assert r.state == ProductState.ERROR
    assert "listening" not in r.state.value
    assert "type" in r.assistant_text.lower()
    FAULTS.reset()
    FAULTS.fail_llm = True
    r2 = await engine.handle_text("show burgers")
    assert "quota" in r2.assistant_text.lower() or "unavailable" in r2.assistant_text.lower()
    assert "cart is unchanged" in r2.assistant_text.lower() or "unchanged" in r2.assistant_text.lower()


@pytest.mark.asyncio
async def test_t20_interrupt_mutation_reconcile() -> None:
    from foodease_agent.interruption import InterruptionReconciler

    rec = InterruptionReconciler()
    rec.register_pending("action-xyz", "cart.add_item")
    utt = rec.on_barge_in(spoken_so_far="Adding", full_intended="Adding two colas.")
    assert utt.status.value == "interrupted"
    assert "action-xyz" in rec.pending
    reply = rec.late_result_reply("action-xyz", success=True)
    assert reply == "Done."


@pytest.mark.asyncio
async def test_v84_reconnect_mid_checkout() -> None:
    app = MockAdapter()
    await app.submit_action(
        ActionRequestPayload(
            action_id="pre",
            operation=Operation.CART_ADD_ITEM,
            arguments={"item_id": "drink-cola", "quantity": 1},
        )
    )
    engine = ConversationEngine(adapter=app, planner=DialogueSuitePlanner())
    await engine.handle_text("checkout")
    assert engine.confirmation.state.value == "awaiting"
    # Simulate in-flight unknown mutation
    engine.reconnect.unknown_action_ids.add("ghost-submit")
    blocked = guard_resubmit(
        engine.reconnect,
        ActionRequestPayload(
            action_id="ghost-submit",
            operation=Operation.CHECKOUT_SUBMIT_DEMO_ORDER,
            arguments={"confirmed": True},
        ),
    )
    assert blocked is not None
    assert blocked.status == ActionResultStatus.REJECTED

    snap = await engine.reconnect.on_reconnect(app, engine.confirmation)
    assert engine.confirmation.state.value == "none"
    assert snap.revision >= 0


def test_v85_llm_fallback_or_honest_fail() -> None:
    chain = FallbackChain()
    primary = chain.choose_llm(primary_failed=False)
    assert primary.active == chain.llm_primary
    backup = chain.choose_llm(primary_failed=True)
    assert backup.active == chain.llm_backup
    assert backup.reason == "fallback"
    # Honest fail path still available via FAULTS.fail_llm (tested in T17)


def test_confidence_gate_consequential() -> None:
    gate = ConfidenceGate(min_confidence=0.55)
    assert gate.needs_clarification("add two colas", 0.3) is True
    assert gate.needs_clarification("add two colas", 0.9) is False
    assert gate.needs_clarification("stop", 0.1) is False


@pytest.mark.asyncio
async def test_ds21_25_failure_dialogue() -> None:
    """DS-21…DS-25 failure phrasing scenarios."""
    engine = ConversationEngine(adapter=MockAdapter(), planner=DialogueSuitePlanner())

    FAULTS.fail_stt = True
    ds21 = await engine.handle_text("hello")
    assert "type" in ds21.assistant_text.lower()
    FAULTS.reset()

    FAULTS.fail_llm = True
    ds22 = await engine.handle_text("hello")
    assert "unchanged" in ds22.assistant_text.lower() or "unavailable" in ds22.assistant_text.lower()
    FAULTS.reset()

    app = MockAdapter()
    app.set_scenario(ScenarioConfig(mode=ScenarioMode.REJECTED, reason="Out of stock today."))
    eng = ConversationEngine(
        adapter=app,
        planner=ScriptedPlanner(
            {
                "add bbq": [
                    ToolCall(Operation.CART_ADD_ITEM, {"item_id": "burger-soldout", "quantity": 1})
                ]
            }
        ),
    )
    ds23 = await eng.handle_text("add bbq")
    assert "rejected" in ds23.assistant_text.lower() or "stock" in ds23.assistant_text.lower() or "try" in ds23.assistant_text.lower()

    app2 = MockAdapter(default_timeout_s=0.05)
    app2.set_scenario(ScenarioConfig(mode=ScenarioMode.NEVER_REPLY))
    eng2 = ConversationEngine(
        adapter=app2,
        planner=ScriptedPlanner(
            {
                "add cola": [
                    ToolCall(Operation.CART_ADD_ITEM, {"item_id": "drink-cola", "quantity": 1})
                ]
            }
        ),
    )
    ds24 = await eng2.handle_text("add cola")
    assert "not sure" in ds24.assistant_text.lower() or "check" in ds24.assistant_text.lower()

    FAULTS.drop_connection = True
    ds25 = await engine.handle_text("hello")
    assert ds25.state == ProductState.RECONNECTING
    assert "reconnect" in ds25.assistant_text.lower() or "connection" in ds25.assistant_text.lower()


@pytest.mark.asyncio
async def test_v83_chaos_no_duplicate_no_false_success() -> None:
    """Compact chaos: random faults across many turns (scaled; not wall-clock 30 min)."""
    rng = random.Random(42)
    mutations = 0
    false_success = 0
    stuck_error_listening = 0

    for i in range(80):
        FAULTS.reset()
        app = MockAdapter(default_timeout_s=0.05)
        engine = ConversationEngine(adapter=app, planner=DialogueSuitePlanner())
        fault = rng.choice(
            ["none", "stt", "llm", "drop", "reject", "timeout", "low_conf"]
        )
        if fault == "stt":
            FAULTS.fail_stt = True
        elif fault == "llm":
            FAULTS.fail_llm = True
        elif fault == "drop":
            FAULTS.drop_connection = True
        elif fault == "low_conf":
            FAULTS.low_confidence = True
        elif fault == "reject":
            app.set_scenario(ScenarioConfig(mode=ScenarioMode.REJECTED))
        elif fault == "timeout":
            app.set_scenario(ScenarioConfig(mode=ScenarioMode.NEVER_REPLY))

        r = await engine.handle_text("add 1 Cola Can")
        if r.state == ProductState.ERROR and "listening" in r.state.value:
            stuck_error_listening += 1
        if "successfully added" in r.assistant_text.lower():
            false_success += 1
        if r.tool_results:
            for tr in r.tool_results:
                if tr.status == ActionResultStatus.SUCCESS and fault in {"reject", "timeout"}:
                    false_success += 1
                if tr.status == ActionResultStatus.TIMEOUT_UNKNOWN:
                    # attempt illegal resend
                    blocked = guard_resubmit(
                        engine.reconnect,
                        ActionRequestPayload(
                            action_id=tr.action_id,
                            operation=Operation.CART_ADD_ITEM,
                            arguments={"item_id": "drink-cola", "quantity": 1},
                        ),
                    )
                    assert blocked is not None
                    mutations += 1

    assert false_success == 0
    assert stuck_error_listening == 0


@pytest.mark.asyncio
async def test_stop_during_checkout() -> None:
    app = MockAdapter()
    await app.submit_action(
        ActionRequestPayload(
            action_id="pre",
            operation=Operation.CART_ADD_ITEM,
            arguments={"item_id": "drink-cola", "quantity": 1},
        )
    )
    engine = ConversationEngine(adapter=app, planner=DialogueSuitePlanner())
    await engine.handle_text("checkout")
    r = await engine.handle_text("stop")
    assert engine.confirmation.state.value == "none"
    assert "won't place" in r.assistant_text.lower() or "will not" in r.assistant_text.lower() or "stopped" in r.assistant_text.lower()


@pytest.mark.asyncio
async def test_gui_switch_mid_turn_message() -> None:
    r = recover(Va17Situation.GUI_SWITCH_MID_TURN)
    assert "screen" in r.assistant_text.lower() or "guidance" in r.assistant_text.lower()


@pytest.mark.asyncio
async def test_two_matching_items_clarify() -> None:
    r = recover(Va17Situation.TWO_MATCHING)
    assert "which" in r.assistant_text.lower()
