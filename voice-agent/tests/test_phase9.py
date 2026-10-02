"""Phase 9 — latency report math, campaign manifest, interruption fixtures."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from foodease_agent.latency_report import (
    load_jsonl,
    percentile,
    summarize_metric,
    reliability_rate,
)

ROOT = Path(__file__).resolve().parents[1]


def test_percentile_known_values() -> None:
    vals = [100.0, 200.0, 300.0, 400.0, 500.0]
    assert percentile(vals, 50) == 300.0
    assert percentile(vals, 95) is not None
    assert percentile([], 50) is None


def test_summarize_excludes_dry_run(tmp_path: Path) -> None:
    p = tmp_path / "m.jsonl"
    rows = [
        {"mode": "dry_run", "turn_kind": "response", "response_ttfa_ms": 100},
        {"mode": "mode_1", "turn_kind": "response", "response_ttfa_ms": 1000},
        {"mode": "mode_1", "turn_kind": "response", "response_ttfa_ms": 1500},
    ]
    p.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    loaded = load_jsonl([p])
    s = summarize_metric(loaded, metric_key="response_ttfa_ms", turn_kind="response", mode="mode_1")
    assert s.n == 2
    assert s.p50 == 1250.0
    assert s.met_p50 is False  # target 1200


def test_reliability_rate() -> None:
    rows = [
        {"mode": "mode_1", "turn_kind": "response", "success": True},
        {"mode": "mode_1", "turn_kind": "response", "success": False},
        {"mode": "mode_1", "turn_kind": "barge_in", "success": False},
    ]
    ok, total, rate = reliability_rate(rows)
    assert total == 2
    assert ok == 1
    assert rate == 0.5


def test_campaign_manifest_has_30_plus_10() -> None:
    subprocess.check_call(
        [
            sys.executable,
            str(ROOT / "tools" / "run_latency_campaign.py"),
            "--manifest-only",
        ],
        cwd=str(ROOT),
    )
    manifest = json.loads(
        (ROOT / "evidence" / "phase-9" / "campaign" / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["mode_1"]["scripted_turns"] == 30
    assert manifest["mode_1"]["barge_turns"] == 10


def test_generate_report_from_fixture(tmp_path: Path) -> None:
    raw = tmp_path / "baseline"
    raw.mkdir()
    metrics = raw / "metrics.jsonl"
    samples = [
        {
            "mode": "mode_1",
            "turn_kind": "response",
            "response_ttfa_ms": 900,
            "completed_without_restart": True,
        },
        {
            "mode": "mode_1",
            "turn_kind": "greeting_warm",
            "greeting_warm_ttfa_ms": 700,
            "completed_without_restart": True,
        },
    ]
    metrics.write_text("\n".join(json.dumps(s) for s in samples), encoding="utf-8")
    out = tmp_path / "report.md"
    subprocess.check_call(
        [
            sys.executable,
            str(ROOT / "tools" / "generate_latency_report.py"),
            "--root",
            str(tmp_path),
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
    )
    text = out.read_text(encoding="utf-8")
    assert "Mode 1 headline metrics" in text
    assert "response_ttfa_ms" in text
