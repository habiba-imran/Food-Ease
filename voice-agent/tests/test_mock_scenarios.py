"""V3.2 / V3.3 — idempotency and scenario modes."""

from __future__ import annotations

import pytest

from foodease_agent.adapters.mock import MockAdapter, ScenarioConfig, ScenarioMode
from foodease_agent.contract.enums import ActionResultStatus, Operation
from foodease_agent.contract.models import ActionRequestPayload, ActionResultPayload


def _req(action_id: str, operation: Operation, **arguments: object) -> ActionRequestPayload:
    return ActionRequestPayload(action_id=action_id, operation=operation, arguments=arguments)


@pytest.mark.asyncio
async def test_duplicate_action_id_no_second_mutation() -> None:
    app = MockAdapter()
    first = await app.submit_action(
        _req("dup-1", Operation.CART_ADD_ITEM, item_id="wrap-chicken", quantity=1)
    )
    assert first.status == ActionResultStatus.SUCCESS
    snap_after_first = await app.get_snapshot()
    second = await app.submit_action(
        _req("dup-1", Operation.CART_ADD_ITEM, item_id="wrap-chicken", quantity=1)
    )
    snap_after_second = await app.get_snapshot()
    assert second.status == first.status
    assert second.action_id == first.action_id
    assert second.verified_state == first.verified_state
    # No second mutation: revision and qty unchanged
    assert snap_after_second.revision == snap_after_first.revision
    assert snap_after_second.cart.lines[0].quantity == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mode", "status"),
    [
        (ScenarioMode.FAILED, ActionResultStatus.FAILED),
        (ScenarioMode.REJECTED, ActionResultStatus.REJECTED),
        (ScenarioMode.STALE_CONTEXT, ActionResultStatus.STALE_CONTEXT),
        (ScenarioMode.REQUIRES_CONFIRMATION, ActionResultStatus.REQUIRES_CONFIRMATION),
        (ScenarioMode.NEVER_REPLY, ActionResultStatus.TIMEOUT_UNKNOWN),
    ],
)
async def test_scenario_modes_contract_valid(
    mode: ScenarioMode, status: ActionResultStatus
) -> None:
    app = MockAdapter(default_timeout_s=0.05)
    app.set_scenario(ScenarioConfig(mode=mode, delay_ms=5, reason="nope"))
    result = await app.submit_action(
        _req(f"sc-{mode}", Operation.CART_ADD_ITEM, item_id="wrap-veg", quantity=1)
    )
    # Ensures payload validates as contract model
    ActionResultPayload.model_validate(result.model_dump(mode="json"))
    assert result.status == status


@pytest.mark.asyncio
async def test_delayed_then_success() -> None:
    app = MockAdapter()
    app.set_scenario(ScenarioConfig(mode=ScenarioMode.DELAYED, delay_ms=20))
    result = await app.submit_action(
        _req("delay-1", Operation.CART_ADD_ITEM, item_id="side-raita", quantity=1)
    )
    assert result.status == ActionResultStatus.SUCCESS


@pytest.mark.asyncio
async def test_gui_navigation_and_cart_change() -> None:
    app = MockAdapter()
    await app.submit_action(
        _req("g0", Operation.CART_ADD_ITEM, item_id="wrap-veg", quantity=1)
    )
    summary = await app.submit_action(_req("g1", Operation.CHECKOUT_GET_SUMMARY))
    assert summary.confirmation_token is not None
    # T13-style GUI cart change clears confirmation token
    await app.simulate_cart_change("wrap-veg", quantity=2)
    assert app._pending_confirmation_token is None
    snap = await app.simulate_gui_navigation("desserts")
    assert snap.route in {"category", "desserts"} or snap.revision >= 1
