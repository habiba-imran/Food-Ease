"""Prepare and evaluate operator-observed final acceptance. Never run providers."""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "orchestration/evidence/final/phase-09"
DEVICES = ("chrome_desktop", "edge_desktop", "phone")
ACCESS = ("keyboard", "screen_reader")
FAULTS = ("stt", "llm", "tts", "room", "http", "rpc_timeout", "dispatch", "app_seat", "credentials")


def scenarios() -> list[dict]:
    sources = [
        (ROOT / "orchestration/docs/FINAL_ORCHESTRATION_IMPLEMENTATION_PLAN.md", r"O-\d{2}", 21),
        (ROOT / "Zainab_Web_Application_UI_UX_Requirements_Specification (1).md", r"W\d{2}", 22),
        (ROOT / "voice-agent/docs/SPEC.md", r"T\d{2}", 20),
    ]
    rows = []
    for path, pattern, count in sources:
        matches = re.findall(
            rf"^\| ({pattern}) \| (.*?) \| (.*?) \|$", path.read_text(encoding="utf-8"), re.M
        )
        if len(matches) != count or len({row[0] for row in matches}) != count:
            raise ValueError("Acceptance specification coverage changed")
        rows += [
            {
                "id": key,
                "scenario": scenario,
                "expected": expected,
                "status": "not_run",
                "evidence": "",
                "observer": "",
            }
            for key, scenario, expected in matches
        ]
    return rows


def prepare(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    if (output / "observations.json").exists():
        raise ValueError("Refusing to overwrite existing observations")

    def checks(ids):
        return [{"id": key, "status": "not_run", "evidence": "", "observer": ""} for key in ids]

    data = {
        "schema_version": 1,
        "kind": "not_run",
        "human_observed": False,
        "transport": "not_run",
        "providers": "not_run",
        "website": "real",
        "environment_evidence": "",
        "real_model_turns": 0,
        "scenarios": scenarios(),
        "devices": checks(DEVICES),
        "accessibility": checks(ACCESS),
        "faults": checks(FAULTS),
        "listeners": [],
        "samples": [],
    }
    (output / "observations.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (output / "README.md").write_text(
        "# Operator evidence\n\nNo checks have been run. Use FINAL_RUNBOOK.md.\n"
        "Keep original failed attempts; do not substitute SDK/server time for audible timing.\n"
        "Evidence paths stay inside this folder. No tokens, raw audio or personal data.\n"
        "Ratings: listeners [{id, naturalness, helpfulness, evidence}]. Scores are 1..5.\n"
        "Samples: [{sample_id, kind, warmth, clock_id, source, onset_ms, playback_ms, "
        "completed, genuine, evidence}]. kind=greeting/response/interruption; warmth=warm/cold; "
        "source=audible_observation. Each timing pair uses one common clock. "
        "A failed completion may leave playback_ms null. Never omit failed attempts.\n"
        "Evaluation checks operator attestations; it cannot independently certify their truth.\n",
        encoding="utf-8",
    )


def local_reference(value: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 240
        or "\\" in value
        or ":" in value
        or Path(value).is_absolute()
        or ".." in Path(value).parts
        or ".env" in Path(value).name
        or Path(value).suffix.lower() in {".wav", ".mp3", ".mp4"}
    ):
        raise ValueError("Use a relative, non-secret evidence file inside the run directory")
    return value


def artifact(output: Path, value: str) -> None:
    path = (output / local_reference(value)).resolve()
    if not path.is_relative_to(output.resolve()) or not path.is_file() or not path.stat().st_size:
        raise ValueError("Evidence file is missing, empty or outside this run")


def percentile(values: list[float], fraction: float) -> float | None:
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)] if values else None


