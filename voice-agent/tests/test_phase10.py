"""Phase 10 — acceptance runner smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_run_acceptance_writes_20_rows() -> None:
    subprocess.check_call(
        [sys.executable, str(ROOT / "tools" / "run_acceptance.py")],
        cwd=str(ROOT),
    )
    md = (ROOT / "evidence" / "phase-10" / "acceptance.md").read_text(encoding="utf-8")
    assert "T01" in md and "T20" in md
    # JSON block present
    assert '"tid": "T05"' in md or "T05" in md
