"""Refuse committed secrets under orchestration/ (demo hygiene)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERN = re.compile(
    r"(api[_-]?key|api[_-]?secret|livekit_api_secret)\s*[=:]\s*['\"]?[A-Za-z0-9_\-]{16,}",
    re.I,
)
SKIP = {".venv", ".git", "__pycache__", ".pytest_cache", ".ruff_cache"}


def main() -> None:
    hits: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP for part in path.parts):
            continue
        if path.name in {".env"}:
            continue
        if path.suffix not in {".py", ".md", ".toml", ".txt", ".json", ".example", ".js"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if PATTERN.search(line) and "APIxxxxxxxx" not in line and "secretxxxxxxxx" not in line:
                # allow obvious placeholders
                if "your-" in line.lower() or "placeholder" in line.lower():
                    continue
                if "APItestkey" in line or "secretsecretsecret" in line:
                    # test fixtures OK
                    continue
                hits.append(f"{path.relative_to(ROOT)}:{i}: {line.strip()[:80]}")
    if hits:
        print("secret_scan FAILED:")
        for h in hits:
            print(h)
        raise SystemExit(1)
    print("secret_scan OK")


if __name__ == "__main__":
    main()