def validate_sample(row: dict) -> dict:
    keys = {
        "sample_id",
        "kind",
        "warmth",
        "clock_id",
        "source",
        "onset_ms",
        "playback_ms",
        "completed",
        "genuine",
        "evidence",
    }
    if set(row) != keys:
        raise ValueError("Unexpected or missing measurement fields")
    if row["kind"] not in {"greeting", "response", "interruption"} or row["warmth"] not in {
        "warm",
        "cold",
    }:
        raise ValueError("Invalid measurement kind or warmth")
    if row["source"] != "audible_observation" or not row["clock_id"] or not row["sample_id"]:
        raise ValueError("Measurements require actual audible observations and a common clock")
    if type(row["completed"]) is not bool or type(row["genuine"]) is not bool:
        raise ValueError("Completion and genuine interruption must be explicit booleans")
    start, end = row["onset_ms"], row["playback_ms"]
    if type(start) not in {int, float} or not math.isfinite(start) or start < 0:
        raise ValueError("Invalid measured onset")
    if end is None and not row["completed"]:
        latency = None
    elif (
        not isinstance(end, int | float)
        or isinstance(end, bool)
        or not math.isfinite(end)
        or end < start
    ):
        raise ValueError("Invalid measured playback time")
    else:
        latency = end - start
    local_reference(row["evidence"])
    return {**row, "latency_ms": latency}


