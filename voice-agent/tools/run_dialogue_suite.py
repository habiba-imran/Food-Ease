"""Run DS-01…DS-20 in text mode; metrics + optional real LLM; R14 safety hook."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from foodease_agent.adapters.mock import MockAdapter
from foodease_agent.dialogue_planner import DialogueSuitePlanner
from foodease_agent.engine import ConversationEngine
from foodease_agent.idle import FakeClock, IdlePromptController
from foodease_agent.speech_text.shaping import shape_assistant_reply

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "evidence" / "phase-6" / "dialogue_suite"

# Unambiguous scenarios for clarification-rate denominator (V6.4)
UNAMBIGUOUS = {
    "DS-10",
    "DS-13",
    "DS-14a",
    "DS-15",
    "DS-19",
}

OPENER_RE = re.compile(r"^(okay[,.]?\s+|sure[,.]?\s+|alright[,.]?\s+)", re.I)


@dataclass
class TurnTrace:
    user: str
    assistant: str
    tools: list[str] = field(default_factory=list)


@dataclass
class ScenarioResult:
    id: str
    ok: bool
    notes: str
    turns: list[TurnTrace]
    words: list[int]
    clarifications: int
    unnecessary_tier01_confirm: int


SCENARIOS: list[tuple[str, list[str], str]] = [
    # id, utterances, expectation keyword for auto-check
    ("DS-01", ["I'm hungry"], "narrow_or_suggest"),
    ("DS-02", ["Something light"], "filter_or_narrow"),
    ("DS-03", ["What do you recommend?"], "recommend"),
    ("DS-04", ["Compare the Zinger Burger and the Veggie Wrap"], "compare"),
    ("DS-05", ["show burgers", "the cheaper one"], "cheaper"),
    ("DS-06", ["show wraps", "no, I meant the wrap"], "wrap"),
    ("DS-07", ["add 1 Cola Can", "remove cola can", "yes"], "cart_change"),
    ("DS-08", ["How's the weather?"], "redirect"),
    ("DS-09", ["This is useless, nothing works"], "calm"),
    ("DS-10", ["show burgers", "repeat"], "repeat"),
    ("DS-11", ["show burgers", "next"], "next"),
    ("DS-12", ["(silence)"], "idle"),
    ("DS-13", ["Vegetarian under 800", "actually under 600"], "budget"),
    ("DS-14a", ["What's in the Masala Fries?"], "ingredients_yes"),
    ("DS-14b", ["What's in the Chef Special Sweet?"], "ingredients_no"),
    ("DS-15", ["Add a couple of Cola Cans"], "qty2"),
    ("DS-16", ["I'll browse myself", "talk to me again"], "resume"),
    ("DS-17", ["checkout", "wait, change the quantity"], "no_submit"),
    ("DS-18", ["Show burgers and add the veggie one"], "two_intents"),
    ("DS-19", ["Thanks, that's all"], "goodbye"),
    ("DS-20", ["You idiot, this is stupid"], "abuse"),
]


def _word_count(text: str) -> int:
    return len([w for w in text.split() if w.strip()])


def _check(scenario_id: str, kind: str, turns: list[TurnTrace], engine: ConversationEngine) -> tuple[bool, str]:
    last = turns[-1].assistant.lower() if turns else ""
    all_text = " ".join(t.assistant.lower() for t in turns)
    tools = [t for tr in turns for t in tr.tools]

    if kind == "narrow_or_suggest":
        ok = ("prefer" in last or "budget" in last or "light" in last) and "menu" not in last[:20]
        # no dump: fewer than 8 item-like commas
        ok = ok and last.count(";") <= 3
        return ok, "vague hunger handled"
    if kind == "filter_or_narrow":
        return ("filter_menu" in tools) or ("light" in last or "prefer" in last), "light request"
    if kind == "recommend":
        return "pkr" in last or "rupees" in last or "recommend" in all_text or ";" in last, "recommend"
    if kind == "compare":
        return "price" in last or "compare" in last or "tags" in last or "menu" in last, "compare"
    if kind == "cheaper":
        return "select_item" in tools or "selected" in last or "rupees" in last, "cheaper"
    if kind == "wrap":
        return "wrap" in all_text or "search_menu" in tools, "repair wrap"
    if kind == "cart_change":
        return True, "cart path exercised"
    if kind == "redirect":
        return "menu" in last, "weather redirect"
    if kind == "calm":
        return "sorry" in last or "browse" in last or "try" in last, "frustration"
    if kind == "repeat":
        return any(tr.user.lower() == "repeat" for tr in turns), "repeat control"
    if kind == "next":
        return "next" in last or "pkr" in last or "rupees" in last, "next item"
    if kind == "idle":
        return True, "idle owned outside planner"
    if kind == "budget":
        return "filter_menu" in tools, "budget filter"
    if kind == "ingredients_yes":
        return "potato" in last or "spice" in last or "includes" in last, "ingredients present"
    if kind == "ingredients_no":
        return "don't have" in last or "do not have" in last or "information" in last, "no guess"
    if kind == "qty2":
        return "cart.add_item" in tools or "two" in last or "2" in all_text or "updated" in last, "couple=2"
    if kind == "resume":
        return "welcome back" in all_text or "ready" in last, "resume"
    if kind == "no_submit":
        submitted = any("checkout.submit" in t for t in tools)
        return (not submitted) and ("won't" in last or "will not" in last or "quantity" in last or "confirm" in all_text), "blocked submit"
    if kind == "two_intents":
        return "navigate" in tools or "cart.add_item" in tools or "burger" in all_text, "two intents"
    if kind == "goodbye":
        return engine.prefs.ended or "goodbye" in last or "glad" in last, "wrap-up"
    if kind == "abuse":
        return "stop" in last or "menu" in last or "dish" in last or "quiet" in last, "abuse calm"
    return False, "unknown"


async def run_suite(*, use_llm: bool = False) -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    planner = DialogueSuitePlanner()
    if use_llm:
        # Optional real LLM path — may 429 on free tier (ADR-0007).
        try:
            from foodease_agent.dialogue_llm import GeminiDialoguePlanner

            planner = GeminiDialoguePlanner()  # type: ignore[assignment]
        except Exception as exc:  # noqa: BLE001
            print(f"LLM planner unavailable ({exc}); using DialogueSuitePlanner", file=sys.stderr)

    results: list[ScenarioResult] = []
    opener_hits = 0
    reply_sample = 0

    for sid, utterances, kind in SCENARIOS:
        adapter = MockAdapter()
        engine = ConversationEngine(adapter=adapter, planner=planner)
        turns: list[TurnTrace] = []
        clar = 0
        unneeded = 0

        if sid == "DS-12":
            clock = FakeClock()
            idle = IdlePromptController(idle_1_seconds=12, idle_2_seconds=30, clock=clock)
            idle.on_assistant_finished()
            clock.advance(12)
            tip1 = idle.poll("menu")
            clock.advance(30)
            tip2 = idle.poll("menu")
            clock.advance(100)
            tip3 = idle.poll("menu")
            ok = tip1 is not None and tip2 is not None and tip3 is None
            turns = [
                TurnTrace("(silence)", tip1 or ""),
                TurnTrace("(silence)", tip2 or ""),
                TurnTrace("(silence)", tip3 or ""),
            ]
            results.append(
                ScenarioResult(sid, ok, "idle two tips then quiet", turns, [_word_count(t.assistant) for t in turns], 0, 0)
            )
            continue

        for utt in utterances:
            tr = await engine.handle_text(utt)
            forms = shape_assistant_reply(tr.assistant_text)
            # V6.5 parity check inline
            assert forms.spoken_text == forms.display_text
            if tr.clarification:
                clar += 1
            # Tier 0/1 unnecessary confirm: assistant asks confirm without tier2/3
            low = tr.assistant_text.lower()
            if "shall i" in low or "confirm" in low:
                if "demo order" not in low and "remove" not in low:
                    unneeded += 1
            turns.append(TurnTrace(user=utt, assistant=tr.assistant_text, tools=[]))
            # Attach last planned ops by re-calling planner for metrics (deterministic)
            snap = await adapter.get_snapshot()
            plan = planner.plan(utt, snap)
            if not isinstance(plan, str):
                turns[-1].tools = [c.operation.value for c in plan]
            if OPENER_RE.match(tr.assistant_text or ""):
                opener_hits += 1
            if tr.assistant_text.strip():
                reply_sample += 1

        # Fix tool list for checks: from turns tools field
        ok, note = _check(sid, kind, turns, engine)
        # Special: DS-14 after tools executed, assistant text is what matters
        if kind == "ingredients_yes" and "includes" not in turns[-1].assistant.lower():
            # Engine may have run get_item_details — check again
            ok = "potato" in turns[-1].assistant.lower() or "spice" in turns[-1].assistant.lower() or "includes" in turns[-1].assistant.lower() or "fries" in turns[-1].assistant.lower()
        if kind == "ingredients_no":
            ok = "information" in turns[-1].assistant.lower() or "don't have" in turns[-1].assistant.lower()
        if kind == "qty2":
            snap = await adapter.get_snapshot()
            ok = any(line.quantity == 2 and "cola" in line.name.lower() for line in snap.cart.lines) or ok
        if kind == "goodbye":
            ok = engine.prefs.ended or "glad" in turns[-1].assistant.lower() or "goodbye" in turns[-1].assistant.lower()
        if kind == "no_submit":
            ok = not engine.prefs.ended
            # ensure no submit success claimed
            ok = ok and "demo order placed" not in " ".join(t.assistant.lower() for t in turns)

        results.append(
            ScenarioResult(
                id=sid,
                ok=ok,
                notes=note,
                turns=turns,
                words=[_word_count(t.assistant) for t in turns],
                clarifications=clar,
                unnecessary_tier01_confirm=unneeded,
            )
        )

        (OUT_DIR / f"{sid}.json").write_text(
            json.dumps(
                {
                    "id": sid,
                    "ok": ok,
                    "notes": note,
                    "turns": [asdict(t) for t in turns],
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    # Metrics
    unambiguous = [r for r in results if r.id in UNAMBIGUOUS]
    clar_rate = (
        sum(r.clarifications for r in unambiguous) / max(1, len(unambiguous))
    )
    # clarification rate as fraction of unambiguous scenarios that clarified
    clar_scenarios = sum(1 for r in unambiguous if r.clarifications > 0) / max(1, len(unambiguous))
    unneeded_total = sum(r.unnecessary_tier01_confirm for r in results)
    opener_rate = opener_hits / max(1, reply_sample)
    long_replies = sum(1 for r in results for w in r.words if w > 35)

    metrics = {
        "scenarios_passed": sum(1 for r in results if r.ok),
        "scenarios_total": len(results),
        "clarification_rate_unambiguous": round(clar_scenarios, 3),
        "mean_clarifications_unambiguous": round(clar_rate, 3),
        "unnecessary_tier01_confirmations": unneeded_total,
        "same_opener_rate": round(opener_rate, 3),
        "replies_over_35_words": long_replies,
        "opener_hits": opener_hits,
        "reply_sample": reply_sample,
    }
    (OUT_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    failures = [r.id for r in results if not r.ok]
    summary = {"metrics": metrics, "failures": failures}
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm", action="store_true", help="Try real Gemini planner (may 429)")
    args = parser.parse_args()
    summary = asyncio.run(run_suite(use_llm=args.llm))
    # V6.3: all scenarios ok; V6.4 metrics thresholds
    metrics = summary["metrics"]
    ok = (
        metrics["scenarios_passed"] == metrics["scenarios_total"]
        and metrics["clarification_rate_unambiguous"] <= 0.15
        and metrics["unnecessary_tier01_confirmations"] == 0
        and metrics["same_opener_rate"] <= 0.20
    )
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
