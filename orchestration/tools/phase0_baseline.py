"""Offline Phase 0 checks; never starts the worker or calls voice providers.

Run from any directory with orchestration/.venv/Scripts/python.exe. Existing
acceptance tests regenerate old evidence; preserve those files byte-for-byte.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import inspect
import json
import os
import re
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "orchestration" / "evidence" / "final" / "phase-00"
PACKAGES = ("voice-agent", "orchestration", "website")


def inventory(with_api: bool) -> None:
    """Report installed versions/signatures without constructing provider clients."""
    result = {
        "python": sys.version,
        "executable": sys.executable,
        "base_executable": getattr(sys, "_base_executable", None),
        "distributions": dict(
            sorted(
                (dist.metadata["Name"], dist.version)
                for dist in importlib.metadata.distributions()
                if dist.metadata["Name"]
            )
        ),
    }
    if with_api:
        from livekit import rtc
        from livekit.agents import Agent, AgentSession, room_io

        objects = {
            "AgentSession.start": AgentSession.start,
            "AgentSession.say": AgentSession.say,
            "AgentSession.interrupt": AgentSession.interrupt,
            "AgentSession.generate_reply": AgentSession.generate_reply,
            "Agent.on_user_turn_completed": Agent.on_user_turn_completed,
            "RoomOptions": room_io.RoomOptions,
            "LocalParticipant.register_rpc_method": rtc.LocalParticipant.register_rpc_method,
            "LocalParticipant.perform_rpc": rtc.LocalParticipant.perform_rpc,
            "LocalParticipant.publish_data": rtc.LocalParticipant.publish_data,
        }
        result["livekit_api"] = {
            name: {
                "signature": str(inspect.signature(obj)),
                "source": inspect.getsourcefile(obj),
                "line": inspect.getsourcelines(obj)[1],
            }
            for name, obj in objects.items()
        }
    print(json.dumps(result, indent=2))


def offline_environment() -> dict[str, str]:
    env = os.environ.copy()
    for key in (
        "LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "DEEPGRAM_API_KEY",
        "CARTESIA_API_KEY", "GROQ_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY",
    ):
        env.pop(key, None)
    env.update(
        PYTHON_DOTENV_DISABLED="1",
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
        HF_HUB_DISABLE_TELEMETRY="1",
        PYTHONIOENCODING="utf-8",
        PYTHONUTF8="1",
        RECORD_AUDIO="false",
        LIVEKIT_AGENT_DISPATCH="false",
        DEV_MODE="false",
    )
    return env


def check_requirement_map() -> dict[str, int]:
    mapping = (EVIDENCE / "requirements-map.md").read_text(encoding="utf-8")
    specifications = {
        "WEB": (ROOT / "Zainab_Web_Application_UI_UX_Requirements_Specification (1).md", 22),
        "W": (ROOT / "Zainab_Web_Application_UI_UX_Requirements_Specification (1).md", 22),
        "VA": (ROOT / "voice-agent/docs/SPEC.md", 17),
        "T": (ROOT / "voice-agent/docs/SPEC.md", 20),
        "O": (ROOT / "orchestration/docs/FINAL_ORCHESTRATION_IMPLEMENTATION_PLAN.md", 21),
    }
    coverage = {}
    for prefix, (source, count) in specifications.items():
        hyphen = "-" if prefix in {"WEB", "VA", "O"} else ""
        expected = {f"{prefix}{hyphen}{number:02d}" for number in range(1, count + 1)}
        pattern = rf"(?<![A-Z0-9-]){prefix}{hyphen}\d{{2}}(?!\d)"
        source_ids = set(re.findall(pattern, source.read_text(encoding="utf-8")))
        rows = re.findall(rf"^\| ({prefix}{hyphen}\d{{2}}) \|", mapping, re.MULTILINE)
        if set(rows) != expected or len(rows) != count or not expected <= source_ids:
            raise ValueError(f"Incomplete or duplicate {prefix} mapping")
        coverage[prefix] = count
    return coverage


def run(output: Path) -> int:
    output = output.resolve()
    if not output.is_relative_to(EVIDENCE.resolve()) or output == EVIDENCE.resolve():
        raise ValueError("Output must be a run directory beneath phase-00 evidence")
    output.mkdir(parents=True, exist_ok=True)
    env = offline_environment()
    preserved_paths = [ROOT / "voice-agent/evidence/phase-9/campaign/manifest.json"]
    preserved_paths.extend((ROOT / "voice-agent/evidence/phase-10").rglob("*"))
    preserved = {path: path.read_bytes() for path in preserved_paths if path.is_file()}
    results = []

    def check(label: str, cwd: Path, command: list[str], *, timeout: int = 300) -> None:
        started = time.monotonic()
        try:
            completed = subprocess.run(
                command, cwd=cwd, env=env, text=True, encoding="utf-8",
                errors="replace", stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                timeout=timeout, check=False,
            )
            code, log = completed.returncode, completed.stdout
        except (OSError, subprocess.TimeoutExpired) as exc:
            code, log = 1, f"{type(exc).__name__}: {exc}\n"
        (output / f"{label}.log").write_text(log, encoding="utf-8")
        results.append({
            "label": label, "cwd": str(cwd.relative_to(ROOT)), "command": command,
            "exit_code": code, "duration_seconds": round(time.monotonic() - started, 3),
        })
        print(f"{label}: {'PASS' if code == 0 else 'FAIL'} (exit {code})", flush=True)

    try:
        for package in PACKAGES:
            cwd = ROOT / package
            python = str(cwd / ".venv/Scripts/python.exe")
            check(f"{package}-inventory", cwd, [
                python, str(Path(__file__).resolve()), "--inventory",
                *(["--livekit-api"] if package == "voice-agent" else []),
            ])
            check(f"{package}-tests", cwd, [python, "-m", "pytest", "-q"])
            targets = ["."] if package == "voice-agent" else ["src", "tests"]
            if package == "orchestration":
                targets.append("tools")
            check(f"{package}-lint", cwd, [python, "-m", "ruff", "check", *targets])
        check("voice-agent-typecheck", ROOT / "voice-agent", [
            str(ROOT / "voice-agent/.venv/Scripts/python.exe"), "-m", "pyright",
        ])
        check("website-js-syntax", ROOT / "website", ["node", "--check", "static/js/app.js"])
        check("node-version", ROOT, ["node", "--version"])
        coverage = check_requirement_map()
        (output / "requirements-coverage.json").write_text(
            json.dumps(coverage, indent=2), encoding="utf-8",
        )
        print(f"requirements-map: PASS ({sum(coverage.values())} rows)", flush=True)
    finally:
        # Do not let baseline tests rewrite the prior handover evidence.
        for path, content in preserved.items():
            if path.read_bytes() != content:
                path.write_bytes(content)

    locks = {
        package: hashlib.sha256((ROOT / package / "uv.lock").read_bytes()).hexdigest()
        for package in PACKAGES
    }
    summary = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "mode": "offline-components-only",
        "dotenv_disabled": True,
        "worker_started": False,
        "lock_sha256": locks,
        "preserved_handover_files": len(preserved),
        "requirements_coverage": coverage,
        "checks": results,
        "failed_checks": [r["label"] for r in results if r["exit_code"]],
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return int(bool(summary["failed_checks"]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", action="store_true")
    parser.add_argument("--livekit-api", action="store_true")
    parser.add_argument("--output", type=Path, default=EVIDENCE / "run-1")
    args = parser.parse_args()
    if args.inventory:
        inventory(args.livekit_api)
    else:
        raise SystemExit(run(args.output))


if __name__ == "__main__":
    main()
