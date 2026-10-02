"""Map LiveKit agent states → product VA-07 states (partial Phase 5; full in Phase 7)."""

from __future__ import annotations

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
