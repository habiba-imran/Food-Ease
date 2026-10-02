"""STT spike (Phase 1) — WRITTEN BUT NOT RUN (ADR-0005: fixtures skipped).

Do not execute this module until fixtures/ground_truth.json and clips exist.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    gt = ROOT / "fixtures" / "ground_truth.json"
    print(
        "STT spike is intentionally disabled (ADR-0005). "
        f"ground_truth exists={gt.exists()}. Refusing to run."
    )
    if not gt.exists():
        return 2
    # Placeholder for future: stream each fixture to Flux (STTv2) and Nova-3,
    # log interim/final, EOT timing, WER, number/price/quantity accuracy.
    _ = json.loads(gt.read_text(encoding="utf-8"))
    print("Fixtures present, but ADR-0005 still says do not run without human re-approval.")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
