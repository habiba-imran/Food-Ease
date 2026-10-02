"""FoodEase LiveKit Agent — wires Phase 4 brain to real-time voice."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from livekit.agents import Agent, RunContext, function_tool

from foodease_agent.adapters.base import AppAdapter
from foodease_agent.broker import ActionBroker
from foodease_agent.config import Settings
from foodease_agent.contract.enums import Operation, ProductState
from foodease_agent.controls import ControlIntent, match_control
from foodease_agent.greeting import GreetingCache, GreetingSelector
from foodease_agent.idle import IdlePromptController
from foodease_agent.interruption import InterruptionReconciler
from foodease_agent.product_state import fatal_error_state, map_livekit_agent_state
from foodease_agent.turn_commit import TurnCommitGate

logger = logging.getLogger(__name__)

_POLICY_PATH = Path(__file__).resolve().parents[2] / "prompts" / "agent_policy.v1.md"


def _load_policy() -> str:
    if _POLICY_PATH.is_file():
        return _POLICY_PATH.read_text(encoding="utf-8")
    return (
        "You are a FoodEase shopping assistant, not a person. "
        "Use tools for facts. Keep replies to 1–3 short sentences."
    )


class FoodEaseAgent(Agent):
    """Voice agent with committed-turn mutation gating and control fast-path."""

    def __init__(
        self,
        settings: Settings,
        *,
        adapter: AppAdapter,
        idle: IdlePromptController | None = None,
        greetings: GreetingSelector | None = None,
        turn_gate: TurnCommitGate | None = None,
        reconciler: InterruptionReconciler | None = None,
    ) -> None:
        super().__init__(instructions=_load_policy())
        self.settings = settings
        self.adapter = adapter
        self.broker = ActionBroker(self.adapter)
        self.idle = idle or IdlePromptController(
            idle_1_seconds=settings.idle_prompt_1_seconds,
            idle_2_seconds=settings.idle_prompt_2_seconds,
        )
        self.greetings = greetings or GreetingSelector()
        self.turn_gate = turn_gate or TurnCommitGate()
        self.reconciler = reconciler or InterruptionReconciler()
        self.greeting_cache = GreetingCache(
            voice_id=settings.tts_voice_id,
            tts_model=settings.tts_model,
        )
        self.product_state = ProductState.OFF_AWAITING_CONSENT
        self._snapshot_ready = asyncio.Event()
        self._has_context = False
        self._greeted = False
        self._tts_speed = 1.0
        self._paused = False

    def set_product_state_from_lk(self, lk_state: str) -> ProductState:
        if self.product_state == ProductState.ERROR:
            return self.product_state
        self.product_state = map_livekit_agent_state(lk_state)
        return self.product_state

    def mark_fatal_error(self) -> ProductState:
        self.product_state = fatal_error_state()
        return self.product_state

    def notify_context_snapshot(self) -> None:
        self._has_context = True
        self._snapshot_ready.set()

    async def wait_for_snapshot_or_timeout(self) -> bool:
        """Return True if snapshot arrived; False on timeout (still greet)."""
        timeout = self.settings.snapshot_timeout_seconds
        try:
            await asyncio.wait_for(self._snapshot_ready.wait(), timeout=timeout)
            return True
        except TimeoutError:
            return False

    async def proactive_greeting(self, session: Any) -> str:
        """Speak first after consent + room ready (VA-01). Interruptible."""
        has_ctx = await self.wait_for_snapshot_or_timeout()
        text = self.greetings.next_greeting(has_context=has_ctx)
        self.greetings.mark_session_voice_active()
        audio = None
        if self.settings.greeting_cache:
            audio = self.greeting_cache.get(text)
        # session.say supports text + optional pre-synthesized audio (1.8 docs).
        if audio is not None:
            handle = session.say(text, audio=audio, allow_interruptions=True)
        else:
            handle = session.say(text, allow_interruptions=True)
        await handle
        self._greeted = True
        self.idle.on_assistant_finished()
        self.product_state = ProductState.READY_LISTENING
        return text

    def handle_control_utterance(self, utterance: str) -> ControlIntent | None:
        """Fast-path: stop/repeat/slower never reach the LLM."""
        match = match_control(utterance)
        if match is None:
            return None
        intent = match.intent
        if intent == ControlIntent.STOP:
            self.idle.disable()
        elif intent in {ControlIntent.PAUSE}:
            self._paused = True
            self.idle.set_muted(True)
            self.product_state = ProductState.MUTED_PAUSED
        elif intent == ControlIntent.RESUME:
            self._paused = False
            self.idle.set_muted(False)
            self.product_state = ProductState.READY_LISTENING
        elif intent == ControlIntent.SLOWER:
            self._tts_speed = max(0.7, self._tts_speed - 0.15)
        elif intent == ControlIntent.FASTER:
            self._tts_speed = min(1.3, self._tts_speed + 0.15)
        self.idle.reset_after_activity()
        return intent

    async def on_user_turn_completed(self, turn_ctx: Any, new_message: Any) -> None:
        """Commit the turn before any mutating tool may run."""
        self.turn_gate.mark_committed()
        self.idle.reset_after_activity()
        text = ""
        if new_message is not None:
            content = getattr(new_message, "text_content", None) or getattr(
                new_message, "content", ""
            )
            if isinstance(content, list):
                text = " ".join(str(c) for c in content)
            else:
                text = str(content or "")
        control = self.handle_control_utterance(text)
        if control is not None:
            # Control handled in code — suppress LLM by clearing tools path via StopResponse
            from livekit.agents.llm import StopResponse

            raise StopResponse()

    async def _execute_op(self, operation: Operation, arguments: dict[str, Any]) -> str:
        self.turn_gate.require(operation)
        snapshot = await self.adapter.get_snapshot()
        outcome = await self.broker.run(
            operation=operation, arguments=arguments, snapshot=snapshot
        )
        result = outcome.result
        self.reconciler.register_pending(result.action_id, operation.value)
        if result.status.value in {"success", "failed", "rejected", "stale_context"}:
            self.reconciler.resolve_pending(result.action_id)
        return f"{outcome.speak_guidance} | status={result.status.value}"

    @function_tool
    async def navigate(self, context: RunContext, target: str) -> str:
        """Navigate to a menu area or go back. target examples: home, burgers, cart, back."""
        return await self._execute_op(Operation.NAVIGATE, {"target": target})

    @function_tool
    async def search_menu(self, context: RunContext, query: str) -> str:
        """Search the menu by free-text query."""
        return await self._execute_op(Operation.SEARCH_MENU, {"query": query})

    @function_tool
    async def filter_menu(
        self,
        context: RunContext,
        category: str | None = None,
        vegetarian: bool | None = None,
        max_price_pkr: int | None = None,
    ) -> str:
        """Filter the menu by category, vegetarian flag, and/or max price in PKR."""
        args: dict[str, Any] = {}
        if category:
            args["category"] = category
        if vegetarian is not None:
            args["vegetarian"] = vegetarian
        if max_price_pkr is not None:
            args["max_price_pkr"] = max_price_pkr
        return await self._execute_op(Operation.FILTER_MENU, args)

    @function_tool
    async def select_item(self, context: RunContext, item_id: str) -> str:
        """Select a visible menu item by application item_id."""
        return await self._execute_op(Operation.SELECT_ITEM, {"item_id": item_id})

    @function_tool
    async def get_item_details(self, context: RunContext, item_id: str) -> str:
        """Get authoritative details for an item_id."""
        return await self._execute_op(Operation.GET_ITEM_DETAILS, {"item_id": item_id})

    @function_tool
    async def get_cart(self, context: RunContext) -> str:
        """Read the current cart from the application."""
        return await self._execute_op(Operation.GET_CART, {})

    @function_tool
    async def cart_add_item(
        self, context: RunContext, item_id: str, quantity: int = 1
    ) -> str:
        """Add an item to the cart. Only after the user turn is committed."""
        return await self._execute_op(
            Operation.CART_ADD_ITEM, {"item_id": item_id, "quantity": quantity}
        )

    @function_tool
    async def cart_set_quantity(
        self, context: RunContext, item_id: str, quantity: int
    ) -> str:
        """Set cart line quantity."""
        return await self._execute_op(
            Operation.CART_SET_QUANTITY, {"item_id": item_id, "quantity": quantity}
        )

    @function_tool
    async def cart_remove_item(self, context: RunContext, item_id: str) -> str:
        """Remove an item from the cart."""
        return await self._execute_op(Operation.CART_REMOVE_ITEM, {"item_id": item_id})

    @function_tool
    async def get_current_context(self, context: RunContext) -> str:
        """Fetch the latest application context snapshot."""
        return await self._execute_op(Operation.GET_CURRENT_CONTEXT, {})


async def apply_speech_speed(session: Any, speed: float) -> None:
    """Update Cartesia speed via update_options when supported."""
    tts = getattr(session, "tts", None)
    if tts is None:
        return
    update = getattr(tts, "update_options", None)
    if callable(update):
        try:
            update(speed=speed)
        except TypeError:
            logger.info("TTS update_options does not accept speed; skipping")
