"""Shared turn/control/delivery policy connected to public LiveKit session events."""

from __future__ import annotations

import asyncio
import contextlib
import json
import re
from collections.abc import Callable
from typing import Any

from foodease_contract.models import ActionResultEvent, ContextSnapshot, VisibleItem
from livekit.agents import llm

from foodease_agent.adapters.integrated import IntegratedAppAdapter, new_id
from foodease_agent.confirmation import ConfirmationMachine, ConfirmState
from foodease_agent.i18n import label, render, speech_text
from foodease_agent.idle import IdlePromptController
from foodease_agent.integrated.broker import IntegratedActionBroker
from foodease_agent.integrated.control_intents import CONVERSATION_INTENTS, PAGE_INTENTS
from foodease_agent.integrated.conversation import (
    BrowseMemory,
    SemanticPage,
    list_speech,
    reference_item,
)
from foodease_agent.integrated.policy import (
    Turn,
    cart_hash,
    cart_speech,
    explicit_yes,
    has_reference,
    safe_failure,
)
from foodease_agent.integrated.recovery import RuntimeRecovery
from foodease_agent.interruption import InterruptionReconciler
from foodease_agent.preferences import SessionPreferences
from foodease_agent.production_metrics import log_metrics
from foodease_agent.reference import PresentedItem, ReferenceResolver
from foodease_agent.speech_text.shaping import shape_assistant_reply


