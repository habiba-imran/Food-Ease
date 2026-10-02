"""V3.1 — cart totals, quantity edits, remove, fees, rounding."""

from __future__ import annotations

import pytest

from foodease_agent.adapters.mock import MockAdapter
from foodease_agent.contract.enums import ActionResultStatus, Operation
from foodease_agent.contract.models import ActionRequestPayload


def _req(action_id: str, operation: Operation, **arguments: object) -> ActionRequestPayload:
    return ActionRequestPayload(
        action_id=action_id,
        operation=operation,
        arguments=arguments,
    )


@pytest.mark.asyncio
async def test_add_set_remove_fees_and_rounding() -> None:
    app = MockAdapter()
    # 150 + 1500 + service 50
    r1 = await app.submit_action(
        _req("a1", Operation.CART_ADD_ITEM, item_id="drink-lassi-small", quantity=1)
    )
    assert r1.status == ActionResultStatus.SUCCESS
    r2 = await app.submit_action(
        _req("a2", Operation.CART_ADD_ITEM, item_id="platter-family", quantity=1)
    )
    assert r2.status == ActionResultStatus.SUCCESS
    assert r2.verified_state is not None
    assert r2.verified_state["subtotal"] == 1650.0
    assert r2.verified_state["total"] == 1700.0

    r3 = await app.submit_action(
        _req("a3", Operation.CART_SET_QUANTITY, item_id="drink-lassi-small", quantity=2)
    )
    assert r3.verified_state is not None
    assert r3.verified_state["subtotal"] == 1800.0
    assert r3.verified_state["total"] == 1850.0

    r4 = await app.submit_action(
        _req("a4", Operation.CART_REMOVE_ITEM, item_id="platter-family")
    )
    assert r4.verified_state is not None
    assert r4.verified_state["subtotal"] == 300.0
    assert r4.verified_state["total"] == 350.0

    # empty cart => no fee
    await app.submit_action(_req("a5", Operation.CART_REMOVE_ITEM, item_id="drink-lassi-small"))
    cart = await app.submit_action(_req("a6", Operation.GET_CART))
    assert cart.verified_state is not None
    assert cart.verified_state["total"] == 0.0
    assert cart.verified_state["fees"] == []


@pytest.mark.asyncio
async def test_out_of_stock_rejected() -> None:
    app = MockAdapter()
    result = await app.submit_action(
        _req("oos", Operation.CART_ADD_ITEM, item_id="burger-soldout", quantity=1)
    )
    assert result.status == ActionResultStatus.REJECTED


@pytest.mark.asyncio
async def test_missing_ingredients_flag() -> None:
    app = MockAdapter()
    result = await app.submit_action(
        _req("ing", Operation.GET_ITEM_DETAILS, item_id="dessert-mystery")
    )
    assert result.status == ActionResultStatus.SUCCESS
    assert result.verified_state is not None
    assert result.verified_state["ingredients_available"] is False
    assert result.verified_state["ingredients"] is None


@pytest.mark.asyncio
async def test_revision_monotonic_on_mutation() -> None:
    app = MockAdapter()
    s0 = await app.get_snapshot()
    await app.submit_action(
        _req("m1", Operation.CART_ADD_ITEM, item_id="wrap-veg", quantity=1)
    )
    s1 = await app.get_snapshot()
    assert s1.revision > s0.revision
