"""Phase 11.5 — secret / recording scan of the **git release tree** (no network).

Local ignored files (`.env`, `*.wav` under gitignore) are reported as INFO only.
Tracked secrets or recordings fail the scan (R6 / R13).
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("aws_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("private_key_block", re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----")),
    ("generic_bearer", re.compile(r"(?i)authorization:\s*bearer\s+[a-z0-9\-._~+/]+=*")),
]

FORBIDDEN_SUFFIXES = {".wav", ".mp3", ".m4a", ".ogg", ".webm"}
TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".json",
    ".jsonl",
    ".txt",
    ".toml",
    ".yml",
    ".yaml",
    ".js",
    ".html",
    ".csv",
    ".example",
}


def tracked_files() -> list[Path]:
    try:
        out = subprocess.check_output(
            ["git", "ls-files", "-z"],
            cwd=str(ROOT),
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback: walk without .venv
        return [
            p
            for p in ROOT.rglob("*")
            if p.is_file() and ".venv" not in p.parts and ".git" not in p.parts
        ]
    rels = [r for r in out.decode("utf-8", errors="replace").split("\0") if r]
    return [ROOT / r for r in rels]


def scan_tracked() -> list[str]:
    findings: list[str] = []
    for path in tracked_files():
        rel = path.relative_to(ROOT).as_posix()
        if path.name == ".env":
            findings.append(f"tracked_env:{rel}")
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            findings.append(f"tracked_recording:{rel}")
        if path.suffix.lower() in TEXT_SUFFIXES or path.name == ".env.example":
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if path.name == ".env.example":
                continue
            for label, pat in SECRET_PATTERNS:
                if pat.search(text):
                    findings.append(f"{label}:{rel}")
    return findings


def gitleaks_note() -> str:
    try:
        subprocess.check_call(
            ["gitleaks", "detect", "--source", str(ROOT), "--no-git", "-v"],
            cwd=str(ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return "gitleaks: clean"
    except FileNotFoundError:
        return "gitleaks: not installed (pre-commit hook still applies on commit)"
    except subprocess.CalledProcessError as exc:
        return f"gitleaks: FAIL exit={exc.returncode}"


def main() -> None:
    print(gitleaks_note())
    local_env = ROOT / ".env"
    if local_env.is_file():
        print("INFO: local .env present (gitignored) — OK if not committed")
    findings = scan_tracked()
    if findings:
        print("FINDINGS (tracked tree):")
        for f in findings:
            print(" ", f)
        raise SystemExit(1)
    print("SECRET_SCAN PASS (tracked tree clean)")


if __name__ == "__main__":
    main()
