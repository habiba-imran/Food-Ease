"""V9.5 — re-run automatable acceptance + dialogue suite on frozen config."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--skip-dialogue", action="store_true")
    args = p.parse_args()

    tests = [
        "tests/test_phase4_engine.py",
        "tests/test_phase8.py",
        "tests/test_phase5_voice.py",
    ]
    cmd = [sys.executable, "-m", "pytest", "-q", *tests]
    subprocess.check_call(cmd, cwd=str(ROOT))

    if not args.skip_dialogue:
        subprocess.check_call(
            [sys.executable, str(ROOT / "tools" / "run_dialogue_suite.py")],
            cwd=str(ROOT),
        )
    print("V9.5 regression OK")


if __name__ == "__main__":
    main()