class LiveConversationRuntime:
    def __init__(
        self,
        agent: Any,
        session: Any,
        adapter: IntegratedAppAdapter,
        *,
        gate: Any = None,
        idle: IdlePromptController | None = None,
        speech_controls: frozenset[str] = frozenset(),
    ):
        self.agent, self.session, self.adapter, self.gate = agent, session, adapter, gate
        self.language = agent.language
        agent.runtime = self
        self.snapshot: ContextSnapshot
        self.mode: str | None = None
        self._opening_started = False
        self._announced_mode: str | None = None
        self._choice_clarified = False
        self._choice_deadline: float | None = None
        self.typed_audio = False
        self.closed, self.paused, self.muted, self.tips_paused = False, False, False, False
        self.epoch = 0
        self.active_turn: Turn | None = None
        self.preferences = SessionPreferences()
        self.references = ReferenceResolver()
        self.browse = BrowseMemory()
        self.details: dict[str, dict] = {}
        self.last_cart_item: str | None = None
        self.references_stale = False
        self.speech_controls = speech_controls
        self._volume = 1.0
        self.confirmation = ConfirmationMachine()
        self.confirm_cart: str | None = None
        self.confirm_turn: str | None = None
        self.summary_id: str | None = None
        self.reconciler = InterruptionReconciler()
        self.broker = IntegratedActionBroker(self)
        self.pending = self.broker.pending
        self.idle = idle or IdlePromptController()
        self.speech_turns: dict[str, Turn] = {}
        self.speeches: dict[str, Any] = {}
        self._generating_turn: Turn | None = None
        self._last_completed: tuple[str, int] | None = None
        self._background: set[asyncio.Task] = set()
        self._output_tasks: set[asyncio.Task] = set()
        self._captions: dict[str, dict[str, Any]] = {}
        self._user_caption_id: str | None = None
        self._seen_inputs: dict[str, None] = {}
        self._idle_task: asyncio.Task | None = None
        self._started = False
        self._before_start: list[Any] = list(gate.events) if gate is not None else []
        if gate is not None and gate.latest is not None:
            self.snapshot = gate.latest
        self._speed = 1.0
        self._user_speaking = self._agent_speaking = False
        self.recovery = RuntimeRecovery(self)
        self._handlers = {
            "conversation_item_added": log_metrics,
            "speech_created": self.on_speech_created,
            "user_state_changed": self.on_user_state,
            "agent_state_changed": self.on_agent_state,
            "close": self.on_session_close,
            "user_input_transcribed": self.on_user_transcript,
            "error": self.recovery.provider_error,
            "agent_false_interruption": lambda event: self.recovery.observe(
                "false_interruption", resumed=event.resumed
            ),
        }
        for event, callback in self._handlers.items():
            session.on(event, callback)
        if gate is not None:
            gate.subscribe(self.on_room_event, self.end_local)
        self._room_handlers = {}
        if gate is not None:
            self._room_handlers = {
                "reconnecting": self.recovery.room_reconnecting,
                "reconnected": self.recovery.room_reconnected,
            }
            for event, callback in self._room_handlers.items():
                gate.room.on(event, callback)

    def t(self, template: str, **values) -> str:
        return render(template, self.language, **values)

    async def prepare(self) -> None:
        self.snapshot = await self.adapter.get_snapshot()
        self._sync_preferences()
        self.browse.reset(self.snapshot.visible_items, self.snapshot.revision)
        self._set_audio()

    async def start(self) -> None:
        """Called only after Phase 3's authenticated worker-ready acknowledgement."""
        from livekit.agents import room_io

        if self.closed or self.gate is None or self.gate.closed:
            raise RuntimeError("integrated runtime closed")
        await self.session.start(
            agent=self.agent,
            record=False,
            session_host=False,
            room=self.gate.room,
            room_options=room_io.RoomOptions(
                participant_identity=self.gate.startup.binding.user_identity,
                text_input=False,
                close_on_disconnect=True,
            ),
        )
        self._started = True
        self._set_audio()
        self._idle_task = asyncio.create_task(self._idle_loop())
        pending, self._before_start = self._before_start, []
        for event in pending:
            self.on_room_event(event)
        # Dispatch alone never authorizes shopping or an opening prompt.

    async def open_mode_choice(self) -> None:
        if self.closed or self._opening_started:
            return
        self._opening_started = True
        self.mode = "choosing"
        self._set_audio()
        self._choice_deadline = asyncio.get_running_loop().time() + 15
        self.say(
            "Welcome to FoodEase! How would you like to order today — by voice, or browse yourself?"
        )

    async def choice_timeout(self) -> None:
        if self.mode != "choosing" or self._choice_clarified or self.closed:
            return
        self._choice_clarified = True
        self.say(
            "Would you like to talk through your order, type your request, or browse yourself?"
        )

    async def activate_mode(self, mode: str, *, resuming=False) -> None:
        if mode == "voice" and self.recovery.speech_failed:
            return
        if resuming and self.mode == mode and self._announced_mode == mode:
            if self.paused:
                await self.handle_control("resume")
            return
        if (
            self.closed
            or mode not in {"voice", "typed"}
            or (self.mode == mode and self._announced_mode == mode)
        ):
            return
        self._opening_started = True
        self._announced_mode = mode
        await self.select_mode(mode)
        self.say(
            "Welcome back. What would you like to do next?"
            if resuming
            else "I’m here to help. What would you like to eat?"
        )

    def _sync_preferences(self) -> None:
        self.preferences.vegetarian = "vegetarian" in self.snapshot.filter_tags
        self.preferences.budget_pkr = self.snapshot.max_price_pkr

    def _set_audio(self) -> None:
        voice = self.mode in {"voice", "choosing"} and not self.recovery.speech_failed
        output = voice or self.mode == "typed" and self.typed_audio
        self.session.input.set_audio_enabled(voice and not self.closed and not self.paused)
        self.session.output.set_audio_enabled(
            output
            and not self.closed
            and not self.muted
            and not self.paused
            and not self.recovery.speech_failed
        )

    def _interrupt(self) -> None:
        # Public interruption stops generation/audio. Owned broker tasks are shielded.
        with contextlib.suppress(RuntimeError):
            self.session.interrupt(force=True)

    def _invalidate_confirmation(self) -> None:
        self.confirmation.invalidate()
        self.confirm_cart = self.confirm_turn = self.summary_id = None

    async def select_mode(self, mode: str) -> None:
        if mode not in {"voice", "typed", "manual"} or self.closed:
            return
        if mode == "voice" and self.recovery.speech_failed:
            return
        self.epoch += 1
        if self.active_turn:
            self.active_turn.discarded = True
        self.mode = mode
        self.paused = self.muted = self.typed_audio = False
        self._invalidate_confirmation()
        self.references.clear()
        self._interrupt()
        self.idle.reset_after_activity()
        self._set_audio()

    def authorized(self, turn: Turn, *, revision=True, conversation=False) -> bool:
        return bool(
            not self.closed
            and not self.paused
            and self.mode
            in ({"voice", "typed", "choosing"} if conversation else {"voice", "typed"})
            and self.active_turn is turn
            and turn.epoch == self.epoch
            and turn.committed
            and not turn.discarded
            and (turn.speech is None or not turn.speech.interrupted)
            and (not revision or turn.revision == self.snapshot.revision)
            and (
                turn.source == "text"
                or self.mode == "voice"
                or conversation
                and self.mode == "choosing"
            )
        )

    def uncommit_turn(self, turn_id: str) -> None:
        if self.active_turn and self.active_turn.id == turn_id:
            self.active_turn.committed = False
            self._invalidate_confirmation()
            self._interrupt()

    def discard_turn(self, turn_id: str) -> None:
        if self.active_turn and self.active_turn.id == turn_id:
            self.active_turn.discarded = True
            self._invalidate_confirmation()
            self._interrupt()

    def on_context(self, snapshot: ContextSnapshot, *, source_turn: str | None = None) -> None:
        snapshot = ContextSnapshot.model_validate(snapshot.model_dump(mode="json"))
        if (
            snapshot.session_id != self.snapshot.session_id
            or snapshot.revision <= self.snapshot.revision
        ):
            return
        old_cart = cart_hash(self.snapshot.cart)
        old_items = self.snapshot.visible_items
        self.snapshot = snapshot
        self._sync_preferences()
        self.references.clear()
        self._last_completed = None
        self.idle.reset_after_activity()
        if old_cart != cart_hash(snapshot.cart):
            self._invalidate_confirmation()
        candidates = [record.request for record in self.pending.values()]
        own = (
            self.active_turn
            and source_turn == self.active_turn.id
            and (
                any(
                    request.turn_id == source_turn
                    and request.context_revision + 1 == snapshot.revision
                    for request in candidates
                )
                or any(
                    result.turn_id == source_turn
                    and result.context_revision == snapshot.revision
                    and result.payload.status == "success"
                    for result in self.broker.results.values()
                )
            )
        )
        if not own:
            self.browse.reset([], snapshot.revision)
            self.references_stale = True
            self.last_cart_item = None
            if self.active_turn:
                self.discard_turn(self.active_turn.id)
            self._interrupt()
        elif old_items == snapshot.visible_items:
            self.browse.revision = snapshot.revision
        else:
            self.browse.reset(snapshot.visible_items, snapshot.revision)
        self.details.clear()

    def reasoning_data(self) -> dict:
        if self.mode == "choosing":
            return {
                "response_language": self.language,
                "mode": self.mode,
                "ordering_modes": ["voice", "typed", "manual"],
            }
        # All rows are contract bounded; cap untrusted free text further for prompts.
        data = self.snapshot.model_dump(mode="json", exclude={"cart"})
        data["visible_items"] = [
            {
                **row,
                "name": row["name"][:120],
                "descriptors": [s[:80] for s in row["descriptors"]],
                "speech_name": label(row["name"], self.language),
            }
            for row in data["visible_items"]
        ]
        semantic_page = SemanticPage(self.snapshot, self.details).data()
        # The complete ordered list is already in page.visible_items.
        del semantic_page["results"]
        return {
            "response_language": self.language,
            "page": data,
            "semantic_page": semantic_page,
            "mode": self.mode,
            "preferences": {
                "vegetarian": self.preferences.vegetarian,
                "budget_pkr": self.preferences.budget_pkr,
                "detail_level": self.preferences.detail_level,
            },
            "current_presented_list": [i.item_id for i in self.references.items],
            "presented_revision": self.references.revision,
            "references_invalidated_by_manual_change": self.references_stale,
            "checkout_summary_delivered": self.confirmation.summary_spoken,
        }

    async def input_text(
        self, text: str, turn_id: str, revision: int, *, source="text", chat_ctx=None, message=None
    ) -> Any:
        if self.closed or self.mode not in {"voice", "typed", "choosing"}:
            return None
        if source not in {"audio", "text"} or (
            source == "audio" and self.mode not in {"voice", "choosing"}
        ):
            return None
        if not text.strip() or len(text) > 2000 or not turn_id or len(turn_id) > 128:
            return None
        if turn_id in self._seen_inputs:
            return None
        self._seen_inputs[turn_id] = None
        # A finite session budget rejects new input, never evicts replay identities.
        if len(self._seen_inputs) > 2048:
            self.end_local()
            return None
        self._interrupt()
        if self.active_turn:
            self.active_turn.discarded = True
        turn = Turn(turn_id, revision, self.epoch, source, text)
        self.active_turn = turn
        self.idle.reset_after_activity()
        if revision != self.snapshot.revision:
            turn.discarded = True
            return None
        if self.confirmation.state == ConfirmState.AWAITING:
            if (
                explicit_yes(text)
                and self.confirm_cart == cart_hash(self.snapshot.cart)
                and self.confirmation.try_confirm(
                    "yes", current_revision=self.confirmation.revision or 0
                )
            ):
                self.confirm_turn = turn.id
            else:
                self._invalidate_confirmation()
        elif self.confirmation.state == ConfirmState.CONFIRMED:
            self._invalidate_confirmation()
        self._generating_turn = turn
        try:
            kwargs = {
                "user_input": message or llm.ChatMessage(role="user", content=[text], id=turn_id),
                "input_modality": source,
            }
            if self.mode == "choosing" or self.paused or self.muted:
                kwargs["tools"] = ["conversation_control"]
            if chat_ctx is not None:
                kwargs["chat_ctx"] = chat_ctx
            handle = self.session.generate_reply(**kwargs)
            # Public SDK emits speech_created synchronously; bind returned ID too.
            self.speech_turns[handle.id] = turn
            turn.speech = handle
            return handle
        finally:
            self._generating_turn = None

    async def execute_control(self, context: Any, intent: str) -> dict:
        speech = context.speech_handle
        turn = self.speech_turns.get(speech.id)
        if (
            context.session is not self.session
            or turn is None
            or self.closed
            or self.active_turn is not turn
            or turn.discarded
            or not turn.committed
            or turn.epoch != self.epoch
            or turn.revision != self.snapshot.revision
            or speech.interrupted
            or turn.control_done
            or self.mode not in {"voice", "typed", "choosing"}
            or (turn.source == "audio" and self.mode not in {"voice", "choosing"})
        ):
            return safe_failure("inactive_turn")
        if intent not in CONVERSATION_INTENTS:
            return safe_failure("invalid_arguments")
        choosing = self.mode == "choosing"
        if choosing and intent not in {"voice", "typed", "manual", "end", "stop", "pause", "mute"}:
            return safe_failure("invalid_arguments")
        if (self.paused or self.muted) and intent in (
            PAGE_INTENTS | {"go_back", "undo", "more_detail"}
        ):
            return safe_failure("inactive_turn")
        turn.control_done = True  # before any await; duplicate effects cannot race
        if intent in {"voice", "typed"}:
            await self.activate_mode(intent)
            await self.adapter.publish_control("switch_mode", self.mode)
        elif intent in PAGE_INTENTS:
            await self.handle_semantic(intent, turn)
        else:
            await self.handle_control(intent, turn)
        return {"status": "success", "facts": None, "say": ""}

    async def handle_semantic(self, command: str, turn: Turn) -> None:
        # Read-only refresh and subsequent semantic operations share the owned lane.
        if command == "unsupported_button":
            self.say(
                "I can help with menu, cart and demo checkout controls. "
                "I can’t activate a camera or make a real payment."
            )
            return
        if command == "read_cart":
            result = await self.broker.run(turn, "get_cart", {})
            if self.authorized(turn):
                self.say(result["say"])
            return
        if command in {"read_page", "read_categories", "next", "previous", "add_button"}:
            fresh = await self.broker.run(turn, "get_current_context", {})
            if fresh["status"] != "success" or not self.authorized(turn):
                if self.authorized(turn):
                    self.say(fresh["say"])
                return
        if command == "read_categories":
            categories = [
                target.replace("-", " ")
                for target in self.snapshot.valid_navigation_targets
                if target not in {"home", "menu", "back", "cart", "checkout"}
            ]
            self.say(
                self.t(
                    "The menu categories are {categories}.",
                    categories=", ".join(label(row, self.language) for row in categories),
                )
                if categories
                else "I couldn’t find any menu categories on the site."
            )
        elif command == "read_page":
            if self.snapshot.focus_item_id:
                result = await self.broker.run(
                    turn, "get_item_details", {"item_id": self.snapshot.focus_item_id}
                )
                if result["status"] != "success":
                    self.say(result["say"])
                    return
            self.say(SemanticPage(self.snapshot, self.details).speech(language=self.language))
        elif command in {"next", "previous"}:
            rows = self.browse.window(command)
            self.say(
                list_speech(rows, language=self.language) + self.t(" Would you like to open one?")
                if rows
                else "There are no more options in this view. You can change the search or filters."
            )
        elif command == "add_button":
            item = self.snapshot.focus_item_id
            if not item or "cart.add_item" not in self.snapshot.valid_actions:
                self.say("Open an item first so I know which Add to cart button you mean.")
                return
            result = await self.broker.run(turn, "cart.add_item", {"item_id": item, "quantity": 1})
            if self.authorized(turn):
                self.say(result["say"])
        elif command == "open_reference":
            item = reference_item(turn.text, self.references.items)
            if not item or self.references.revision != self.snapshot.revision:
                self.say(
                    "Which item do you mean? Please name it, or ask me to read the current options."
                )
                return
            result = await self.broker.run(turn, "select_item", {"item_id": item})
            if self.authorized(turn):
                self.say(result["say"])

    async def handle_control(self, control: str, turn: Turn | None = None) -> None:
        self.idle.reset_after_activity()
        if control in {"manual", "browse_self", "voice", "typed", "switch_typing"}:
            await self.select_mode(
                {"browse_self": "manual", "switch_typing": "typed"}.get(control, control)
            )
        elif control == "end":
            self.end_local()
        elif control in {"mute", "unmute"} and self.mode == "typed":
            self.typed_audio = control == "unmute"
            self.muted = False  # Silent typing still delivers text.
            self._set_audio()
        elif control in {"stop", "pause", "mute"}:
            self.recovery.revoke()
            if self.active_turn:
                self.active_turn.discarded = True
            self.paused = control == "pause"
            self.muted = control == "mute"
            self.tips_paused = True
            self._set_audio()
        elif control in {"resume", "unmute"}:
            if await self.recovery.resume():
                self.say("I’m here. What would you like to do next?")
        elif control in {"pause_tips", "stop_tips", "resume_tips"}:
            self.tips_paused = control != "resume_tips"
        elif control == "repeat":
            if self._last_completed and self._last_completed[1] == self.snapshot.revision:
                self.say(self._last_completed[0])
            else:
                self.say(
                    "I don’t have a completed reply for this page. What would you like me to read?"
                )
        elif control in {"go_back", "undo"} and turn is not None and self.authorized(turn):
            operation = "navigate" if control == "go_back" else "undo_last_reversible_action"
            result = await self.broker.run(
                turn, operation, {"target": "back"} if control == "go_back" else {}
            )
            if self.authorized(turn):
                self.say(result["say"])
        elif control in {"slower", "faster"}:
            desired = max(0.7, min(1.3, self._speed + (-0.1 if control == "slower" else 0.1)))
            try:
                if "speed" not in self.speech_controls:
                    raise ValueError("unsupported speech control")
                self.session.tts.update_options(speed=desired)
            except (AttributeError, TypeError, ValueError):
                self.say("I can’t change the speech speed with this voice.")
            else:
                self._speed = desired
                self.say("I’ll use that pace.")
        elif control in {"quieter", "louder"}:
            desired = max(0.5, min(1.5, self._volume + (-0.1 if control == "quieter" else 0.1)))
            try:
                if "volume" not in self.speech_controls:
                    raise ValueError("unsupported speech control")
                self.session.tts.update_options(volume=desired)
            except (AttributeError, TypeError, ValueError):
                self.say("Please use your device’s volume controls to change how loud I sound.")
            else:
                self._volume = desired
                self.say("I’ll use that volume for my next reply.")
        elif control in {"more_detail", "less_detail"}:
            self.preferences.detail_level = "more" if control == "more_detail" else "brief"
            if (
                control == "more_detail"
                and self.language == "en"
                and self.snapshot.focus_item_id
                and turn is not None
            ):
                result = await self.broker.run(
                    turn, "get_item_details", {"item_id": self.snapshot.focus_item_id}
                )
                if self.authorized(turn):
                    if result["status"] == "success":
                        facts = result["facts"]
                        ingredients = facts.get("ingredients")
                        detail = facts["description"] + " "
                        detail += (
                            "Ingredients: " + ", ".join(ingredients) + "."
                            if ingredients
                            else "No ingredient information is available for this item."
                        )
                        self.say(detail)
                    else:
                        self.say(result["say"])
            else:
                self.say("Of course. What would you like to know?")
        elif control in {"help", "explain"}:
            self.say(
                "You can ask me to read the page, find food, change your cart, or check out. "
                "Say stop anytime."
            )
        if turn is not None:
            intent = {
                "manual": "switch_mode",
                "browse_self": "switch_mode",
                "voice": "switch_mode",
                "typed": "switch_mode",
                "switch_typing": "switch_mode",
                "end": "end",
                "pause": "pause",
                "resume": "resume",
                "mute": "mute",
                "unmute": "unmute",
            }.get(control)
            if intent:
                try:
                    await self.adapter.publish_control(
                        intent, self.mode if intent == "switch_mode" else None
                    )
                except Exception:
                    pass  # local revocation already took effect; never report remote cleanup
        if control in {"manual", "browse_self"}:
            self.end_local()

    async def execute(
        self,
        context: Any,
        operation: str,
        arguments: dict | Callable[[], dict],
        *,
        read_all: bool = False,
        sort_by: str | None = None,
    ) -> dict:
        speech = context.speech_handle
        turn = self.speech_turns.get(speech.id)
        if context.session is not self.session or turn is None or speech.interrupted:
            return safe_failure("inactive_turn")
        if not self.authorized(turn) or self.muted:
            return safe_failure("inactive_turn")
        if turn.control_done:
            return safe_failure("inactive_turn")
        if operation in {"search_menu", "filter_menu"}:
            if sort_by not in {None, "price_asc", "price_desc", "name"}:
                return safe_failure("invalid_arguments")
            turn.read_all = read_all
            turn.sort_by = sort_by
        if not isinstance(arguments, dict):
            if operation != "filter_menu":
                return safe_failure("invalid_arguments")
            return await self.broker.run(turn, operation, arguments)
        arguments = dict(arguments)
        if "item_id" in arguments:
            item = arguments["item_id"]
            names = [(row.item_id, row.name) for row in self.snapshot.visible_items]
            names += [(row.item_id, row.name) for row in self.snapshot.cart.lines]
            explicit_name = any(
                candidate == item
                and any(
                    value.lower() in turn.text.lower()
                    for value in {name, label(name, self.language)}
                )
                for candidate, name in names
            )
            if has_reference(turn.text) and not explicit_name:
                if self.references_stale:
                    turn.blocked = True
                    return safe_failure("stale_context")
                focus = self.snapshot.focus_item_id or self.last_cart_item
                resolved = reference_item(turn.text, self.references.items, focus)
                if not resolved or (
                    not focus and self.references.revision != self.snapshot.revision
                ):
                    turn.blocked = True
                    return safe_failure("stale_context")
                item = arguments["item_id"] = resolved
            known = {row.item_id for row in self.snapshot.visible_items} | {
                row.item_id for row in self.snapshot.cart.lines
            }
            if self.snapshot.focus_item_id:
                known.add(self.snapshot.focus_item_id)
            if item not in known:
                resolved = self.references.resolve(item, current_revision=self.snapshot.revision)
                if not isinstance(resolved, PresentedItem):
                    turn.blocked = True
                    return safe_failure("stale_context")
                arguments["item_id"] = resolved.item_id
        return await self.broker.run(turn, operation, arguments)

    def consume_confirmation(self, turn: Turn) -> dict | None:
        confirmation = self.confirmation
        if (
            self.confirm_turn != turn.id
            or confirmation.state != ConfirmState.CONFIRMED
            or not confirmation.summary_spoken
            or self.confirm_cart != cart_hash(self.snapshot.cart)
        ):
            return None
        arguments = {
            "confirmed": True,
            "confirmation_token": confirmation.confirmation_token,
            "summary_revision": confirmation.revision,
        }
        self._invalidate_confirmation()  # consume before the transport await; never auto retry
        return arguments

    async def verified_result(self, turn: Turn, result: ActionResultEvent, request=None) -> dict:
        operation = result.payload.operation
        facts = result.payload.verified_state or {}
        if operation in {"search_menu", "filter_menu"}:
            self.browse.reset(self.snapshot.visible_items, self.snapshot.revision)
            if turn.sort_by:
                self.browse.rows.sort(
                    key=lambda row: row.name.casefold() if turn.sort_by == "name" else row.price,
                    reverse=turn.sort_by == "price_desc",
                )
                # Only presentation order changes; application prices/revision remain authoritative.
                facts = {
                    **facts,
                    "items": [row.model_dump(mode="json") for row in self.browse.rows],
                }
        elif operation == "get_current_context" and self.browse.revision != self.snapshot.revision:
            self.browse.reset(self.snapshot.visible_items, self.snapshot.revision)
        elif operation == "get_current_context" and not self.browse.rows:
            self.browse.reset(self.snapshot.visible_items, self.snapshot.revision)
        if operation == "get_item_details":
            self.details[facts["item_id"]] = facts
            if facts["item_id"] not in {row.item_id for row in self.browse.rows}:
                self.browse.rows.append(
                    VisibleItem.model_validate(
                        {key: facts[key] for key in VisibleItem.model_fields}
                    )
                )
            if len(self.details) > 8:
                del self.details[next(iter(self.details))]
        if operation == "select_item":
            self.references_stale = False
        if request is not None and operation.startswith("cart."):
            self.last_cart_item = request.payload.arguments.get("item_id")
            self.references_stale = False
        say = "The page is ready. What would you like to do next?"
        if "lines" in facts:
            # Exact checkout delivery may not silently fall back to an untranslated item name.
            if (
                self.language == "ur"
                and operation == "checkout.get_summary"
                and any(
                    re.search(r"[A-Za-z]", label(value, "ur"))
                    for value in [line["name"] for line in facts["lines"]]
                    + [fee["label"] for fee in facts["fees"]]
                )
            ):
                self._invalidate_confirmation()
                return safe_failure("not_available")
            say = cart_speech(
                facts, confirmation=operation == "checkout.get_summary", language=self.language
            )
        if operation == "checkout.get_summary":
            self._invalidate_confirmation()
            summary_id = self.summary_id = new_id()
            self.confirm_cart = cart_hash(self.snapshot.cart)
            self.confirmation.begin_awaiting(
                summary=facts,
                revision=facts["summary_revision"],
                summary_text=say,
                confirmation_token=result.payload.confirmation_token,
            )

            def delivered():
                if (
                    self.summary_id == summary_id
                    and self.authorized(turn)
                    and self.confirm_cart == cart_hash(self.snapshot.cart)
                ):
                    self.confirmation.mark_summary_delivered()

            if self.mode == "typed":
                if await self.adapter.present_summary(
                    turn_id=turn.id,
                    summary_id=summary_id,
                    text=say,
                    summary_revision=facts["summary_revision"],
                    summary_hash=self.confirmation.summary_hash or "",
                ):
                    delivered()
            else:
                # Queue a separate exact utterance. Awaiting it inside a tool would
                # deadlock SDK speech scheduling; its public done callback proves delivery.
                self.say(say, on_complete=delivered)
        elif operation == "checkout.submit_demo_order":
            say = "Your demo order was placed. No payment was taken."
        elif operation in {"get_item_details", "select_item"}:
            say = self.t(
                "{name} costs {price} rupees.", name=facts["name"], price=f"{facts['price']:g}"
            )
        elif operation in {"search_menu", "filter_menu"}:
            rows = self.browse.rows
            say = self.t("I found {count} options. ", count=facts["result_count"]) + list_speech(
                rows,
                language=self.language,
                read_all=turn.read_all,
            )
            if facts["result_count"] > len(rows):
                say += self.t(
                    " More matches exist beyond this view; "
                    "narrow the category or price to see them."
                )
            elif not turn.read_all and len(rows) > 3:
                say += self.t(" Say next for more options.")
        elif operation == "navigate":
            say = self.t("You’re on the {route} page.", route=facts["route"])
        elif operation == "get_current_context":
            say = SemanticPage(self.snapshot, self.details).speech(language=self.language)
        say = speech_text(say, self.language)
        # Bound model output from all adapters; never expose app tokens to the LLM.
        answer = {"status": "success", "facts": facts, "say": say}
        if len(json.dumps(answer, ensure_ascii=False).encode()) > 14000:
            return safe_failure("not_available")
        return answer

    def say(self, text: str, *, on_complete=None) -> Any:
        if (
            self.closed
            or self.mode not in {"voice", "typed", "choosing"}
            or self.paused
            or self.muted
        ):
            return None
        revision, epoch = self.snapshot.revision, self.epoch
        voice_deliverable = self.mode == "voice" and self._voice_output_available()
        text = shape_assistant_reply(
            text,
            known_item_ids={i.item_id for i in self.snapshot.visible_items},
            language=self.language,
        ).spoken_text
        handle = self.session.say(text, allow_interruptions=True)

        def done(speech):
            if (
                not self.closed
                and epoch == self.epoch
                and revision == self.snapshot.revision
                and not speech.interrupted
                and speech.exception() is None
            ):
                self.on_delivered(text, revision)
                if on_complete and voice_deliverable and self._voice_output_available():
                    on_complete()

        if handle.done():
            done(handle)
        else:
            handle.add_done_callback(done)
        return handle

    def _voice_output_available(self) -> bool:
        return bool(self.session.output.audio is not None and self.session.output.audio_enabled)

    def on_delivered(self, text: str, revision: int) -> None:
        if text.strip() and revision == self.snapshot.revision and not self.closed:
            if rows := self.browse.delivered(text, revision):
                self.references.set_list(
                    [PresentedItem(row.item_id, row.name, row.price) for row in rows],
                    revision=revision,
                )
                self.references_stale = False
            self._last_completed = (text, revision)
            self.reconciler.on_complete(text)
            del self.reconciler.chat_heard[:-32]
            self.idle.on_assistant_finished()

    def on_speech_created(self, event: Any) -> None:
        handle = event.speech_handle
        self.speeches[handle.id] = handle
        if event.source == "generate_reply" and self._generating_turn is not None:
            self.speech_turns[handle.id] = self._generating_turn
            self._generating_turn.speech = handle
        turn = self.speech_turns.get(handle.id) or self.active_turn
        self._captions[handle.id] = {
            "turn_id": turn.id if turn is not None else handle.id,
            "revision": self.snapshot.revision,
            "text": "",
        }
        self._caption(handle.id, "started")

        def completed(speech):
            self.speeches.pop(speech.id, None)
            turn = self.speech_turns.pop(speech.id, None)
            delivered = " ".join(
                item.text_content or ""
                for item in speech.chat_items
                if isinstance(item, llm.ChatMessage) and item.role == "assistant"
            )
            if speech.id in self._captions:
                self._captions[speech.id]["text"] = delivered[:2000]
                self._caption(
                    speech.id,
                    "interrupted"
                    if speech.interrupted or speech.exception() is not None
                    else "completed",
                )
                self._captions.pop(speech.id, None)
            if (
                turn
                and self.authorized(turn)
                and not speech.interrupted
                and speech.exception() is None
            ):
                text = " ".join(
                    item.text_content or ""
                    for item in speech.chat_items
                    if isinstance(item, llm.ChatMessage) and item.role == "assistant"
                )
                self.on_delivered(text, turn.revision)

        handle.add_done_callback(completed)

    def _publish(self, event_type: str, payload: dict, *, turn_id=None, revision=None) -> None:
        publisher = getattr(self.adapter, "publish_event", None)
        if publisher is None:
            return
        if len(self._output_tasks) >= 64 and payload.get("phase") in {"started", "updated"}:
            return

        async def send():
            try:
                await publisher(event_type, payload, turn_id=turn_id, revision=revision)
            except Exception:
                pass  # Output failure never alters a verified business result or delivery consent.

        task = asyncio.create_task(send())
        self._output_tasks.add(task)
        task.add_done_callback(self._output_tasks.discard)

    def _caption(self, speech_id: str, phase: str) -> None:
        caption = self._captions[speech_id]
        self._publish(
            "transcript.assistant",
            {
                "utterance_id": speech_id,
                "text": caption["text"],
                "phase": phase,
            },
            turn_id=caption["turn_id"],
            revision=caption["revision"],
        )

    def on_caption_fragment(self, speech_id: str, text: str) -> None:
        if speech_id not in self._captions or self.closed:
            return
        caption = self._captions[speech_id]
        caption["text"] = (caption["text"] + text)[:2000]
        self._caption(speech_id, "updated")

    def on_user_transcript(self, event: Any) -> None:
        if self.closed or self.mode not in {"voice", "choosing"}:
            return
        # This fallback is a product identity, never a provider confidence/timing claim.
        utterance = getattr(event, "item_id", None) or self._user_caption_id or new_id()
        self._user_caption_id = None if event.is_final else utterance
        self._publish(
            "transcript.user.final" if event.is_final else "transcript.user.partial",
            {
                "utterance_id": utterance,
                "text": event.transcript[:2000],
                "source": "speech",
            },
            turn_id=utterance,
            revision=self.snapshot.revision,
        )

    def on_user_state(self, event: Any) -> None:
        speaking = event.new_state == "speaking"
        if speaking and not self.closed:
            self.recovery.observe("user_speaking", assistant_speaking=self._agent_speaking)
        self._user_speaking = speaking
        self.idle.mark_user_busy(speaking or self._agent_speaking)
        if speaking and self.active_turn:
            # A new answer must not erase an already delivered summary. An
            # interruption *during* its delivery still invalidates it immediately.
            self.active_turn.committed = False
            if not self.confirmation.summary_spoken:
                self._invalidate_confirmation()
            self._interrupt()
        elif not speaking:
            self.idle.reset_after_activity()
            self.idle.mark_user_busy(self._agent_speaking)

    def on_agent_state(self, event: Any) -> None:
        state = {
            "initializing": "connecting",
            "listening": "ready/listening",
            "thinking": "thinking",
            "speaking": "assistant_speaking",
        }.get(event.new_state)
        if state and not self.closed:
            self._publish("agent.status", {"state": state}, revision=self.snapshot.revision)
        self._agent_speaking = event.new_state == "speaking"
        self.idle.mark_user_busy(self._agent_speaking or self._user_speaking)
        if event.new_state == "listening" and not self._user_speaking:
            self.idle.on_assistant_finished()

    async def poll_idle(self) -> str | None:
        if (
            self.closed
            or self.mode != "voice"
            or self.paused
            or self.muted
            or self.tips_paused
            or self.pending
            or self.speeches
            or self._user_speaking
            or self._agent_speaking
        ):
            return None
        tip = self.idle.poll(self.snapshot.route)
        if tip:
            self.say(tip)
        return tip

    async def _idle_loop(self) -> None:
        while not self.closed:
            await asyncio.sleep(0.25)
            if (
                self.mode == "choosing"
                and self._choice_deadline is not None
                and asyncio.get_running_loop().time() >= self._choice_deadline
                and not self._user_speaking
                and not self._agent_speaking
            ):
                await self.choice_timeout()
            await self.poll_idle()

    def on_room_event(self, event: Any) -> None:
        from foodease_contract.models import AppControlEvent, ContextEvent, TextInputEvent

        if self.closed:
            return
        if isinstance(event, ContextEvent):
            self.on_context(event.payload, source_turn=event.turn_id)
        else:
            # Clear/manual/end must revoke admission synchronously before an async task runs.
            if isinstance(event, AppControlEvent) and event.payload.intent == "end":
                self.end_local()
                return
            if self.gate is not None and not self._started:
                if len(self._before_start) >= 64:
                    self.end_local()
                else:
                    self._before_start.append(event)
                return
            if isinstance(event, AppControlEvent) and event.payload.intent in {
                "switch_mode",
                "pause",
                "mute",
                "resume",
                "unmute",
            }:
                if event.payload.mode == "voice" and self.recovery.speech_failed:
                    return
                # Revoke the old lane before scheduling control processing.
                self.epoch += 1
                if self.active_turn:
                    self.active_turn.discarded = True
                self._invalidate_confirmation()
                self._interrupt()
                if event.payload.intent == "switch_mode":
                    self.mode = event.payload.mode
                    self._set_audio()
            if (
                isinstance(event, AppControlEvent)
                and event.payload.intent == "switch_mode"
                and event.payload.mode == "manual"
            ):
                self.mode = "manual"
                self.end_local()
                return

            async def handle():
                if isinstance(event, AppControlEvent):
                    if event.payload.intent == "start" and event.payload.mode == "voice":
                        await self.open_mode_choice()
                    elif event.payload.intent in {"switch_mode", "resume"} and (
                        event.payload.mode in {"voice", "typed"}
                    ):
                        # Frozen Control fields express direct activation vs chooser/resume.
                        await self.activate_mode(
                            event.payload.mode, resuming=event.payload.intent == "resume"
                        )
                        if (
                            event.payload.intent == "switch_mode"
                            and not self.closed
                            and self.mode == event.payload.mode
                        ):
                            await self.adapter.publish_control("switch_mode", self.mode)
                        if event.payload.intent == "resume" and not self.closed and not self.paused:
                            self._publish(
                                "agent.control",
                                {"intent": "resume", "mode": self.mode},
                                turn_id=event.turn_id,
                            )
                    else:
                        await self.handle_control(event.payload.intent)
                elif isinstance(event, TextInputEvent):
                    await self.input_text(event.payload.text, event.turn_id, event.context_revision)

            task = asyncio.create_task(handle())
            self._background.add(task)
            task.add_done_callback(self._background.discard)

    def end_local(self) -> None:
        if self.closed:
            return
        self.closed = True
        self.epoch += 1
        self.idle.disable()
        self._invalidate_confirmation()
        self._interrupt()
        self._set_audio()
        if self._idle_task:
            self._idle_task.cancel()

    def on_session_close(self, event: Any) -> None:
        if not self.closed:
            self.end_local()
            self._publish("agent.control", {"intent": "end", "mode": None})

    async def drain(self) -> None:
        await self.broker.drain()

    async def close(self) -> None:
        self.end_local()
        if self.gate:
            self.gate.unsubscribe(self.on_room_event, self.end_local)
            for event, callback in self._room_handlers.items():
                self.gate.room.off(event, callback)
        if self._idle_task:
            with contextlib.suppress(asyncio.CancelledError):
                await self._idle_task
        for task in tuple(self._background):
            task.cancel()
        if self._background:
            await asyncio.gather(*self._background, return_exceptions=True)
        # Network adapters bound each RPC. Keep owned tasks even if shutdown exceeds
        # this drain window; never cancel or silently remove uncertain records.
        if self.broker.tasks:
            await asyncio.wait(tuple(self.broker.tasks), timeout=16)
        # These are read-only lookups; business submission tasks above stay owned.
        for task in tuple(self.broker.reconciliation_tasks):
            task.cancel()
        if self.broker.reconciliation_tasks:
            await asyncio.gather(*self.broker.reconciliation_tasks, return_exceptions=True)
        for event, callback in self._handlers.items():
            self.session.off(event, callback)
        if self._started:
            await self.session.aclose()
        if self._output_tasks:
            await asyncio.wait(tuple(self._output_tasks), timeout=1)
