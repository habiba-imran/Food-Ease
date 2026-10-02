"""Phase 9 — aggregate latency JSONL and compare to SPEC §7 targets (R8)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

Mode = Literal["mode_1", "mode_2", "dry_run"]

# Project targets from docs/SPEC.md §7 (goals, not guarantees).
TARGETS: dict[str, tuple[float | None, float | None]] = {
    "greeting_warm_ttfa_ms": (800.0, 1500.0),
    "greeting_cold_ttfa_ms": (2000.0, 4000.0),
    "response_ttfa_ms": (1200.0, 2500.0),
    "barge_in_stop_ms": (None, 350.0),  # p95 only
}

RELIABILITY_TARGET = 0.95


@dataclass(frozen=True)
class MetricSummary:
    metric: str
    mode: str
    n: int
    p50: float | None
    p95: float | None
    target_p50: float | None
    target_p95: float | None
    met_p50: bool | None
    met_p95: bool | None


def percentile(sorted_values: list[float], p: float) -> float | None:
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return sorted_values[0]
    k = (len(sorted_values) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_values) - 1)
    if f == c:
        return sorted_values[f]
    return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)


def load_jsonl(paths: list[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _mode_label(row: dict[str, Any]) -> str:
    raw = row.get("mode") or row.get("extra", {}).get("mode") or "unknown"
    if raw in {"mode_1", "1", "Mode 1"}:
        return "mode_1"
    if raw in {"mode_2", "2", "Mode 2"}:
        return "mode_2"
    if raw == "dry_run":
        return "dry_run"
    return str(raw)


def _value(row: dict[str, Any], key: str) -> float | None:
    v = row.get(key)
    if v is None and key == "response_ttfa_ms":
        v = row.get("audible_ttfa_ms")
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def summarize_metric(
    rows: list[dict[str, Any]],
    *,
    metric_key: str,
    turn_kind: str | None = None,
    mode: str | None = None,
    exclude_dry_run: bool = True,
) -> MetricSummary:
    filtered: list[float] = []
    for row in rows:
        m = _mode_label(row)
        if exclude_dry_run and m == "dry_run":
            continue
        if mode is not None and m != mode:
            continue
        kind = row.get("turn_kind") or row.get("extra", {}).get("turn_kind")
        if turn_kind is not None and kind != turn_kind:
            continue
        val = _value(row, metric_key)
        if val is not None:
            filtered.append(val)
    filtered.sort()
    p50 = percentile(filtered, 50)
    p95 = percentile(filtered, 95)
    t_p50, t_p95 = TARGETS.get(metric_key, (None, None))
    met_p50 = None if t_p50 is None or p50 is None else p50 <= t_p50
    met_p95 = None if t_p95 is None or p95 is None else p95 <= t_p95
    label_mode = mode or "all_measured"
    return MetricSummary(
        metric=metric_key,
        mode=label_mode,
        n=len(filtered),
        p50=p50,
        p95=p95,
        target_p50=t_p50,
        target_p95=t_p95,
        met_p50=met_p50,
        met_p95=met_p95,
    )


def reliability_rate(rows: list[dict[str, Any]], *, exclude_dry_run: bool = True) -> tuple[int, int, float | None]:
    total = 0
    ok = 0
    for row in rows:
        m = _mode_label(row)
        if exclude_dry_run and m == "dry_run":
            continue
        if row.get("turn_kind") == "barge_in":
            continue
        total += 1
        if row.get("completed_without_restart", row.get("success", True)):
            ok += 1
    if total == 0:
        return 0, 0, None
    return ok, total, ok / total


def markdown_report(
    summaries: list[MetricSummary],
    *,
    reliability: tuple[int, int, float | None],
    source_files: list[str],
    lever_tables: list[tuple[str, list[MetricSummary]]] | None = None,
) -> str:
    lines = [
        "# Latency report (generated)",
        "",
        "All headline numbers are derived from raw JSONL only (R8). "
        "`dry_run` rows are excluded from targets.",
        "",
        f"**Sources:** {', '.join(source_files) or '(none)'}",
        "",
        "## Mode 1 headline metrics",
        "",
        "| Metric | n | p50 (ms) | target p50 | met | p95 (ms) | target p95 | met |",
        "|---|---:|---:|---:|:---:|---:|---:|:---:|",
    ]
    for s in summaries:
        lines.append(
            f"| {s.metric} | {s.n} | {_fmt(s.p50)} | {_fmt(s.target_p50)} | {_tick(s.met_p50)} | "
            f"{_fmt(s.p95)} | {_fmt(s.target_p95)} | {_tick(s.met_p95)} |"
        )
    ok, total, rate = reliability
    lines.extend(["", "## Reliability (scripted turns, excluding barge-in probes)", ""])
    if rate is not None:
        lines.append(f"- Completed without restart: **{ok}/{total}** ({rate * 100:.1f}%)")
    else:
        lines.append("- No measured turns yet.")
    lines.append(f"- Target: ≥ {RELIABILITY_TARGET * 100:.0f}%")
    lines.append("")
    if lever_tables:
        lines.append("## After-each-lever snapshots")
        lines.append("")
        for name, lever_sums in lever_tables:
            lines.append(f"### {name}")
            lines.append("")
            lines.append("| Metric | n | p50 | p95 |")
            lines.append("|---|---:|---:|---:|")
            for s in lever_sums:
                lines.append(f"| {s.metric} | {s.n} | {_fmt(s.p50)} | {_fmt(s.p95)} |")
            lines.append("")
    return "\n".join(lines)


def _fmt(v: float | None) -> str:
    if v is None:
        return "—"
    return f"{v:.0f}"


def _tick(v: bool | None) -> str:
    if v is None:
        return "—"
    return "yes" if v else "no"

