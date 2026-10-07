"""Pytest hook for joint integration scenarios."""

from __future__ import annotations

import pytest

from foodease_agent.integration.scenarios import run_all


@pytest.mark.asyncio
async def test_integration_suite_all_pass() -> None:
    results = await run_all()
    failed = [f"{r.id}: {r.detail}" for r in results if not r.ok]
    assert not failed, "Integration failures:\n" + "\n".join(failed)
