"""Committed-turn gate for mutating tools (Phase 5.7 / V5.7)."""

from __future__ import annotations

from dataclasses import dataclass, field

from foodease_agent.contract.enums import Operation

# Mutations / navigation that must never run on a discarded / uncommitted speculative turn.
MUTATING_OPS: frozenset[Operation] = frozenset(
    {
        Operation.CART_ADD_ITEM,
        Operation.CART_SET_QUANTITY,
        Operation.CART_REMOVE_ITEM,
        Operation.CHECKOUT_SUBMIT_DEMO_ORDER,
        Operation.UNDO_LAST_REVERSIBLE_ACTION,
        Operation.NAVIGATE,
        Operation.SEARCH_MENU,
        Operation.FILTER_MENU,
        Operation.SELECT_ITEM,
    }
)


@dataclass
class TurnCommitGate:
    """Tracks whether the current user turn is committed.

    LiveKit may start LLM generation before end-of-turn is confirmed
    (preemptive generation). Mutating AppAdapter calls are rejected unless
    ``committed`` is True.
    """

    committed: bool = False
    discarded_generation_blocks: int = 0
    mutation_attempts_while_uncommitted: list[str] = field(default_factory=list)

    def mark_committed(self) -> None:
        self.committed = True

    def mark_uncommitted(self) -> None:
        self.committed = False

    def on_generation_discarded(self) -> None:
        self.discarded_generation_blocks += 1
        self.committed = False

    def allow(self, operation: Operation) -> bool:
        """Return True if this operation may execute now."""
        if operation in {
            Operation.GET_ITEM_DETAILS,
            Operation.GET_CART,
            Operation.GET_CURRENT_CONTEXT,
            Operation.CHECKOUT_GET_SUMMARY,
        }:
            return True
        if not self.committed:
            self.mutation_attempts_while_uncommitted.append(operation.value)
            return False
        return True

    def require(self, operation: Operation) -> None:
        if not self.allow(operation):
            raise TurnNotCommittedError(
                f"Refused {operation.value}: user turn not committed "
                "(speculative / discarded generation safety)"
            )


class TurnNotCommittedError(RuntimeError):
    """Raised when a mutating tool runs before the turn is committed."""
