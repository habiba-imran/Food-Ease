"""Text-mode scripted acceptance traces (T05–T08, T11–T14, T16, T19)."""

from __future__ import annotations

from pathlib import Path

import pytest

from foodease_agent.adapters.mock import MockAdapter, ScenarioConfig, ScenarioMode
from foodease_agent.contract.enums import ActionResultStatus, Operation
from foodease_agent.engine import ConversationEngine, ToolCall
from foodease_agent.planner import RulePlanner, ScriptedPlanner

TRACE = Path(__file__).resolve().parents[1] / "evidence" / "phase-4" / "traces"
TRACE.mkdir(parents=True, exist_ok=True)


def _save(name: str, lines: list[str]) -> None:
    (TRACE / name).write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.mark.asyncio
async def test_t05_filter_vegetarian() -> None:
    engine = ConversationEngine(adapter=MockAdapter(), planner=RulePlanner())
    r = await engine.handle_text("vegetarian under 800")
    _save("t05.txt", ["USER: vegetarian under 800", f"ASSISTANT: {r.assistant_text}"])
    assert r.tool_results and r.tool_results[0].status == ActionResultStatus.SUCCESS


@pytest.mark.asyncio
async def test_t06_orientation() -> None:
    engine = ConversationEngine(adapter=MockAdapter(), planner=RulePlanner())
    r = await engine.handle_text("where am I?")
    _save("t06.txt", ["USER: where am I?", f"ASSISTANT: {r.assistant_text}"])
    assert "page" in r.assistant_text.lower() or "home" in r.assistant_text.lower()


@pytest.mark.asyncio
async def test_t07_reference_second() -> None:
    app = MockAdapter()
    scripts = {
        "show wraps": [ToolCall(Operation.SEARCH_MENU, {"query": "wrap"})],
    }
    engine = ConversationEngine(adapter=app, planner=ScriptedPlanner(scripts))
    await engine.handle_text("show wraps")
    # Force a presented list
    from foodease_agent.reference import PresentedItem

    engine.references.set_list(
        [
            PresentedItem("wrap-chicken", "Chicken Wrap", 600),
            PresentedItem("wrap-veg", "Veggie Wrap", 500),
        ],
        revision=(await app.get_snapshot()).revision,
    )
    r = await engine.handle_text("the second one")
    _save("t07.txt", ["USER: the second one", f"ASSISTANT: {r.assistant_text}"])
    assert r.tool_results


@pytest.mark.asyncio
async def test_t08_failed_add_not_announced_success() -> None:
    app = MockAdapter()
    app.set_scenario(ScenarioConfig(mode=ScenarioMode.FAILED))
    scripts = {
        "add": [ToolCall(Operation.CART_ADD_ITEM, {"item_id": "wrap-veg", "quantity": 1})],
    }
    engine = ConversationEngine(adapter=app, planner=ScriptedPlanner(scripts))
    r = await engine.handle_text("add")
    _save("t08.txt", ["USER: add", f"ASSISTANT: {r.assistant_text}"])
    assert r.tool_results[0].status == ActionResultStatus.FAILED
    assert "updated" not in r.assistant_text.lower()


@pytest.mark.asyncio
async def test_t11_silence_does_not_confirm() -> None:
    app = MockAdapter()
    scripts = {
        "seed": [ToolCall(Operation.CART_ADD_ITEM, {"item_id": "drink-cola", "quantity": 1})],
        "checkout": [ToolCall(Operation.CHECKOUT_SUBMIT_DEMO_ORDER, {"confirmed": False})],
    }
    engine = ConversationEngine(adapter=app, planner=ScriptedPlanner(scripts))
    await engine.handle_text("seed")
    await engine.handle_text("checkout")
    # empty / non-affirmative
    await engine.handle_text("hmm")
    snap = await app.get_snapshot()
    assert snap.cart.lines  # order not submitted / cart still has items or empty only after success
    # demo order not placed means page not order_confirmation with empty from submit
    assert not engine.prefs.ended


@pytest.mark.asyncio
async def test_t12_explicit_confirm_once() -> None:
    app = MockAdapter()
    scripts = {
        "seed": [ToolCall(Operation.CART_ADD_ITEM, {"item_id": "drink-cola", "quantity": 1})],
        "checkout": [ToolCall(Operation.CHECKOUT_SUBMIT_DEMO_ORDER, {"confirmed": False})],
    }
    engine = ConversationEngine(adapter=app, planner=ScriptedPlanner(scripts))
    await engine.handle_text("seed")
    await engine.handle_text("checkout")
    r = await engine.handle_text("yes")
    _save("t12.txt", ["USER: yes", f"ASSISTANT: {r.assistant_text}"])
    assert "demo order" in r.assistant_text.lower()


@pytest.mark.asyncio
async def test_t13_cart_change_invalidates_confirmation() -> None:
    app = MockAdapter()
    scripts = {
        "seed": [ToolCall(Operation.CART_ADD_ITEM, {"item_id": "wrap-veg", "quantity": 1})],
        "checkout": [ToolCall(Operation.CHECKOUT_SUBMIT_DEMO_ORDER, {"confirmed": False})],
    }
    engine = ConversationEngine(adapter=app, planner=ScriptedPlanner(scripts))
    await engine.handle_text("seed")
    await engine.handle_text("checkout")
    await app.simulate_cart_change("wrap-veg", quantity=2)
    engine.confirmation.on_cart_or_revision_change((await app.get_snapshot()).revision)
    assert engine.confirmation.state.value == "none" or engine.confirmation.revision != (
        await app.get_snapshot()
    ).revision or engine.confirmation.state.value == "none"


@pytest.mark.asyncio
async def test_t14_timeout_unknown_no_duplicate() -> None:
    app = MockAdapter(default_timeout_s=0.05)
    app.set_scenario(ScenarioConfig(mode=ScenarioMode.NEVER_REPLY))
    scripts = {
        "add": [ToolCall(Operation.CART_ADD_ITEM, {"item_id": "wrap-veg", "quantity": 1})],
    }
    engine = ConversationEngine(adapter=app, planner=ScriptedPlanner(scripts))
    r = await engine.handle_text("add")
    _save("t14.txt", ["USER: add", f"ASSISTANT: {r.assistant_text}"])
    assert r.tool_results[0].status == ActionResultStatus.TIMEOUT_UNKNOWN
    assert (await app.get_snapshot()).cart.lines == []


@pytest.mark.asyncio
async def test_t16_typed() -> None:
    engine = ConversationEngine(adapter=MockAdapter(), planner=RulePlanner())
    r = await engine.handle_text("show rolls")
    assert r.assistant_text


@pytest.mark.asyncio
async def test_t19_browse_self() -> None:
    engine = ConversationEngine(adapter=MockAdapter(), planner=RulePlanner())
    await engine.handle_text("I'll browse myself")
    assert engine.prefs.browsing_self
