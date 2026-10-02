"""Clean-checkout smoke (Phase 11.4) — no provider API calls."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SMOKE_TESTS = [
    "tests/test_config.py",
    "tests/test_env_example_drift.py",
    "tests/adapter_conformance/test_conformance.py",
    "tests/test_phase7.py::test_v77_conformance_livekit_rpc_mockapp",
    "tests/test_phase4_engine.py",
    "tests/test_phase8.py::test_v82_each_va17_row_has_recovery",
]


def main() -> None:
    print("FoodEase smoke — pytest subset (no live providers)")
    cmd = [sys.executable, "-m", "pytest", "-q", *SMOKE_TESTS]
    subprocess.check_call(cmd, cwd=str(ROOT))
    # Handover paths exist
    required = [
        ROOT / "docs" / "handover" / "INTEGRATION_NOTE.md",
        ROOT / "docs" / "handover" / "FRONTEND_QUICKSTART.md",
        ROOT / "docs" / "handover" / "OPEN_DECISIONS.md",
        ROOT / "docs" / "handover" / "DELIVERABLES.md",
        ROOT / ".env.example",
        ROOT / "contract" / "v1" / "schemas" / "transport_defaults.json",
        ROOT / "evidence" / "phase-10" / "acceptance.md",
    ]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
    if missing:
        raise SystemExit(f"Missing handover paths: {missing}")
    print("SMOKE PASS")


if __name__ == "__main__":
    main()
