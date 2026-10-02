"""Headless injection client — produces metrics JSONL (Phase 7.8 / V7.9).

Full LiveKit WAV publish needs a live room; this tool always writes a valid
metrics record structure. Optional --live is reserved for later wiring.
"""

from __future__ import annotations

import argparse
import json
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
    args = parser.parse_args()

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
    # Simulated pipeline timings for dry-run (not claimed as live measurements)
    end_of_turn = 450.0
    llm_ft = 180.0
    tts_fb = 220.0
    audible = 620.0
    if args.wav and args.wav.exists():
        # Presence of WAV noted; full LiveKit publish is Phase 9 campaign territory
        end_of_turn = 500.0
    metrics = TurnMetrics(
        turn_id=turn_id,
        session_id=args.session_id,
        config_hash=logger.hash,
        end_of_turn_delay_ms=end_of_turn,
        llm_first_token_ms=llm_ft,
        tts_first_byte_ms=tts_fb,
        audible_ttfa_ms=audible,
        extra={
            "mode": "dry_run",
            "interrupt_at_ms": args.interrupt_at_ms,
            "elapsed_tool_ms": round((time.perf_counter() - t0) * 1000, 2),
            "note": "dry_run timings are structural placeholders, not live Mode-1 measurements (R8)",
        },
    )
    logger.write(metrics)
    print(json.dumps({"wrote": str(args.out), "turn_id": turn_id, "config_hash": logger.hash}))


if __name__ == "__main__":
    main()
