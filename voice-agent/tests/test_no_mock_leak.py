"""V3.5 — nothing outside adapters/ imports the mock module."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "foodease_agent"


def test_no_mock_imports_outside_adapters() -> None:
    offenders: list[str] = []
    for path in SRC.rglob("*.py"):
        if "adapters" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod == "foodease_agent.adapters.mock" or mod.endswith(".adapters.mock"):
                    offenders.append(str(path.relative_to(ROOT)))
                if mod == "foodease_agent.adapters" and any(
                    alias.name == "mock" for alias in node.names
                ):
                    offenders.append(str(path.relative_to(ROOT)))
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.endswith("adapters.mock"):
                        offenders.append(str(path.relative_to(ROOT)))
    assert offenders == [], f"mock imported outside adapters/: {offenders}"
