"""Idle tips (VA-02) — never acts, never loops, cancelled by activity."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Protocol


class IdleStage(IntEnum):
    WAITING_FIRST = 0
    WAITING_SECOND = 1
    QUIET = 2


class Clock(Protocol):
    def monotonic(self) -> float: ...


@dataclass
class SystemClock:
    def monotonic(self) -> float:
        import time

        return time.monotonic()


@dataclass
class FakeClock:
    """Deterministic clock for unit tests."""

    now: float = 0.0

    def monotonic(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@dataclass
class IdlePromptController:
    """Schedules at most two contextual tips, then stays quiet.

    Tips never mutate the app. Any cancel signal resets or clears pending tips.
    """

    idle_1_seconds: float = 12.0
    idle_2_seconds: float = 30.0
    clock: Clock = field(default_factory=SystemClock)
    stage: IdleStage = IdleStage.WAITING_FIRST
    _anchor: float | None = None
    _muted: bool = False
    _user_busy: bool = False
    _enabled: bool = True

    def reset_after_activity(self) -> None:
        """Call on user speech, typed input, GUI event, control, disconnect."""
        if self.stage != IdleStage.QUIET:
            self.stage = IdleStage.WAITING_FIRST
        self._anchor = self.clock.monotonic()
        self._user_busy = False

    def mark_user_busy(self, busy: bool = True) -> None:
        self._user_busy = busy
        if busy:
            self._anchor = self.clock.monotonic()

    def set_muted(self, muted: bool) -> None:
        self._muted = muted
        if muted:
            self._anchor = None

    def disable(self) -> None:
        self._enabled = False
        self.stage = IdleStage.QUIET
        self._anchor = None

    def on_assistant_finished(self) -> None:
        """Start idle timers after the agent finishes speaking (post-greeting)."""
        if not self._enabled or self.stage == IdleStage.QUIET:
            return
        self._anchor = self.clock.monotonic()

    def tip_for_context(self, page_kind: str, *, which: int) -> str:
        page = (page_kind or "menu").lower()
        if which == 1:
            if page in {"item", "item_detail", "product"}:
                return "You can ask for ingredients, the price, or to add this to your cart."
            if page in {"cart", "checkout"}:
                return "You can ask me to read your cart, change a quantity, or check out."
            return "You can say a category like burgers, or tell me what you feel like eating."
        # second tip — different wording
        if page in {"item", "item_detail", "product"}:
            return "Or say go back if you want to keep browsing."
        if page in {"cart", "checkout"}:
            return "Say stop anytime if you want me to stay quiet."
        return "You can also filter by vegetarian or a budget if that helps."

    def poll(self, page_kind: str = "menu") -> str | None:
        """Return a tip to speak, or None. Never returns after QUIET."""
        if not self._enabled or self._muted or self._user_busy:
            return None
        if self.stage == IdleStage.QUIET:
            return None
        if self._anchor is None:
            return None

        elapsed = self.clock.monotonic() - self._anchor
        if self.stage == IdleStage.WAITING_FIRST and elapsed >= self.idle_1_seconds:
            tip = self.tip_for_context(page_kind, which=1)
            self.stage = IdleStage.WAITING_SECOND
            self._anchor = self.clock.monotonic()
            return tip
        if self.stage == IdleStage.WAITING_SECOND and elapsed >= self.idle_2_seconds:
            tip = self.tip_for_context(page_kind, which=2)
            self.stage = IdleStage.QUIET
            self._anchor = None
            return tip
        return None


SpeakFn = Callable[[str], None]
