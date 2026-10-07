"""Consent / room policy unit tests."""

from __future__ import annotations

import pytest

from foodease_session.policy import PolicyError, normalize_room, resolve_identity


def test_normalize_generates_prefixed_room() -> None:
    name = normalize_room(None)
    assert name.startswith("foodease-")
    assert normalize_room("foodease-demo") == "foodease-demo"


def test_normalize_rejects_bad_room() -> None:
    with pytest.raises(PolicyError):
        normalize_room("../evil")
    with pytest.raises(PolicyError):
        normalize_room("other-room")
    # Empty / whitespace → generate (same as null), not reject
    assert normalize_room("").startswith("foodease-")
    assert normalize_room("   ").startswith("foodease-")


def test_resolve_identity() -> None:
    assert resolve_identity("mock-app", prefix="app") == "mock-app"
    generated = resolve_identity(None, prefix="user")
    assert generated.startswith("user-")
