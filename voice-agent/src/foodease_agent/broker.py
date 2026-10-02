"""ActionBroker — validate, stamp, submit, never blind-retry mutations."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from foodease_agent.adapters.base import AppAdapter
from foodease_agent.contract.enums import ActionResultStatus, Operation
from foodease_agent.contract.models import (
    ARGS_BY_OPERATION,
    ActionRequestPayload,
    ActionResultPayload,
    ContextSnapshot,
)
from foodease_agent.tiers import RiskTier, allows_read_retry, tier_for


@dataclass
class BrokerOutcome:
    result: ActionResultPayload
    speak_guidance: str
    snapshot: ContextSnapshot


class ActionBroker:
    def __init__(self, adapter: AppAdapter) -> None:
        self._adapter = adapter

    @staticmethod
    def new_action_id() -> str:
        return f"action-{uuid.uuid4().hex[:12]}"

    async def run(
        self,
        *,
        operation: Operation,
        arguments: dict[str, Any],
        snapshot: ContextSnapshot,
        action_id: str | None = None,
        timeout_s: float | None = None,
        allow_read_retry: bool = True,
    ) -> BrokerOutcome:
        # Validate allowlist + schema
        model = ARGS_BY_OPERATION[operation]
        parsed = model.model_validate(arguments)
        args = parsed.model_dump(mode="json", exclude_none=True)

        # Item IDs must exist in snapshot or cart when present
        item_id = args.get("item_id")
        if item_id is not None:
            known = {v.item_id for v in snapshot.visible_items} | {
                line.item_id for line in snapshot.cart.lines
            }
            # Also allow known catalog via get after refresh for consequential ops
            if item_id not in known and tier_for(operation) != RiskTier.READ:
                # Refresh once then re-check
                snapshot = await self._adapter.get_snapshot()
                known = {v.item_id for v in snapshot.visible_items} | {
                    line.item_id for line in snapshot.cart.lines
                }
                # Mock catalog items may not all be visible — allow if operation is cart on known pattern
                # Consequential: reject if still not in cart for set/remove
                if operation in {Operation.CART_SET_QUANTITY, Operation.CART_REMOVE_ITEM}:
                    if item_id not in {line.item_id for line in snapshot.cart.lines}:
                        return BrokerOutcome(
                            result=ActionResultPayload(
                                action_id=action_id or self.new_action_id(),
                                status=ActionResultStatus.REJECTED,
                                error_message="That item is not in the cart.",
                            ),
                            speak_guidance="clarify: item not in cart",
                            snapshot=snapshot,
                        )

        aid = action_id or self.new_action_id()
        # Refresh stale snapshot before consequential actions
        if tier_for(operation) != RiskTier.READ:
            fresh = await self._adapter.get_snapshot()
            if fresh.revision < snapshot.revision:
                # Should not go backwards; still use fresh
                snapshot = fresh
            elif fresh.revision != snapshot.revision:
                snapshot = fresh

        request = ActionRequestPayload(
            action_id=aid,
            operation=operation,
            arguments=args,
        )
        result = await self._adapter.submit_action(request, timeout_s=timeout_s)

        # One read-only retry allowed
        if (
            allow_read_retry
            and allows_read_retry(operation)
            and result.status
            in {ActionResultStatus.FAILED, ActionResultStatus.TIMEOUT_UNKNOWN}
        ):
            retry_id = self.new_action_id()
            retry_req = ActionRequestPayload(
                action_id=retry_id, operation=operation, arguments=args
            )
            result = await self._adapter.submit_action(retry_req, timeout_s=timeout_s)

        # Never auto-retry mutations (even on timeout_unknown)
        snap = await self._adapter.get_snapshot()
        guidance = self._speak_guidance(operation, result)
        return BrokerOutcome(result=result, speak_guidance=guidance, snapshot=snap)

    def _speak_guidance(self, operation: Operation, result: ActionResultPayload) -> str:
        if result.status == ActionResultStatus.SUCCESS:
            state = result.verified_state or {}
            if operation in {
                Operation.CART_ADD_ITEM,
                Operation.CART_SET_QUANTITY,
                Operation.CART_REMOVE_ITEM,
                Operation.GET_CART,
                Operation.UNDO_LAST_REVERSIBLE_ACTION,
            }:
                total = state.get("total")
                lines = state.get("cart") or []
                if lines:
                    last = lines[-1]
                    return (
                        f"verified: cart has {last.get('quantity')} "
                        f"{last.get('name')}, total {total} PKR"
                    )
                return "verified: cart is empty"
            if operation == Operation.CHECKOUT_SUBMIT_DEMO_ORDER:
                return "verified: demo order placed"
            if operation == Operation.CHECKOUT_GET_SUMMARY:
                total = (result.verified_state or {}).get("total")
                return f"verified: checkout summary total {total} PKR"
            return f"verified: {operation.value} succeeded"
        if result.status == ActionResultStatus.TIMEOUT_UNKNOWN:
            return "unknown: refresh cart then ask the user; do not retry the mutation"
        if result.status == ActionResultStatus.STALE_CONTEXT:
            return "stale: refresh context before acting"
        if result.status == ActionResultStatus.REQUIRES_CONFIRMATION:
            return "needs confirmation of the current summary"
        return f"not verified: {result.status.value} — {result.error_message or 'failed'}"
