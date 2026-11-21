"""Cooperate with authenticated manual state changes; never reauthorize old tools."""

from __future__ import annotations

import asyncio
import re
from typing import Any

from livekit.agents import FlushSentinel

from foodease_agent.i18n import label
from foodease_agent.integrated.policy import cart_hash, cart_speech


def operation_scope(operation: str) -> str:
    if operation.startswith("cart.") or operation == "get_cart":
        return "cart"
    if operation.startswith("checkout."):
        return "review"
    if operation in {"filter_menu", "search_menu"}:
        return "menu"
    if operation in {"get_item_details", "select_item"}:
        return "item"
    return "unknown"


async def sentence_segments(text: str, handle: Any):
    # Public SDK FlushSentinel provides real independent playout boundaries.
    # Punctuation here segments already-authored speech, never user intent.
    for sentence in re.split(r"(?<=[.!?۔؟])\s+", text.strip()):
        if handle.interrupted:
            return
        if sentence:
            yield sentence + " "
            yield FlushSentinel()


class ManualCoexistence:
    def __init__(self, runtime: Any):
        self.runtime = runtime
        self.scopes: dict[str, str] = {}
        self.output_turns: set[str] = set()
        self.stopped: set[str] = set()
        self.boundary_handles: set[str] = set()
        self.audio = None
        self.sequence = 0
        self.pending: tuple | None = None
        self.following: tuple | None = None
        self.quiet = asyncio.Event()
        self.quiet.set()

    def bind(self, handle: Any, scope: str) -> None:
        self.scopes[handle.id] = scope
        audio = self.runtime.session.output.audio
        if audio is not self.audio and hasattr(audio, "on"):
            if self.audio is not None:
                self.audio.off("playback_finished", self.on_boundary)
            self.audio = audio
            audio.on("playback_finished", self.on_boundary)

    def generated_scope(self, turn: Any, scope: str) -> None:
        if turn is None or turn.speech is None:
            return
        # The model describes its reply's meaning, never its action permissions.
        # Actual cart/review receipts override an optimistic metadata label.
        if any(
            result.turn_id == turn.id
            and result.payload.status == "success"
            and (
                result.payload.operation == "get_cart"
                or result.payload.operation.startswith(("cart.", "checkout."))
            )
            for result in self.runtime.broker.results.values()
        ):
            scope = "cart" if scope == "cart" else "unknown"
        self.scopes[turn.speech.id] = scope

    def cancel(self) -> None:
        self.sequence += 1
        self.pending = None
        self.following = None
        self.boundary_handles.clear()
        self.output_turns.clear()
        # A stopped parent can still own an independent say() in this turn.
        # Keep those identities until its old handles finish, bounded per session.
        if len(self.stopped) > 256:
            self.stopped.intersection_update(self.runtime.speeches)

    def user_changed(self, speaking: bool) -> None:
        if speaking:
            self.quiet.clear()
        else:
            self.quiet.set()

    def stop_handle(self, handle: Any) -> None:
        if not handle.done():
            self.stopped.add(handle.id)
            handle.interrupt(force=True)

    def changed(self, before: Any, after: Any, *, review_was_active: bool) -> None:
        runtime = self.runtime
        owner = runtime.active_turn
        if owner is not None:
            owner.effects_revoked = True
            self.output_turns.add(owner.id)
        handles = [s for s in runtime.speeches.values() if not s.done()]
        view = any(
            getattr(before, k) != getattr(after, k)
            for k in (
                "route",
                "focus_item_id",
                "category",
                "search_query",
                "filter_tags",
                "max_price_pkr",
            )
        )
        cart = cart_hash(before.cart) != cart_hash(after.cart)
        old_rows = {r.item_id: r for r in before.visible_items}
        facts = any(r.item_id in old_rows and r != old_rows[r.item_id] for r in after.visible_items)
        reason = None
        affected = []
        for handle in handles:
            scope = self.scopes.get(handle.id, "unknown")
            if cart and scope in {"cart", "review", "unknown"} or facts and scope != "general":
                self.stop_handle(handle)
                affected.append(handle)
                reason = "cart" if cart else "view"
            elif view:
                affected.append(handle)
                reason = reason or "view"
                if self.audio is not None:
                    self.boundary_handles.add(handle.id)
                else:
                    # Text-only sinks have no audible sentence to finish.
                    self.stop_handle(handle)
        if reason is None:
            prior = self.pending or self.following
            if prior is not None:
                self.sequence += 1
                self.pending = (
                    self.sequence,
                    after.revision,
                    runtime.epoch,
                    owner,
                    "view" if view else prior[4],
                    prior[5] or review_was_active,
                    prior[6],
                )
                if not self.boundary_handles:
                    self.kick()
            return
        self.sequence += 1
        self.pending = (
            self.sequence,
            after.revision,
            runtime.epoch,
            owner,
            reason,
            review_was_active,
            affected,
        )
        if not self.boundary_handles:
            self.kick()

    def on_boundary(self, event: Any) -> None:
        if event.interrupted or not self.boundary_handles:
            return
        ids, self.boundary_handles = self.boundary_handles, set()
        for speech_id in ids:
            if handle := self.runtime.speeches.get(speech_id):
                self.stop_handle(handle)
        self.kick()

    def completed(self, handle: Any, owner: Any) -> None:
        self.scopes.pop(handle.id, None)
        if handle.interrupted and handle.id not in self.stopped:
            if owner is self.runtime.active_turn:
                self.cancel()
            return
        self.boundary_handles.discard(handle.id)
        if self.pending and not self.boundary_handles:
            self.kick()

    def kick(self) -> None:
        if self.pending is None:
            return
        pending, self.pending = self.pending, None
        self.following = pending
        task = asyncio.create_task(self.follow(pending))
        self.runtime._background.add(task)

        def finished(done):
            self.runtime._background.discard(done)
            if self.following is pending:
                self.following = None

        task.add_done_callback(finished)

    async def follow(self, pending: tuple) -> None:
        sequence, revision, epoch, owner, reason, review, handles = pending
        runtime = self.runtime

        def valid():
            return (
                sequence == self.sequence
                and epoch == runtime.epoch
                and runtime.active_turn is owner
                and not runtime.closed
                and not runtime.paused
                and not runtime.muted
                and not runtime._user_speaking
                and runtime.mode in {"voice", "typed"}
                and runtime.snapshot.revision == revision
            )

        for handle in handles:
            await handle.wait_for_playout()
        await self.quiet.wait()
        if not valid():
            return
        try:
            # This is only an authority read, never a synthetic user command or
            # a replay of the manual write. The adapter verifies its correlation.
            fresh = await runtime.adapter.get_snapshot()
        except Exception:
            if valid():
                runtime.say(
                    "میں حاضر ہوں۔ آپ کیا دیکھنا چاہیں گے؟"
                    if runtime.language == "ur" else "I'm here. What would you like to see?",
                    detached=True,
                )
            return
        if not valid() or fresh.revision != revision:
            return
        if self.following is pending:
            self.following = None
        if reason == "cart":
            text = cart_speech(fresh.cart.model_dump(mode="json"), language=runtime.language)
            if review:
                text += (
                    " تصدیق سے پہلے کارٹ کا نیا جائزہ سننا ضروری ہے۔"
                    if runtime.language == "ur"
                    else " A new cart review is needed before confirmation."
                )
            scope = "cart"
        else:
            if fresh.route == "menu" and fresh.category:
                name = label(fresh.category, runtime.language)
                text = (
                    f"اب {name} کا حصہ کھلا ہے۔"
                    if runtime.language == "ur"
                    else f"The {name} section is open."
                )
            elif fresh.route == "item":
                text = (
                    "آپ کھانے کی تفصیل دیکھ رہے ہیں۔"
                    if runtime.language == "ur"
                    else "The item details are open."
                )
            elif fresh.route == "cart":
                text = "آپ کا کارٹ کھلا ہے۔" if runtime.language == "ur" else "Your cart is open."
            else:
                text = (
                    "میں آپ کے موجودہ صفحے کے مطابق مدد جاری رکھوں گی۔"
                    if runtime.language == "ur"
                    else "I'll follow the page you have open."
                )
            scope = "view"
        runtime.say(text, scope=scope, detached=True)

    def close(self) -> None:
        self.cancel()
        if self.audio is not None:
            self.audio.off("playback_finished", self.on_boundary)
            self.audio = None
