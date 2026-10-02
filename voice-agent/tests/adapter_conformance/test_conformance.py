"""Adapter conformance suite — parametrized for any AppAdapter implementation."""

from __future__ import annotations

import pytest

from foodease_agent.adapters.mock import MockAdapter, ScenarioConfig, ScenarioMode
from foodease_agent.contract.enums import ActionResultStatus, Operation
from foodease_agent.contract.models import ActionRequestPayload


def _req(action_id: str, operation: Operation, **arguments: object) -> ActionRequestPayload:
    return ActionRequestPayload(action_id=action_id, operation=operation, arguments=arguments)


@pytest.fixture
def adapter() -> MockAdapter:
    return MockAdapter(default_timeout_s=0.05)


@pytest.mark.asyncio
async def test_idempotency(adapter: MockAdapter) -> None:
    a = await adapter.submit_action(
        _req("idemp", Operation.CART_ADD_ITEM, item_id="drink-cola", quantity=1)
    )
    b = await adapter.submit_action(
        _req("idemp", Operation.CART_ADD_ITEM, item_id="drink-cola", quantity=1)
    )
    assert a.model_dump(mode="json") == b.model_dump(mode="json")


@pytest.mark.asyncio
async def test_revision_monotonicity(adapter: MockAdapter) -> None:
    r0 = (await adapter.get_snapshot()).revision
    await adapter.submit_action(
        _req("rev1", Operation.CART_ADD_ITEM, item_id="side-salad", quantity=1)
    )
    r1 = (await adapter.get_snapshot()).revision
    await adapter.submit_action(
        _req("rev2", Operation.CART_SET_QUANTITY, item_id="side-salad", quantity=2)
    )
    r2 = (await adapter.get_snapshot()).revision
    assert r0 < r1 < r2


@pytest.mark.asyncio
async def test_stale_handling(adapter: MockAdapter) -> None:
    adapter.set_scenario(ScenarioConfig(mode=ScenarioMode.STALE_CONTEXT))
    result = await adapter.submit_action(
        _req("stale", Operation.CART_ADD_ITEM, item_id="wrap-veg", quantity=1)
    )
    assert result.status == ActionResultStatus.STALE_CONTEXT
    # No cart mutation on stale
    snap = await adapter.get_snapshot()
    assert snap.cart.lines == []


@pytest.mark.asyncio
async def test_result_correlation(adapter: MockAdapter) -> None:
    result = await adapter.submit_action(
        _req("corr-9", Operation.CART_ADD_ITEM, item_id="roll-paneer", quantity=1)
    )
    assert result.action_id == "corr-9"
    assert result.status == ActionResultStatus.SUCCESS


@pytest.mark.asyncio
async def test_timeout_behavior(adapter: MockAdapter) -> None:
    adapter.set_scenario(ScenarioConfig(mode=ScenarioMode.NEVER_REPLY))
    result = await adapter.submit_action(
        _req("to-1", Operation.CART_ADD_ITEM, item_id="wrap-veg", quantity=1),
        timeout_s=0.05,
    )
    assert result.status == ActionResultStatus.TIMEOUT_UNKNOWN
    assert result.action_id == "to-1"
