"""Smoke-import demo_up helpers (no live server required)."""

from __future__ import annotations

import importlib.util
import io
from contextlib import redirect_stdout
from pathlib import Path


def _load_demo_up():
    path = Path(__file__).resolve().parents[1] / "tools" / "demo_up.py"
    spec = importlib.util.spec_from_file_location("demo_up", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_print_stack_mentions_ownership() -> None:
    demo_up = _load_demo_up()
    buf = io.StringIO()
    with redirect_stdout(buf):
        demo_up.print_stack(session_api="http://127.0.0.1:8090", room="foodease-demo")
    text = buf.getvalue()
    assert "OWNERSHIP.md" in text
    assert "foodease-session" in text
    assert "Session API" in text
