"""Reconnect + pending-mutation discipline (VA-14 / Phase 8.4)."""

from __future__ import annotations

from dataclasses import dataclass, field

from foodease_agent.adapters.base import AppAdapter
from foodease_agent.confirmation import ConfirmationMachine
from foodease_agent.contract.enums import ActionResultStatus, Operation
from foodease_agent.contract.models import ActionRequestPayload, ActionResultPayload, ContextSnapshot
from foodease_agent.tiers import RiskTier, tier_for


@dataclass
class PendingMutation:
    action_id: str
    operation: Operation
    outcome_known: bool = False


@dataclass
class ReconnectManager:
    """On reconnect: fresh snapshot, reset confirmation, never resend unknown mutations."""

    pending: dict[str, PendingMutation] = field(default_factory=dict)
    unknown_action_ids: set[str] = field(default_factory=set)

    def register_mutation(self, action_id: str, operation: Operation) -> None:
        if tier_for(operation) == RiskTier.READ:
            return
        self.pending[action_id] = PendingMutation(action_id=action_id, operation=operation)

    def resolve(self, result: ActionResultPayload) -> None:
        pend = self.pending.get(result.action_id)
        if pend is None:
            return
        if result.status == ActionResultStatus.TIMEOUT_UNKNOWN:
            self.unknown_action_ids.add(result.action_id)
            pend.outcome_known = False
        else:
            pend.outcome_known = True
            self.unknown_action_ids.discard(result.action_id)

    def may_resend(self, action_id: str) -> bool:
        """Never resend a mutating action whose outcome is unknown (R4)."""
        if action_id in self.unknown_action_ids:
            return False
        pend = self.pending.get(action_id)
        if pend is None:
            return True
        return pend.outcome_known

    async def on_reconnect(
        self,
        adapter: AppAdapter,
        confirmation: ConfirmationMachine,
    ) -> ContextSnapshot:
        confirmation.invalidate()
        # Do not resend any pending unknown mutations
        snap = await adapter.get_snapshot()
        confirmation.on_cart_or_revision_change(snap.revision)
        return snap


def guard_resubmit(
    mgr: ReconnectManager,
    request: ActionRequestPayload,
) -> ActionResultPayload | None:
    """Return a synthetic reject if this would illegally resend an unknown mutation."""
    if not mgr.may_resend(request.action_id):
        return ActionResultPayload(
            action_id=request.action_id,
            status=ActionResultStatus.REJECTED,
            error_message="I won’t resend that until we know what happened. Checking the cart first.",
        )
    return None
