"""Phase 11 — handover paths + smoke/secret tools."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

HANDOVER = [
    "docs/handover/INTEGRATION_NOTE.md",
    "docs/handover/FRONTEND_QUICKSTART.md",
    "docs/handover/OPEN_DECISIONS.md",
    "docs/handover/DELIVERABLES.md",
    "docs/handover/SAMPLE_DIALOGUE.md",
    "README.md",
]


def test_v114_ten_deliverable_paths_exist() -> None:
    for rel in HANDOVER:
        assert (ROOT / rel).is_file(), rel
    assert (ROOT / "evidence" / "phase-10" / "acceptance.md").is_file()
    assert (ROOT / "contract" / "v1" / "schemas" / "transport_defaults.json").is_file()


def test_secret_scan_clean() -> None:
    subprocess.check_call(
        [sys.executable, str(ROOT / "tools" / "secret_scan.py")],
        cwd=str(ROOT),
    )
