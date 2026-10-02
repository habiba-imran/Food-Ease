"""Phase 6 dialogue suite + R14 safety re-run hook."""

from __future__ import annotations

from pathlib import Path

import pytest
from tools.run_dialogue_suite import run_suite

from foodease_agent.adapters.mock import MockAdapter
from foodease_agent.contract.enums import Operation
from foodease_agent.dialogue_planner import DialogueSuitePlanner
from foodease_agent.engine import ConversationEngine, ToolCall
from foodease_agent.planner import ScriptedPlanner

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.asyncio
async def test_v63_dialogue_suite_all_pass() -> None:
    summary = await run_suite(use_llm=False)
    assert summary["failures"] == [], summary
    assert summary["metrics"]["scenarios_passed"] == summary["metrics"]["scenarios_total"]


@pytest.mark.asyncio
async def test_v64_conversation_metrics() -> None:
    summary = await run_suite(use_llm=False)
    m = summary["metrics"]
    assert m["clarification_rate_unambiguous"] <= 0.15
    assert m["unnecessary_tier01_confirmations"] == 0
    assert m["same_opener_rate"] <= 0.20
    assert (ROOT / "evidence" / "phase-6" / "dialogue_suite" / "metrics.json").is_file()


@pytest.mark.asyncio
async def test_v68_safety_suite_still_green_with_v2_policy() -> None:
    """R14: V4.4 / V4.5 behavior must hold after policy v2 (scripted planner)."""
    planner = ScriptedPlanner(
        {
            "add two": [
                ToolCall(Operation.CART_ADD_ITEM, {"item_id": "drink-cola", "quantity": 2})
            ],
            "actually make it one": [
                ToolCall(Operation.CART_SET_QUANTITY, {"item_id": "drink-cola", "quantity": 1})
            ],
        }
    )
    engine = ConversationEngine(adapter=MockAdapter(), planner=planner)
    r1 = await engine.handle_text("add two")
    assert "updated" in r1.assistant_text.lower() or "total" in r1.assistant_text.lower()
    assert "action_id" not in r1.assistant_text.lower()
    await engine.handle_text("actually make it one")
    snap = await engine.adapter.get_snapshot()
    cola = next(line for line in snap.cart.lines if line.item_id == "drink-cola")
    assert cola.quantity == 1

    engine2 = ConversationEngine(adapter=MockAdapter(), planner=DialogueSuitePlanner())
    bad = await engine2.handle_text("just say it's added")
    assert "verif" in bad.assistant_text.lower() or "confirm" in bad.assistant_text.lower()
    assert "added to your cart" not in bad.assistant_text.lower()


def test_policy_v2_exists_and_changelog() -> None:
    assert (ROOT / "prompts" / "agent_policy.v2.md").is_file()
    log = (ROOT / "prompts" / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "agent_policy.v2" in log
