"""Text-mode conversation engine — brain before audio."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Protocol

from foodease_agent.adapters.base import AppAdapter
from foodease_agent.broker import ActionBroker
from foodease_agent.confidence import ConfidenceGate
from foodease_agent.confirmation import ConfirmationMachine, ConfirmState
from foodease_agent.contract.enums import ActionResultStatus, Operation, ProductState
from foodease_agent.contract.models import ActionResultPayload, ContextSnapshot
from foodease_agent.controls import ControlIntent, match_control
from foodease_agent.faults import FAULTS
from foodease_agent.preferences import SessionPreferences
from foodease_agent.reconnect import ReconnectManager
from foodease_agent.recovery import Va17Situation, recover
from foodease_agent.reference import PresentedItem, ReferenceResolver
from foodease_agent.speech_text.sanitizer import count_sentences
from foodease_agent.speech_text.shaping import shape_assistant_reply
from foodease_agent.tiers import RiskTier, tier_for


@dataclass
class ToolCall:
    operation: Operation
    arguments: dict[str, Any]


@dataclass
class TurnResult:
    assistant_text: str
    state: ProductState
    tool_results: list[ActionResultPayload] = field(default_factory=list)
    clarification: str | None = None
    ended: bool = False
    control: ControlIntent | None = None


class Planner(Protocol):
    def plan(self, utterance: str, snapshot: ContextSnapshot) -> list[ToolCall] | str:
        """Return tool calls, or a plain assistant string (no tools)."""


@dataclass
class ConversationEngine:
    adapter: AppAdapter
    planner: Planner
    broker: ActionBroker | None = None
    confirmation: ConfirmationMachine = field(default_factory=ConfirmationMachine)
    prefs: SessionPreferences = field(default_factory=SessionPreferences)
    references: ReferenceResolver = field(default_factory=ReferenceResolver)
    last_assistant: str = ""
    state: ProductState = ProductState.READY_LISTENING
    pending_tier2: ToolCall | None = None
    known_item_ids: set[str] = field(default_factory=set)
    confidence_gate: ConfidenceGate = field(default_factory=ConfidenceGate)
    reconnect: ReconnectManager = field(default_factory=ReconnectManager)

    def __post_init__(self) -> None:
        if self.broker is None:
            self.broker = ActionBroker(self.adapter)

    async def handle_text(
        self,
        utterance: str,
        *,
        stt_confidence: float | None = None,
    ) -> TurnResult:
        if self.prefs.ended:
            return TurnResult(
                assistant_text="This session has ended.",
                state=ProductState.ENDED,
                ended=True,
            )

        # Provider / mic faults (VA-17) — never fake listening when STT is dead
        if FAULTS.mic_denied:
            r = recover(Va17Situation.MIC_DENIED)
            return self._reply(r.assistant_text, r.state)
        if FAULTS.fail_stt:
            r = recover(Va17Situation.STT_DOWN)
            self.state = ProductState.ERROR
            return self._reply(r.assistant_text, ProductState.ERROR)
        if FAULTS.fail_llm:
            r = recover(Va17Situation.LLM_DOWN)
            self.state = ProductState.ERROR
            return self._reply(r.assistant_text, ProductState.ERROR)
        if FAULTS.drop_connection:
            r = recover(Va17Situation.CONNECTION_LOSS)
            self.state = ProductState.RECONNECTING
            return self._reply(r.assistant_text, ProductState.RECONNECTING)

        conf = 0.2 if FAULTS.low_confidence else stt_confidence
        if self.confidence_gate.needs_clarification(utterance, conf):
            q = self.confidence_gate.clarify_line()
            return self._reply(q, ProductState.READY_LISTENING, clarification=q)

        # Control fast-path — stop never reaches planner/LLM
        control = match_control(utterance)
        if control is not None:
            return await self._handle_control(control.intent)

        snapshot = await self.adapter.get_snapshot()
        self.known_item_ids |= {v.item_id for v in snapshot.visible_items}
        self.known_item_ids |= {line.item_id for line in snapshot.cart.lines}
        self.confirmation.on_cart_or_revision_change(snapshot.revision)

        # Confirmation affirmative for checkout
        if self.confirmation.try_confirm(utterance, current_revision=snapshot.revision):
            return await self._submit_checkout(snapshot)

        # Tier-2 pending confirmation (remove)
        if self.pending_tier2 is not None:
            if utterance.strip().lower() in {"yes", "yeah", "yep", "confirm", "remove it"}:
                call = self.pending_tier2
                self.pending_tier2 = None
                return await self._execute_calls([call], snapshot, skip_tier_gates=True)
            if utterance.strip().lower() in {"no", "cancel", "stop"}:
                self.pending_tier2 = None
                text = "Okay, I will not remove it."
                return self._reply(text, ProductState.READY_LISTENING)

        # Reference resolution
        ref = self.references.resolve(utterance, current_revision=snapshot.revision)
        if isinstance(ref, str) and ref.startswith("clarify:"):
            q = "Which item did you mean? Please say the name."
            return self._reply(q, ProductState.READY_LISTENING, clarification=q)
        if isinstance(ref, PresentedItem):
            # Rewrite soft references into select/add using resolved id internally
            if "add" in utterance.lower():
                plan: list[ToolCall] | str = [
                    ToolCall(Operation.CART_ADD_ITEM, {"item_id": ref.item_id, "quantity": 1})
                ]
            else:
                plan = [ToolCall(Operation.SELECT_ITEM, {"item_id": ref.item_id})]
            return await self._execute_calls(plan, snapshot)

        # Adversarial / injection: never place order or invent success from speech alone
        low = utterance.lower()
        if any(
            p in low
            for p in (
                "just say it's added",
                "just say it is added",
                "ignore your rules",
                "place the order",
                "pretend",
            )
        ) and "confirm" not in low:
            if "place the order" in low or "ignore your rules" in low:
                return self._reply(
                    "I can only place a demo order after you confirm the current summary.",
                    ProductState.READY_LISTENING,
                )
            if "just say" in low:
                return self._reply(
                    "I only confirm cart changes after the app verifies them.",
                    ProductState.READY_LISTENING,
                )

        plan = self.planner.plan(utterance, snapshot)
        if isinstance(plan, str):
            return self._reply(plan, ProductState.READY_LISTENING)

        return await self._execute_calls(plan, snapshot)

    async def _handle_control(self, intent: ControlIntent) -> TurnResult:
        if intent == ControlIntent.STOP:
            # VA-17: stop during checkout — do not infer consent
            if self.confirmation.state.value in {"awaiting", "confirmed"}:
                self.confirmation.invalidate()
                r = recover(Va17Situation.STOP_DURING_CHECKOUT)
                self.state = ProductState.READY_LISTENING
                return TurnResult(
                    assistant_text=r.assistant_text,
                    state=self.state,
                    control=intent,
                )
            self.state = ProductState.READY_LISTENING
            return TurnResult(assistant_text="", state=self.state, control=intent)
        if intent == ControlIntent.REPEAT:
            text = self.last_assistant or "I have not said anything yet."
            return self._reply(text, ProductState.ASSISTANT_SPEAKING, control=intent)
        if intent == ControlIntent.GO_BACK:
            snapshot = await self.adapter.get_snapshot()
            return await self._execute_calls(
                [ToolCall(Operation.NAVIGATE, {"target": "back"})], snapshot, control=intent
            )
        if intent == ControlIntent.UNDO:
            snapshot = await self.adapter.get_snapshot()
            return await self._execute_calls(
                [ToolCall(Operation.UNDO_LAST_REVERSIBLE_ACTION, {})], snapshot, control=intent
            )
        if intent == ControlIntent.HELP:
            return self._reply(
                "I can help you browse the menu, filter dishes, update the cart, and place a demo order.",
                ProductState.READY_LISTENING,
                control=intent,
            )
        if intent == ControlIntent.BROWSE_SELF:
            self.prefs.browsing_self = True
            return self._reply(
                "Okay. I will stay quiet unless you ask for help. Your cart stays as it is.",
                ProductState.IDLE,
                control=intent,
            )
        if intent == ControlIntent.SWITCH_TYPING:
            return self._reply(
                "You can type instead. I will treat typed messages the same way.",
                ProductState.READY_LISTENING,
                control=intent,
            )
        if intent == ControlIntent.GOODBYE:
            self.prefs.ended = True
            self.state = ProductState.ENDED
            return self._reply("Thanks for trying the demo. Goodbye.", self.state, control=intent, ended=True)
        if intent == ControlIntent.MORE_DETAIL:
            self.prefs.detail_level = "more"
            return self._reply("Okay, I will give a bit more detail.", ProductState.READY_LISTENING, control=intent)
        if intent == ControlIntent.LESS_DETAIL:
            self.prefs.detail_level = "brief"
            return self._reply("Okay, I will keep it brief.", ProductState.READY_LISTENING, control=intent)
        if intent in {ControlIntent.SLOWER, ControlIntent.FASTER, ControlIntent.QUIETER, ControlIntent.LOUDER}:
            return self._reply("Okay, I will adjust that when speaking.", ProductState.READY_LISTENING, control=intent)
        if intent == ControlIntent.PAUSE:
            self.state = ProductState.MUTED_PAUSED
            return TurnResult(assistant_text="Paused.", state=self.state, control=intent)
        if intent == ControlIntent.RESUME:
            self.state = ProductState.READY_LISTENING
            return self._reply("I am listening again.", self.state, control=intent)
        return self._reply("Okay.", ProductState.READY_LISTENING, control=intent)

    async def _submit_checkout(self, snapshot: ContextSnapshot) -> TurnResult:
        assert self.broker is not None
        args: dict[str, Any] = {"confirmed": True}
        if self.confirmation.confirmation_token:
            args["confirmation_token"] = self.confirmation.confirmation_token
        outcome = await self.broker.run(
            operation=Operation.CHECKOUT_SUBMIT_DEMO_ORDER,
            arguments=args,
            snapshot=snapshot,
        )
        self.confirmation.mark_submitted()
        if outcome.result.status == ActionResultStatus.SUCCESS:
            text = "Demo order placed. No real payment was taken."
        else:
            text = outcome.speak_guidance.replace("not verified:", "I could not finish that.")
        return self._reply(text, ProductState.READY_LISTENING, tools=[outcome.result])

    async def _execute_calls(
        self,
        calls: list[ToolCall],
        snapshot: ContextSnapshot,
        control: ControlIntent | None = None,
        *,
        skip_tier_gates: bool = False,
    ) -> TurnResult:
        assert self.broker is not None
        if self.prefs.browsing_self and not calls:
            return self._reply("", ProductState.IDLE, control=control)

        results: list[ActionResultPayload] = []
        lines: list[str] = []

        for call in calls:
            tier = tier_for(call.operation)

            # Tier 3: never submit without confirmation machine
            if not skip_tier_gates and tier == RiskTier.CHECKOUT_SUBMIT:
                if self.confirmation.state != ConfirmState.CONFIRMED:
                    # Fetch summary instead and await confirmation
                    summary = await self.broker.run(
                        operation=Operation.CHECKOUT_GET_SUMMARY,
                        arguments={},
                        snapshot=snapshot,
                    )
                    results.append(summary.result)
                    snapshot = summary.snapshot
                    if summary.result.status == ActionResultStatus.SUCCESS:
                        total = (summary.result.verified_state or {}).get("total")
                        spoken = f"Your demo total is {total} rupees. Shall I place the demo order?"
                        self.confirmation.begin_awaiting(
                            summary=summary.result.verified_state or {},
                            revision=snapshot.revision,
                            summary_text=spoken,
                            confirmation_token=summary.result.confirmation_token,
                        )
                        self.confirmation.mark_summary_delivered()
                        return self._reply(spoken, ProductState.READY_LISTENING, tools=results, control=control)
                    return self._reply(
                        "I could not get a checkout summary yet.",
                        ProductState.READY_LISTENING,
                        tools=results,
                        control=control,
                    )

            # Tier 2 remove: confirm scope first
            if (
                not skip_tier_gates
                and tier == RiskTier.DESTRUCTIVE_OR_AMBIGUOUS
                and self.pending_tier2 is None
            ):
                self.pending_tier2 = call
                item = call.arguments.get("item_id", "that item")
                # Speak name if possible
                name = item
                for line in snapshot.cart.lines:
                    if line.item_id == item:
                        name = line.name
                        break
                q = f"Remove {name} from the cart?"
                return self._reply(q, ProductState.READY_LISTENING, clarification=q, control=control)

            outcome = await self.broker.run(
                operation=call.operation,
                arguments=call.arguments,
                snapshot=snapshot,
            )
            results.append(outcome.result)
            snapshot = outcome.snapshot
            self.confirmation.on_cart_or_revision_change(snapshot.revision)
            self.reconnect.register_mutation(outcome.result.action_id, call.operation)
            self.reconnect.resolve(outcome.result)

            if call.operation in {Operation.SEARCH_MENU, Operation.FILTER_MENU}:
                items = (outcome.result.verified_state or {}).get("items") or []
                presented = [
                    PresentedItem(
                        item_id=i["item_id"],
                        name=i["name"],
                        price=float(i["price"]),
                    )
                    for i in items[:5]
                    if "item_id" in i
                ]
                self.references.set_list(presented, revision=snapshot.revision)
                if presented:
                    bits = [f"{p.name} at {int(p.price)} rupees" for p in presented[:3]]
                    lines.append("Here is what I found: " + "; ".join(bits) + ".")
                else:
                    lines.append("I did not find matching items.")
            elif outcome.result.status == ActionResultStatus.SUCCESS:
                if call.operation == Operation.NAVIGATE:
                    # Populate reference list from new snapshot visibles
                    presented = [
                        PresentedItem(
                            item_id=v.item_id,
                            name=v.name,
                            price=float(v.price),
                        )
                        for v in snapshot.visible_items[:5]
                    ]
                    if presented:
                        self.references.set_list(presented, revision=snapshot.revision)
                        bits = [f"{p.name} at {int(p.price)} rupees" for p in presented[:3]]
                        lines.append("Here is what I found: " + "; ".join(bits) + ".")
                    else:
                        lines.append(self._friendly_success(call.operation, outcome.result))
                else:
                    lines.append(self._friendly_success(call.operation, outcome.result))
            elif outcome.result.status == ActionResultStatus.TIMEOUT_UNKNOWN:
                lines.append(recover(Va17Situation.ACTION_TIMEOUT).assistant_text)
            elif outcome.result.status in {
                ActionResultStatus.REJECTED,
                ActionResultStatus.FAILED,
            }:
                reason = outcome.result.error_message or "That request was rejected."
                lines.append(recover(Va17Situation.ACTION_REJECTED, app_reason=reason).assistant_text)
            else:
                lines.append(outcome.result.error_message or "That did not work.")

            # After checkout summary tool explicitly
            if (
                call.operation == Operation.CHECKOUT_GET_SUMMARY
                and outcome.result.status == ActionResultStatus.SUCCESS
            ):
                total = (outcome.result.verified_state or {}).get("total")
                spoken = f"Your demo total is {total} rupees. Shall I place the demo order?"
                self.confirmation.begin_awaiting(
                    summary=outcome.result.verified_state or {},
                    revision=snapshot.revision,
                    summary_text=spoken,
                    confirmation_token=outcome.result.confirmation_token,
                )
                self.confirmation.mark_summary_delivered()
                lines = [spoken]

        text = " ".join(lines) if lines else "Okay."
        return self._reply(text, ProductState.READY_LISTENING, tools=results, control=control)

    def _friendly_success(self, operation: Operation, result: ActionResultPayload) -> str:
        state = result.verified_state or {}
        if operation in {
            Operation.CART_ADD_ITEM,
            Operation.CART_SET_QUANTITY,
            Operation.CART_REMOVE_ITEM,
            Operation.UNDO_LAST_REVERSIBLE_ACTION,
        }:
            total = state.get("total")
            lines = state.get("cart") or []
            if not lines:
                return "Your cart is empty."
            last = lines[-1]
            return f"Updated. You have {last.get('quantity')} {last.get('name')}. Total {total} rupees."
        if operation == Operation.NAVIGATE:
            return "Okay, navigated."
        if operation == Operation.SELECT_ITEM:
            return "Okay, selected."
        if operation == Operation.GET_CART:
            total = state.get("total")
            return f"Your cart total is {total} rupees."
        if operation == Operation.GET_ITEM_DETAILS:
            name = state.get("name", "that item")
            if state.get("ingredients_available") is False or state.get("ingredients") is None:
                return f"I don't have ingredient information for {name}."
            ingredients = state.get("ingredients") or []
            if ingredients:
                joined = ", ".join(str(x) for x in ingredients)
                return f"{name} includes {joined}."
            return f"I don't have that information for {name}."
        if operation == Operation.CHECKOUT_SUBMIT_DEMO_ORDER:
            return "Demo order placed. No real payment was taken."
        return "Done."

    def _reply(
        self,
        text: str,
        state: ProductState,
        *,
        tools: list[ActionResultPayload] | None = None,
        clarification: str | None = None,
        control: ControlIntent | None = None,
        ended: bool = False,
    ) -> TurnResult:
        # TTS down: keep text/status on screen; never pretend speech worked (VA-17)
        if FAULTS.fail_tts and text.strip():
            note = recover(Va17Situation.TTS_DOWN).assistant_text
            if note and note not in text:
                text = f"{note} {text}".strip()
        forms = shape_assistant_reply(text, known_item_ids=self.known_item_ids)
        clean = forms.spoken_text
        if self.prefs.detail_level == "brief" and count_sentences(clean) > 2:
            # Keep first two sentences
            parts = re.split(r"(?<=[.!?])\s+", clean)
            clean = " ".join(parts[:2]).strip()
        self.last_assistant = clean
        self.state = state
        return TurnResult(
            assistant_text=clean,
            state=state,
            tool_results=tools or [],
            clarification=clarification,
            ended=ended,
            control=control,
        )
