"""Generate evidence/phase-9/latency_report.md from raw JSONL (V9.2)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from foodease_agent.latency_report import (
    load_jsonl,
    markdown_report,
    summarize_metric,
    reliability_rate,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GLOB = ROOT / "evidence" / "phase-9"
DEFAULT_OUT = ROOT / "evidence" / "phase-9" / "latency_report.md"


def collect_jsonl(root: Path) -> list[Path]:
    return sorted(root.rglob("*.jsonl"))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=DEFAULT_GLOB)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--levers-dir", type=Path, default=ROOT / "evidence" / "phase-9" / "levers")
    args = p.parse_args()

    files = collect_jsonl(args.root)
    rows = load_jsonl(files)

    summaries = [
        summarize_metric(
            rows,
            metric_key="greeting_warm_ttfa_ms",
            turn_kind="greeting_warm",
            mode="mode_1",
        ),
        summarize_metric(
            rows,
            metric_key="greeting_cold_ttfa_ms",
            turn_kind="greeting_cold",
            mode="mode_1",
        ),
        summarize_metric(
            rows,
            metric_key="response_ttfa_ms",
            turn_kind="response",
            mode="mode_1",
        ),
        summarize_metric(
            rows,
            metric_key="barge_in_stop_ms",
            turn_kind="barge_in",
            mode="mode_1",
        ),
    ]

    lever_tables: list[tuple[str, list]] = []
    if args.levers_dir.exists():
        for lever_json in sorted(args.levers_dir.glob("lever-*.json")):
            meta = json.loads(lever_json.read_text(encoding="utf-8"))
            lever_files = [Path(p) for p in meta.get("jsonl_files", [])]
            lever_rows = load_jsonl(lever_files)
            lever_tables.append(
                (
                    meta.get("name", lever_json.stem),
                    [
                        summarize_metric(
                            lever_rows,
                            metric_key="response_ttfa_ms",
                            turn_kind="response",
                            mode="mode_1",
                        ),
                        summarize_metric(
                            lever_rows,
                            metric_key="barge_in_stop_ms",
                            turn_kind="barge_in",
                            mode="mode_1",
                        ),
                    ],
                )
            )

    rel = reliability_rate(rows)
    source_files: list[str] = []
    for f in files:
        try:
            source_files.append(str(f.relative_to(ROOT)))
        except ValueError:
            source_files.append(str(f))
    md = markdown_report(
        summaries,
        reliability=rel,
        source_files=source_files,
        lever_tables=lever_tables or None,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(md, encoding="utf-8")
    print(json.dumps({"wrote": str(args.out), "rows": len(rows), "files": len(files)}))


if __name__ == "__main__":
    main()
