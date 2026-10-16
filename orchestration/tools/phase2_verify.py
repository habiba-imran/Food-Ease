"""Repeat Phase 2 offline checks and localhost HTTP smoke; preserve old evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import time
from pathlib import Path

import httpx
from phase0_baseline import offline_environment

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "orchestration/evidence/final/phase-02"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=EVIDENCE / "run-1")
    args = parser.parse_args()
    output = args.output.resolve()
    if output == EVIDENCE or not output.is_relative_to(EVIDENCE):
        raise ValueError("Use a run directory beneath phase-02 evidence")
    output.mkdir(parents=True, exist_ok=True)
    env = offline_environment()
    preserved_roots = [
        ROOT / "voice-agent/contract/v1",
        ROOT / "zainab-pack/contract/v1",
        ROOT / "voice-agent/evidence/phase-10",
    ]
    preserved = {
        path: path.read_bytes()
        for tree in preserved_roots
        for path in tree.rglob("*")
        if path.is_file()
    }
    manifest = ROOT / "voice-agent/evidence/phase-9/campaign/manifest.json"
    preserved[manifest] = manifest.read_bytes()
    checks = []
    restored = []

    def python(package: str) -> str:
        return str(ROOT / package / ".venv/Scripts/python.exe")

    def check(label: str, package: str, command: list[str], *, inherited: bool = False) -> None:
        result = subprocess.run(
            command,
            cwd=ROOT / package,
            env=env,
            timeout=300,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        (output / f"{label}.log").write_text(result.stdout, encoding="utf-8")
        checks.append(
            {
                "label": label,
                "command": command,
                "cwd": package,
                "exit_code": result.returncode,
                "inherited_baseline": inherited,
            }
        )
        print(f"{label}: exit {result.returncode}", flush=True)

    try:
        check("website-tests", "website", [python("website"), "-m", "pytest", "-q"])
        check(
            "website-shared-lint",
            "website",
            [python("website"), "-m", "ruff", "check", "src", "tests", "../contracts/src"],
        )
        check(
            "website-shared-types",
            "voice-agent",
            [python("voice-agent"), "-m", "pyright", "--project", "../website"],
        )
        check(
            "contract-tests",
            "voice-agent",
            [
                python("voice-agent"),
                "-m",
                "pytest",
                "-q",
                "tests/test_contract_v1.py",
                "tests/test_contract_v2.py",
            ],
        )
        check(
            "contract-freeze",
            "voice-agent",
            [python("voice-agent"), "tools/freeze_contract_v2.py", "--check"],
        )
        check(
            "contract-lint",
            "voice-agent",
            [
                python("voice-agent"),
                "-m",
                "ruff",
                "check",
                "tools/freeze_contract_v2.py",
                "tests/test_contract_v2.py",
                "src/foodease_agent/contract/v2",
                "../contracts/src",
            ],
        )
        check("javascript-syntax", "website", ["node", "--check", "static/js/app.js"])
        check(
            "javascript-transport",
            "website",
            ["node", "--test", "tests/session_transport.test.cjs"],
        )
        check(
            "orchestration-tests", "orchestration", [python("orchestration"), "-m", "pytest", "-q"]
        )
        check(
            "phase2-tools-lint",
            "orchestration",
            [
                python("orchestration"),
                "-m",
                "ruff",
                "check",
                "tools/phase2_verify.py",
                "tools/phase2_http_smoke.py",
                "tools/phase0_website_smoke.py",
            ],
        )
        check(
            "agent-full-tests",
            "voice-agent",
            [python("voice-agent"), "-m", "pytest", "-q"],
            inherited=True,
        )
        check(
            "agent-full-lint",
            "voice-agent",
            [python("voice-agent"), "-m", "ruff", "check", "."],
            inherited=True,
        )
        check(
            "agent-full-types",
            "voice-agent",
            [python("voice-agent"), "-m", "pyright"],
            inherited=True,
        )

        # Never attach a test to, or stop, an existing user's server.
        try:
            with socket.create_connection(("127.0.0.1", 18080), timeout=0.5):
                raise RuntimeError("Port 18080 is occupied; choose a disposable verification port")
        except OSError:
            pass
        with (output / "localhost-server.log").open("w", encoding="utf-8") as log:
            server = subprocess.Popen(
                [
                    python("website"),
                    "-m",
                    "uvicorn",
                    "foodease_website.app:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "18080",
                    "--no-access-log",
                ],
                cwd=ROOT / "website",
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            try:
                with httpx.Client(trust_env=False, timeout=0.5) as client:
                    for _ in range(100):
                        if server.poll() is not None:
                            raise RuntimeError("Disposable website exited during startup")
                        try:
                            if client.get("http://127.0.0.1:18080/healthz").status_code == 200:
                                break
                        except httpx.TransportError:
                            pass
                        time.sleep(0.1)
                    else:
                        raise RuntimeError("Disposable website startup timed out")
                for label, script in (
                    ("manual-http-smoke", "phase0_website_smoke.py"),
                    ("v2-http-smoke", "phase2_http_smoke.py"),
                ):
                    check(
                        label,
                        "website",
                        [
                            python("website"),
                            str(ROOT / "orchestration/tools" / script),
                            "--output",
                            str(output / f"{label}.json"),
                        ],
                    )
            finally:
                server.terminate()
                server.wait(timeout=10)
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
        changed = [
            name
            for name, digest in expected.items()
            if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest
        ]
        summary = {
            "checks": checks,
            "restored_legacy_test_side_effects": restored,
            "v1_files_checked": len(expected),
            "v1_drift": changed,
            "dotenv_disabled": True,
            "worker_started": False,
            "browser_or_audible_evidence": False,
        }
        (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    failures = [
        row["label"] for row in checks if row["exit_code"] and not row["inherited_baseline"]
    ]
    if failures or changed:
        raise SystemExit(f"Phase 2 failures: {failures}; v1 drift: {changed}")
    print("PASS Phase 2 implementation checks; inherited agent failures remain separately recorded")


if __name__ == "__main__":
    main()
