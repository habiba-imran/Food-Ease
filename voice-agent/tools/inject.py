"""Headless injection client — produces metrics JSONL (Phase 7.8 / V7.9).

Full LiveKit WAV publish needs a live room; this tool always writes a valid
metrics record structure. Optional --live is reserved for later wiring.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from pathlib import Path

from foodease_agent.metrics import MetricsLogger, TurnMetrics

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "evidence" / "phase-7" / "metrics.jsonl"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--wav", type=Path, default=None, help="Optional pre-recorded mic WAV")
    parser.add_argument("--interrupt-at-ms", type=float, default=None)
    parser.add_argument("--session-id", default="inject-session")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write one structural row labelled dry_run (not Mode 1 measurements)",
    )
    args = parser.parse_args()

    if not args.dry_run:
        print(
            json.dumps(
                {
                    "error": "Mode 1 requires tools/inject_live.py with --room and a live worker.",
                    "hint": "Use --dry-run only for JSONL schema checks.",
                }
            ),
            file=sys.stderr,
        )
        raise SystemExit(2)

    logger = MetricsLogger(
        args.out,
        config={
            "tool": "inject.py",
            "wav": str(args.wav) if args.wav else None,
            "interrupt_at_ms": args.interrupt_at_ms,
            "stt": "flux-general-en",
            "tts": "sonic-3.6",
            "llm": "gemini-3.1-flash-lite",
        },
    )
    turn_id = f"turn-{uuid.uuid4().hex[:8]}"
    t0 = time.perf_counter()
    metrics = TurnMetrics(
        turn_id=turn_id,
        session_id=args.session_id,
        config_hash=logger.hash,
        end_of_turn_delay_ms=None,
        llm_first_token_ms=None,
        tts_first_byte_ms=None,
        audible_ttfa_ms=None,
        extra={
            "mode": "dry_run",
            "interrupt_at_ms": args.interrupt_at_ms,
            "elapsed_tool_ms": round((time.perf_counter() - t0) * 1000, 2),
            "note": "schema check only — not counted toward §7 targets (R8)",
        },
    )
    logger.write(metrics)
    print(json.dumps({"wrote": str(args.out), "turn_id": turn_id, "config_hash": logger.hash}))


if __name__ == "__main__":
    main()
