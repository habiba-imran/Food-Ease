"""Final Phase 3 offline implementation checks. No Cloud, keys or microphone."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from phase0_baseline import offline_environment

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "orchestration/evidence/final/phase-03"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=EVIDENCE / "run-1")
    args = parser.parse_args()
    output = args.output.resolve()
    if output == EVIDENCE or not output.is_relative_to(EVIDENCE):
        raise ValueError("Use a run directory beneath Phase 3 evidence")
    output.mkdir(parents=True, exist_ok=True)
    env = offline_environment()
    roots = [
        ROOT / "voice-agent/contract/v1",
        ROOT / "zainab-pack/contract/v1",
        ROOT / "voice-agent/evidence/phase-10",
    ]
    preserved = {
        path: path.read_bytes() for tree in roots for path in tree.rglob("*") if path.is_file()
    }
    manifest = ROOT / "voice-agent/evidence/phase-9/campaign/manifest.json"
    preserved[manifest] = manifest.read_bytes()
    checks, restored = [], []

    def python(package):
        return str(ROOT / package / ".venv/Scripts/python.exe")

    def check(name, package, command, inherited=False):
        result = subprocess.run(
            command,
            cwd=ROOT / package,
            env=env,
            timeout=300,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        (output / f"{name}.log").write_text(result.stdout, encoding="utf-8")
        checks.append(
            {
                "name": name,
                "command": command,
                "cwd": package,
                "exit_code": result.returncode,
                "inherited_baseline": inherited,
            }
        )
        print(f"{name}: exit {result.returncode}", flush=True)

    try:
        for package in ("orchestration", "website"):
            check(f"{package}-tests", package, [python(package), "-m", "pytest", "-q"])
            check(
                f"{package}-lint", package, [python(package), "-m", "ruff", "check", "src", "tests"]
            )
        check("orchestration-types", "orchestration", [python("orchestration"), "-m", "pyright"])
        check(
            "website-shared-types",
            "voice-agent",
            [python("voice-agent"), "-m", "pyright", "--project", "../website"],
        )
        check(
            "worker-startup-tests",
            "voice-agent",
            [
                python("voice-agent"),
                "-m",
                "pytest",
                "-q",
                "tests/test_integrated_startup.py",
                "tests/test_livekit_room.py",
            ],
        )
        check(
            "worker-startup-lint",
            "voice-agent",
            [
                python("voice-agent"),
                "-m",
                "ruff",
                "check",
                "src/foodease_agent/worker.py",
                "src/foodease_agent/adapters/integrated_startup.py",
                "src/foodease_agent/adapters/dev_wiring.py",
                "src/foodease_agent/adapters/livekit_room.py",
                "tests/test_integrated_startup.py",
                "../contracts/src",
            ],
        )
        check(
            "worker-startup-types",
            "voice-agent",
            [
                python("voice-agent"),
                "-m",
                "pyright",
                "src/foodease_agent/worker.py",
                "src/foodease_agent/adapters/integrated_startup.py",
                "src/foodease_agent/adapters/dev_wiring.py",
                "tests/test_integrated_startup.py",
                "../contracts/src/foodease_contract/startup.py",
            ],
        )
        check(
            "frozen-contract",
            "voice-agent",
            [python("voice-agent"), "tools/freeze_contract_v2.py", "--check"],
        )
        check(
            "agent-full-tests", "voice-agent", [python("voice-agent"), "-m", "pytest", "-q"], True
        )
        check(
            "agent-full-lint",
            "voice-agent",
            [python("voice-agent"), "-m", "ruff", "check", "."],
            True,
        )
        check("agent-full-types", "voice-agent", [python("voice-agent"), "-m", "pyright"], True)
        check(
            "javascript-tests",
            "website",
            [
                "node",
                "--test",
                "tests/session_transport.test.cjs",
                "tests/assistance-controller.test.mjs",
            ],
        )
        check(
            "javascript-syntax",
            "website",
            ["node", "--check", "static/js/assistance-controller.mjs"],
        )
        check(
            "phase3-tools-lint",
            "orchestration",
            [
                python("orchestration"),
                "-m",
                "ruff",
                "check",
                "tools/phase3_verify.py",
                "tools/phase3_http_smoke.py",
                "tools/demo_up.py",
            ],
        )
        check(
            "two-http-services",
            "orchestration",
            [
                python("orchestration"),
                "tools/phase3_http_smoke.py",
                "--output",
                str(output / "http-smoke.json"),
            ],
        )
    finally:
        for path, content in preserved.items():
            if not path.exists() or path.read_bytes() != content:
                restored.append(str(path.relative_to(ROOT)))
                path.write_bytes(content)
        expected = json.loads(
            (ROOT / "orchestration/evidence/final/phase-01/preservation.json").read_text(
                encoding="utf-8"
            )
        )["legacy_v1_sha256"]
        drift = [
            name
            for name, digest in expected.items()
            if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest
        ]
        summary = {
            "checks": checks,
            "v1_files_checked": len(expected),
            "v1_drift": drift,
            "restored_legacy_test_side_effects": restored,
            "dotenv_disabled": True,
            "livekit_dispatch": "fake only",
            "microphone_or_audible_evidence": False,
        }
        (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    failures = [row["name"] for row in checks if row["exit_code"] and not row["inherited_baseline"]]
    if failures or drift:
        raise SystemExit(f"Phase 3 failures: {failures}; v1 drift: {drift}")
    print("PASS scoped Phase 3 checks; review inherited agent failures separately")


if __name__ == "__main__":
    main()
