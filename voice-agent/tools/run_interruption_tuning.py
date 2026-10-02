"""Phase 9.4 — interruption threshold fixtures (no provider calls)."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence" / "phase-9" / "interruption_tuning.json"

# Synthetic VAD-like segments: (duration_s, should_count_as_interrupt)
FIXTURES: list[tuple[str, float, bool]] = [
    ("short_noise_burst", 0.25, False),
    ("user_stop_command", 0.55, True),
    ("mid_sentence_pause", 0.35, False),
    ("clear_barge_in", 0.70, True),
    ("breath_artifact", 0.40, False),
    ("two_word_overlap", 0.60, True),
]


@dataclass(frozen=True)
class ThresholdResult:
    min_duration: float
    false_positive: int
    missed: int


def evaluate(min_duration: float) -> ThresholdResult:
    fp = missed = 0
    for _name, duration, should in FIXTURES:
        detected = duration >= min_duration
        if detected and not should:
            fp += 1
        if not detected and should:
            missed += 1
    return ThresholdResult(min_duration=min_duration, false_positive=fp, missed=missed)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--min-duration", type=float, default=0.5)
    p.add_argument("--sweep", action="store_true", help="Try 0.35..0.65 step 0.05")
    args = p.parse_args()

    results: list[dict] = []
    if args.sweep:
        d = 0.35
        while d <= 0.651:
            r = evaluate(round(d, 2))
            results.append(r.__dict__)
            d += 0.05
    else:
        results.append(evaluate(args.min_duration).__dict__)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"fixtures": len(FIXTURES), "results": results}, indent=2))
    print(json.dumps({"wrote": str(OUT), "results": results}))


if __name__ == "__main__":
    main()
