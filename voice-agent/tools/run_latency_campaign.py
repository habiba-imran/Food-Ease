"""Phase 9 campaign manifest + Mode 1 live runner hook (V9.2 / V9.3).

Without --live, writes the scripted turn list only (no fabricated timings).
With --live, delegates to inject_live (requires worker in room + .env).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "evidence" / "phase-9" / "campaign"

# 30 ordinary scripted turns (mix of navigation, filter, cart, checkout-adjacent).
SCRIPTED_TURNS: list[dict] = [
    {"id": "L01", "utterance": "show burgers", "turn_kind": "response"},
    {"id": "L02", "utterance": "vegetarian under 800", "turn_kind": "response"},
    {"id": "L03", "utterance": "add 1 Cola Can", "turn_kind": "response"},
    {"id": "L04", "utterance": "what's in the cart", "turn_kind": "response"},
    {"id": "L05", "utterance": "show wraps", "turn_kind": "response"},
    {"id": "L06", "utterance": "add 1 Veggie Wrap", "turn_kind": "response"},
    {"id": "L07", "utterance": "make it 2", "turn_kind": "response"},
    {"id": "L08", "utterance": "make it 1", "turn_kind": "response"},
    {"id": "L09", "utterance": "show drinks", "turn_kind": "response"},
    {"id": "L10", "utterance": "add 1 Masala Fries", "turn_kind": "response"},
    {"id": "L11", "utterance": "go back", "turn_kind": "response"},
    {"id": "L12", "utterance": "show burgers", "turn_kind": "response"},
    {"id": "L13", "utterance": "the second one", "turn_kind": "response"},
    {"id": "L14", "utterance": "add two", "turn_kind": "response"},
    {"id": "L15", "utterance": "remove cola can", "turn_kind": "response"},
    {"id": "L16", "utterance": "yes", "turn_kind": "response"},
    {"id": "L17", "utterance": "show desserts", "turn_kind": "response"},
    {"id": "L18", "utterance": "what's in the Masala Fries?", "turn_kind": "response"},
    {"id": "L19", "utterance": "I'm hungry", "turn_kind": "response"},
    {"id": "L20", "utterance": "something light", "turn_kind": "response"},
    {"id": "L21", "utterance": "what do you recommend?", "turn_kind": "response"},
    {"id": "L22", "utterance": "repeat", "turn_kind": "response"},
    {"id": "L23", "utterance": "help", "turn_kind": "response"},
    {"id": "L24", "utterance": "show sides", "turn_kind": "response"},
    {"id": "L25", "utterance": "add 1 Zinger Burger", "turn_kind": "response"},
    {"id": "L26", "utterance": "checkout", "turn_kind": "response"},
    {"id": "L27", "utterance": "stop", "turn_kind": "response"},
    {"id": "L28", "utterance": "checkout", "turn_kind": "response"},
    {"id": "L29", "utterance": "no", "turn_kind": "response"},
    {"id": "L30", "utterance": "I'll browse myself", "turn_kind": "response"},
]

BARGE_TURNS: list[dict] = [
    {"id": "B01", "utterance": "show burgers", "turn_kind": "barge_in", "interrupt_ms": 400},
    {"id": "B02", "utterance": "add 1 Cola Can", "turn_kind": "barge_in", "interrupt_ms": 500},
    {"id": "B03", "utterance": "vegetarian under 600", "turn_kind": "barge_in", "interrupt_ms": 600},
    {"id": "B04", "utterance": "what do you recommend?", "turn_kind": "barge_in", "interrupt_ms": 450},
    {"id": "B05", "utterance": "show wraps", "turn_kind": "barge_in", "interrupt_ms": 550},
    {"id": "B06", "utterance": "add 1 Veggie Wrap", "turn_kind": "barge_in", "interrupt_ms": 500},
    {"id": "B07", "utterance": "what's in the cart", "turn_kind": "barge_in", "interrupt_ms": 400},
    {"id": "B08", "utterance": "checkout", "turn_kind": "barge_in", "interrupt_ms": 700},
    {"id": "B09", "utterance": "show drinks", "turn_kind": "barge_in", "interrupt_ms": 450},
    {"id": "B10", "utterance": "help", "turn_kind": "barge_in", "interrupt_ms": 350},
]

GREETING_TURNS: list[dict] = [
    {"id": "G-cold-1", "utterance": "(join)", "turn_kind": "greeting_cold", "cold": True},
    {"id": "G-warm-1", "utterance": "(ready)", "turn_kind": "greeting_warm", "cold": False},
]


def write_manifest(out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "mode_1": {
            "scripted_turns": len(SCRIPTED_TURNS),
            "barge_turns": len(BARGE_TURNS),
            "greeting_probes": len(GREETING_TURNS),
            "turns": SCRIPTED_TURNS + BARGE_TURNS + GREETING_TURNS,
        },
        "note": "Run with --live after 9.1 setup; metrics append to --out JSONL.",
    }
    path = out_dir / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest-only", action="store_true", help="Write manifest.json and exit")
    p.add_argument("--live", action="store_true", help="Run Mode 1 live injection campaign")
    p.add_argument("--room", default=None, help="LiveKit room name (required with --live)")
    p.add_argument(
        "--out",
        type=Path,
        default=OUT_DIR / "baseline" / "metrics.jsonl",
        help="Metrics JSONL output (live runs only)",
    )
    p.add_argument("--session-id", default="latency-campaign")
    args = p.parse_args()

    manifest_path = write_manifest(OUT_DIR)
    print(json.dumps({"manifest": str(manifest_path)}))

    if args.manifest_only:
        return

    if not args.live:
        print(
            "No --live: manifest only. Mode 1 timings are not written (R8). "
            "Use --live --room <name> with worker running after completing 9.1 setup.",
            file=sys.stderr,
        )
        return

    if not args.room:
        print("--room is required with --live", file=sys.stderr)
        raise SystemExit(2)

    cmd = [
        sys.executable,
        str(ROOT / "tools" / "inject_live.py"),
        "--room",
        args.room,
        "--out",
        str(args.out),
        "--manifest",
        str(manifest_path),
        "--session-id",
        args.session_id,
    ]
    subprocess.check_call(cmd, cwd=str(ROOT))


if __name__ == "__main__":
    main()
