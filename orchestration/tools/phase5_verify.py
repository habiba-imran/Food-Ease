"""Final Phase 5 offline checks, with frozen contract/historical evidence preservation."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from phase0_baseline import offline_environment

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "orchestration/evidence/final/phase-05"
SCOPED = [
    "src/foodease_agent/integrated",
    "src/foodease_agent/adapters/integrated.py",
    "src/foodease_agent/adapters/integrated_startup.py",
    "src/foodease_agent/worker.py",
    "tests/test_integrated_runtime.py",
    "tests/test_integrated_rpc_worker.py",
    "tests/test_integrated_output.py",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=EVIDENCE / "run-1")
    args = parser.parse_args()
    output = args.output.resolve()
    if output == EVIDENCE or not output.is_relative_to(EVIDENCE):
        raise ValueError("Use a run directory beneath Phase 5 evidence")
    output.mkdir(parents=True, exist_ok=True)
    env = offline_environment()
    trees = [
        ROOT / "voice-agent/contract/v1",
        ROOT / "zainab-pack/contract/v1",
        ROOT / "voice-agent/evidence/phase-10",
    ]
    preserved = {
        path: path.read_bytes() for tree in trees for path in tree.rglob("*") if path.is_file()
    }
    manifest = ROOT / "voice-agent/evidence/phase-9/campaign/manifest.json"
    preserved[manifest] = manifest.read_bytes()
    checks, restored = [], []

    def python(package):
        return str(ROOT / package / ".venv/Scripts/python.exe")

    def check(name, package, command, baseline=None):
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
        known = False
        if baseline == "tests":
            failures = re.findall(r"^FAILED ([^\s]+)", result.stdout, re.MULTILINE)
            known = failures == [
                "tests/test_no_mock_leak.py::test_no_mock_imports_outside_adapters"
            ]
        elif baseline == "lint":
            known = "Found 39 errors." in result.stdout
        elif baseline == "types":
            known = "27 errors, 2 warnings" in result.stdout
        checks.append(
            {
                "name": name,
                "command": command,
                "cwd": package,
                "exit_code": result.returncode,
                "matched_inherited_baseline": known,
            }
        )
        print(f"{name}: exit {result.returncode}; inherited baseline={known}", flush=True)

    try:
        agent = python("voice-agent")
        check(
            "installed-sdk",
            "voice-agent",
            [agent, "../orchestration/tools/phase0_baseline.py", "--inventory", "--livekit-api"],
        )
        check(
            "worker-runtime-tests",
            "voice-agent",
            [
                agent,
                "-m",
                "pytest",
                "-q",
                "tests/test_integrated_runtime.py",
                "tests/test_integrated_rpc_worker.py",
                "tests/test_integrated_startup.py",
                "tests/test_livekit_room.py",
                "tests/test_integrated_output.py",
            ],
        )
        check("worker-runtime-lint", "voice-agent", [agent, "-m", "ruff", "check", *SCOPED])
        check("worker-runtime-types", "voice-agent", [agent, "-m", "pyright", *SCOPED])
        check("frozen-contract", "voice-agent", [agent, "tools/freeze_contract_v2.py", "--check"])
        for package in ("website", "orchestration"):
            check(f"{package}-tests", package, [python(package), "-m", "pytest", "-q"])
            check(
                f"{package}-lint", package, [python(package), "-m", "ruff", "check", "src", "tests"]
            )
        check("orchestration-types", "orchestration", [python("orchestration"), "-m", "pyright"])
        check(
            "website-shared-types",
            "voice-agent",
            [agent, "-m", "pyright", "--project", "../website"],
        )
        check("agent-full-tests", "voice-agent", [agent, "-m", "pytest", "-q"], "tests")
        check("agent-full-lint", "voice-agent", [agent, "-m", "ruff", "check", "."], "lint")
        check("agent-full-types", "voice-agent", [agent, "-m", "pyright"], "types")
        check(
            "javascript-tests",
            "website",
            [
                "node",
                "--test",
                "tests/*.test.cjs",
                "tests/*.test.mjs",
            ],
        )
        check("browser-bundle-build", "website", ["node", "tools/build-browser.mjs"])
        check("browser-integration", "website", ["node", "tools/browser-test.mjs"])
        check(
            "browser-fixture-types",
            "voice-agent",
            [agent, "-m", "pyright", "../website/tests/browser_server.py"],
        )
        check(
            "verifier-lint",
            "orchestration",
            [python("orchestration"), "-m", "ruff", "check", "tools/phase5_verify.py"],
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
        failures = [
            row["name"]
            for row in checks
            if row["exit_code"] and not row["matched_inherited_baseline"]
        ]
        summary = {
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "checks": checks,
            "unexpected_failures": failures,
            "v1_files_checked": len(expected),
            "v1_drift": drift,
            "restored_legacy_test_side_effects": restored,
            "dotenv_disabled": True,
            "providers": "local fakes only",
            "website_authority": "real SessionStore and domain",
            "livekit_cloud": False,
            "microphone_or_audible_evidence": False,
            "browser": "real Chromium with fake RTC/lifecycle and local fake streaming LLM",
            "browser_bundle_sha256": hashlib.sha256(
                (ROOT / "website/static/vendor/livekit-client.2.15.4.mjs").read_bytes()
            ).hexdigest(),
        }
        (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if failures or drift:
        raise SystemExit(f"Phase 5 failures: {failures}; v1 drift: {drift}")
    print("PASS scoped Phase 5 checks; inherited agent failures remain recorded")


if __name__ == "__main__":
    main()
