"""Dev session wiring — MockAdapter stays inside adapters/ (V3.5)."""

from __future__ import annotations

from foodease_agent.adapters.base import AppAdapter
from foodease_agent.adapters.mock import MockAdapter


def create_dev_adapter() -> AppAdapter:
    """In-process mock for the voice worker until LiveKitRpcAdapter (Phase 7)."""
    return MockAdapter()
