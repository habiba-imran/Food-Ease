"""VA-07 product conversation/audio state machine + transition log."""

from __future__ import annotations

from dataclasses import dataclass, field

from foodease_agent.contract.enums import ProductState

# LiveKit AgentSession agent_state strings → product states
_LK_TO_PRODUCT: dict[str, ProductState] = {
    "initializing": ProductState.CONNECTING,
    "idle": ProductState.IDLE,
    "listening": ProductState.READY_LISTENING,
    "thinking": ProductState.THINKING,
    "speaking": ProductState.ASSISTANT_SPEAKING,
}


def map_livekit_agent_state(lk_state: str) -> ProductState:
    return _LK_TO_PRODUCT.get(lk_state, ProductState.READY_LISTENING)


def fatal_error_state() -> ProductState:
    """Fatal provider error must never leave ready/listening."""
    return ProductState.ERROR


# Allowed transitions (permissive but explicit for logging / V7.2)
_ALLOWED: dict[ProductState, frozenset[ProductState]] = {
    ProductState.OFF_AWAITING_CONSENT: frozenset(
        {ProductState.CONNECTING, ProductState.ENDED}
    ),
    ProductState.CONNECTING: frozenset(
        {
            ProductState.READY_LISTENING,
            ProductState.ERROR,
            ProductState.RECONNECTING,
            ProductState.ENDED,
        }
    ),
    ProductState.READY_LISTENING: frozenset(
        {
            ProductState.USER_SPEAKING,
            ProductState.THINKING,
            ProductState.ASSISTANT_SPEAKING,
            ProductState.IDLE,
            ProductState.MUTED_PAUSED,
            ProductState.WAITING_FOR_ACTION_RESULT,
            ProductState.RECONNECTING,
            ProductState.ERROR,
            ProductState.ENDED,
            ProductState.READY_LISTENING,
        }
    ),
    ProductState.USER_SPEAKING: frozenset(
        {
            ProductState.THINKING,
            ProductState.READY_LISTENING,
            ProductState.ASSISTANT_SPEAKING,
            ProductState.ERROR,
            ProductState.ENDED,
        }
    ),
    ProductState.THINKING: frozenset(
        {
            ProductState.ASSISTANT_SPEAKING,
            ProductState.WAITING_FOR_ACTION_RESULT,
            ProductState.READY_LISTENING,
            ProductState.ERROR,
            ProductState.ENDED,
        }
    ),
    ProductState.ASSISTANT_SPEAKING: frozenset(
        {
            ProductState.READY_LISTENING,
            ProductState.USER_SPEAKING,
            ProductState.IDLE,
            ProductState.WAITING_FOR_ACTION_RESULT,
            ProductState.THINKING,
            ProductState.MUTED_PAUSED,
            ProductState.ERROR,
            ProductState.ENDED,
        }
    ),
    ProductState.WAITING_FOR_ACTION_RESULT: frozenset(
        {
            ProductState.ASSISTANT_SPEAKING,
            ProductState.READY_LISTENING,
            ProductState.THINKING,
            ProductState.ERROR,
            ProductState.ENDED,
        }
    ),
    ProductState.IDLE: frozenset(
        {
            ProductState.READY_LISTENING,
            ProductState.USER_SPEAKING,
            ProductState.ASSISTANT_SPEAKING,
            ProductState.MUTED_PAUSED,
            ProductState.ENDED,
            ProductState.ERROR,
        }
    ),
    ProductState.MUTED_PAUSED: frozenset(
        {
            ProductState.READY_LISTENING,
            ProductState.IDLE,
            ProductState.ENDED,
            ProductState.ERROR,
        }
    ),
    ProductState.RECONNECTING: frozenset(
        {
            ProductState.READY_LISTENING,
            ProductState.CONNECTING,
            ProductState.ERROR,
            ProductState.ENDED,
        }
    ),
    ProductState.ERROR: frozenset(
        {ProductState.ENDED, ProductState.CONNECTING, ProductState.OFF_AWAITING_CONSENT}
    ),
    ProductState.ENDED: frozenset(),
}


@dataclass
class StateTransition:
    frm: ProductState
    to: ProductState
    reason: str


@dataclass
class ProductStateMachine:
    state: ProductState = ProductState.OFF_AWAITING_CONSENT
    log: list[StateTransition] = field(default_factory=list)

    def transition(self, new: ProductState, *, reason: str = "") -> ProductState:
        if new == self.state:
            return self.state
        allowed = _ALLOWED.get(self.state, frozenset())
        # Fatal error always allowed from non-ended states
        if new == ProductState.ERROR and self.state != ProductState.ENDED:
            self.log.append(StateTransition(self.state, new, reason or "fatal"))
            self.state = new
            return self.state
        if new not in allowed and self.state != ProductState.ENDED:
            # Still record forced transition for observability (dev)
            reason = f"{reason}|forced_from_{self.state.value}"
        self.log.append(StateTransition(self.state, new, reason))
        self.state = new
        return self.state

    def apply_livekit(self, lk_state: str, *, reason: str = "livekit") -> ProductState:
        if self.state == ProductState.ERROR:
            return self.state
        return self.transition(map_livekit_agent_state(lk_state), reason=reason)

    def mark_fatal(self, reason: str = "provider_fatal") -> ProductState:
        return self.transition(fatal_error_state(), reason=reason)

    def covered_states(self) -> set[ProductState]:
        seen = {self.state}
        for t in self.log:
            seen.add(t.frm)
            seen.add(t.to)
        return seen