def evaluate(output: Path) -> dict:
    path = output / "observations.json"
    if path.stat().st_size > 1_000_000:
        raise ValueError("Evidence manifest exceeds the bounded review budget")
    data = json.loads(path.read_text(encoding="utf-8"))
    allowed = {
        "schema_version",
        "kind",
        "human_observed",
        "transport",
        "providers",
        "website",
        "environment_evidence",
        "real_model_turns",
        "scenarios",
        "devices",
        "accessibility",
        "faults",
        "listeners",
        "samples",
    }
    if set(data) != allowed or data["schema_version"] != 1:
        raise ValueError("Unexpected or missing manifest fields")
    complete = {}
    any_failed = False
    canonical = {row["id"]: row for row in scenarios()}
    for group, expected in [
        ("scenarios", [r["id"] for r in scenarios()]),
        ("devices", DEVICES),
        ("accessibility", ACCESS),
        ("faults", FAULTS),
    ]:
        rows = data[group]
        if (
            not isinstance(rows, list)
            or len(rows) != len(expected)
            or {r["id"] for r in rows} != set(expected)
        ):
            raise ValueError("Missing, repeated or unknown acceptance IDs")
        for row in rows:
            keys = {"id", "status", "evidence", "observer"}
            if group == "scenarios":
                keys |= {"scenario", "expected"}
                if any(
                    row.get(field) != canonical[row["id"]][field]
                    for field in ("scenario", "expected")
                ):
                    raise ValueError("Do not change the specified acceptance expectation")
            if set(row) != keys or row["status"] not in {"pass", "fail", "not_run"}:
                raise ValueError("Invalid acceptance observation")
            if row["status"] != "not_run":
                artifact(output, row["evidence"])
                if not isinstance(row["observer"], str) or not row["observer"].strip():
                    raise ValueError("Performed observations need an observer alias")
            any_failed |= row["status"] == "fail"
        complete[group] = all(row["status"] == "pass" for row in rows)
    if not isinstance(data["samples"], list) or len(data["samples"]) > 2000:
        raise ValueError("Measurement set exceeds the bounded review budget")
    samples = [validate_sample(row) for row in data["samples"]]
    if len({row["sample_id"] for row in samples}) != len(samples):
        raise ValueError("Duplicate measurement sample")
    for sample in samples:
        artifact(output, sample["evidence"])
    groups = {}
    for kind in ("greeting", "response", "interruption"):
        for warmth in ("warm", "cold"):
            rows = [
                r
                for r in samples
                if r["kind"] == kind
                and r["warmth"] == warmth
                and (kind != "interruption" or r["genuine"])
            ]
            measured = [
                r["latency_ms"] for r in rows if r["completed"] and r["latency_ms"] is not None
            ]
            groups[f"{kind}_{warmth}"] = {
                "attempts": len(rows),
                "measured": len(measured),
                "p50_ms": percentile(measured, 0.5),
                "p95_ms": percentile(measured, 0.95),
            }
    responses = [r for r in samples if r["kind"] == "response"]
    interruptions = [r for r in samples if r["kind"] == "interruption" and r["genuine"]]
    reliability = sum(r["completed"] for r in responses) / len(responses) if responses else None

    def within(key, p50, p95):
        row = groups[key]
        return row["p50_ms"] is not None and row["p50_ms"] <= p50 and row["p95_ms"] <= p95

    stops = [
        r["latency_ms"] for r in interruptions if r["completed"] and r["latency_ms"] is not None
    ]
    stop_p95 = percentile(stops, 0.95)
    targets = bool(
        len(responses) >= 30
        and len(interruptions) >= 10
        and len(stops) >= 10
        and reliability is not None
        and reliability >= 0.95
        and within("greeting_warm", 800, 1500)
        and within("greeting_cold", 2000, 4000)
        and within("response_warm", 1200, 2500)
        and within("response_cold", 1200, 2500)
        and stop_p95 is not None
        and stop_p95 <= 350
    )
    listeners = data["listeners"]
    if not isinstance(listeners, list) or len(listeners) > 100:
        raise ValueError("Invalid listener set")
    for row in listeners:
        if set(row) != {"id", "naturalness", "helpfulness", "evidence"} or not row["id"]:
            raise ValueError("Invalid listening observation")
        for score in (row["naturalness"], row["helpfulness"]):
            if type(score) not in {int, float} or not math.isfinite(score) or not 1 <= score <= 5:
                raise ValueError("Listener scores must be actual values from 1 to 5")
        artifact(output, row["evidence"])
    if len({r["id"] for r in listeners}) != len(listeners):
        raise ValueError("Listener aliases must be distinct")
    quality = len(listeners) >= 3 and all(
        statistics.median(r[k] for r in listeners) >= 4 for k in ("naturalness", "helpfulness")
    )
    if type(data["real_model_turns"]) is not int or data["real_model_turns"] < 0:
        raise ValueError("Invalid real-model sample count")
    if data["environment_evidence"]:
        artifact(output, data["environment_evidence"])
    provenance = (
        data["kind"] == "live"
        and data["human_observed"] is True
        and data["transport"] == "livekit"
        and data["providers"] == "live"
        and data["website"] == "real"
        and bool(data["environment_evidence"])
    )
    passed = (
        provenance
        and all(complete.values())
        and targets
        and quality
        and data["real_model_turns"] >= 40
    )
    measured_targets_failed = (
        len(responses) >= 30
        and len(interruptions) >= 10
        and all(
            groups[key]["measured"]
            for key in ("greeting_warm", "greeting_cold", "response_warm", "response_cold")
        )
        and not targets
    )
    report = {
        "live_gate": "passed"
        if passed
        else "failed"
        if any_failed or measured_targets_failed
        else "pending",
        "evidence_source": "operator attestations; not independently certified",
        "complete": complete,
        "provenance_complete": provenance,
        "audible_samples": len(samples),
        "ordinary_attempts": len(responses),
        "genuine_interruptions": len(interruptions),
        "barge_in_p95_ms": stop_p95,
        "scripted_completion_fraction": reliability,
        "groups": groups,
        "targets_passed": targets,
        "human_listeners": len(listeners),
        "quality_passed": bool(quality),
        "real_model_turns": data["real_model_turns"],
        "waivers_retired": False,
    }
    (output / "evaluation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "evaluate"])
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output == EVIDENCE or not output.is_relative_to(EVIDENCE):
        parser.error("Use a run directory beneath final phase-09 evidence")
    if args.mode == "prepare":
        prepare(output)
        print("Prepared 63 unperformed scenarios. Live gate pending.")
    else:
        report = evaluate(output)
        print(json.dumps(report))
        raise SystemExit(
            0 if report["live_gate"] == "passed" else 1 if report["live_gate"] == "failed" else 2
        )


if __name__ == "__main__":
    main()
