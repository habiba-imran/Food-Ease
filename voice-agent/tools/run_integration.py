"""Run joint integration scenarios (IR-01…IR-05) against MockAdapter.

Writes orchestration/evidence/integration/report.md + summary.json
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from foodease_agent.integration.scenarios import run_all

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT.parent / "orchestration" / "evidence" / "integration"
CHECKLIST = ROOT.parent / "orchestration" / "docs" / "INTEGRATION_CHECKLIST.md"


def _render_md(results: list, *, generated: str) -> str:
    lines = [
        "# Integration suite report",
        "",
        f"Generated: {generated}",
        "",
        "Driver: in-process MockAdapter (Zainab live adapter = later).",
        "",
        "| ID | Scenario | Result | Detail |",
        "|---|---|---|---|",
    ]
    for r in results:
        mark = "PASS" if r.ok else "FAIL"
        detail = r.detail.replace("|", "/")[:120]
        lines.append(f"| {r.id} | {r.title} | **{mark}** | `{detail}` |")
    lines.append("")
    failed = [r.id for r in results if not r.ok]
    if failed:
        lines.append(f"**Failed:** {', '.join(failed)}")
    else:
        lines.append("**All scenarios passed.**")
    lines.append("")
    lines.append("Checklist template: `orchestration/docs/INTEGRATION_CHECKLIST.md`")
    lines.append("")
    return "\n".join(lines)


def _update_checklist_boxes(results: list) -> None:
    """Best-effort: mark Auto column [x] for passes in the checklist file."""
    if not CHECKLIST.is_file():
        return
    text = CHECKLIST.read_text(encoding="utf-8")
    for r in results:
        # Replace first "| IR-xx | ... | [ ] | [ ] |" auto column
        old = f"| {r.id} |"
        if old not in text:
            continue
        # Line-based replace of Auto checkbox only
        out_lines = []
        for line in text.splitlines():
            if line.startswith(f"| {r.id} |") and "| [ ] |" in line:
                # First checkbox is Auto
                if r.ok:
                    line = line.replace("| [ ] |", "| [x] |", 1)
                else:
                    line = line.replace("| [ ] |", "| [ ] |", 1)
            out_lines.append(line)
        text = "\n".join(out_lines) + "\n"
    CHECKLIST.write_text(text, encoding="utf-8")


async def _main() -> int:
    results = await run_all()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generated = datetime.now(UTC).isoformat()
    summary = {
        "generated": generated,
        "passed": sum(1 for r in results if r.ok),
        "failed": sum(1 for r in results if not r.ok),
        "results": [r.to_dict() for r in results],
    }
    (OUT_DIR / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    report = _render_md(results, generated=generated)
    (OUT_DIR / "report.md").write_text(report, encoding="utf-8")
    _update_checklist_boxes(results)
    print(report)
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
