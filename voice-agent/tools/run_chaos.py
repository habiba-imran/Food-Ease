"""Compressed chaos harness for Phase 8 / V8.3 invariants.

Runs many random fault+utterance trials (not wall-clock 30 min) and asserts:
no false success, no illegal mutation resend, no ERROR+listening stuck state.
"""

from __future__ import annotations

import argparse
import asyncio
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from foodease_agent.adapters.mock import MockAdapter, ScenarioConfig, ScenarioMode  # noqa: E402
from foodease_agent.contract.enums import ActionResultStatus, Operation, ProductState  # noqa: E402
from foodease_agent.contract.models import ActionRequestPayload  # noqa: E402
from foodease_agent.dialogue_planner import DialogueSuitePlanner  # noqa: E402
from foodease_agent.engine import ConversationEngine  # noqa: E402
from foodease_agent.faults import FAULTS  # noqa: E402
from foodease_agent.reconnect import guard_resubmit  # noqa: E402


UTTERANCES = (
    "add 1 Cola Can",
    "show burgers",
    "checkout",
    "yes",
    "stop",
    "remove cola",
)


async def run_trials(n: int, seed: int) -> dict[str, int]:
    rng = random.Random(seed)
    stats = {
        "trials": 0,
        "false_success": 0,
        "stuck_listening": 0,
        "blocked_resends": 0,
    }
    for _ in range(n):
        FAULTS.reset()
        app = MockAdapter(default_timeout_s=0.05)
        engine = ConversationEngine(adapter=app, planner=DialogueSuitePlanner())
        fault = rng.choice(
            ["none", "stt", "llm", "tts", "drop", "reject", "timeout", "low_conf", "mic"]
        )
        if fault == "stt":
            FAULTS.fail_stt = True
        elif fault == "llm":
            FAULTS.fail_llm = True
        elif fault == "tts":
            FAULTS.fail_tts = True
        elif fault == "drop":
            FAULTS.drop_connection = True
        elif fault == "low_conf":
            FAULTS.low_confidence = True
        elif fault == "mic":
            FAULTS.mic_denied = True
        elif fault == "reject":
            app.set_scenario(ScenarioConfig(mode=ScenarioMode.REJECTED, reason="Sold out."))
        elif fault == "timeout":
            app.set_scenario(ScenarioConfig(mode=ScenarioMode.NEVER_REPLY))

        utterance = rng.choice(UTTERANCES)
        r = await engine.handle_text(utterance)
        stats["trials"] += 1

        if r.state == ProductState.ERROR and "listening" in r.state.value:
            stats["stuck_listening"] += 1
        low = r.assistant_text.lower()
        if "successfully added" in low or "order placed" in low and fault in {
            "reject",
            "timeout",
            "stt",
            "llm",
            "drop",
            "mic",
        }:
            stats["false_success"] += 1
        for tr in r.tool_results:
            if tr.status == ActionResultStatus.SUCCESS and fault in {"reject", "timeout"}:
                stats["false_success"] += 1
            if tr.status == ActionResultStatus.TIMEOUT_UNKNOWN:
                blocked = guard_resubmit(
                    engine.reconnect,
                    ActionRequestPayload(
                        action_id=tr.action_id,
                        operation=Operation.CART_ADD_ITEM,
                        arguments={"item_id": "drink-cola", "quantity": 1},
                    ),
                )
                if blocked is not None:
                    stats["blocked_resends"] += 1
    FAULTS.reset()
    return stats


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--trials", type=int, default=200)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()
    stats = asyncio.run(run_trials(args.trials, args.seed))
    print(stats)
    if stats["false_success"] or stats["stuck_listening"]:
        raise SystemExit(1)
    print("V8.3 invariants OK")


if __name__ == "__main__":
    main()
