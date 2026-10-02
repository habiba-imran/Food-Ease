"""Proactive greeting pool (VA-01) — pre-authored, interruptible, resume variant."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

GREETING_VARIANTS: tuple[str, ...] = (
    "Welcome. I can help you explore the menu and place a demo order. "
    "You can interrupt me, say go back, or browse normally. "
    "Would you like to browse categories or tell me what you feel like eating?",
    "Hi — I'm your FoodEase guide. Interrupt me anytime, or say stop to pause. "
    "Want to browse the menu, or describe what you're craving?",
    "Welcome back to voice help. I can navigate the menu and cart with you. "
    "Say a category, or ask what's popular — your call.",
)

RESUME_GREETING = (
    "Welcome back. Ready when you are — ask for the menu, an item, or your cart."
)

GENERIC_NO_CONTEXT = (
    "Welcome. I'm ready to help once the menu context arrives. "
    "You can interrupt me anytime."
)


@dataclass
class GreetingCache:
    """In-memory cache keyed by voice/settings hash (P1 say-with-audio)."""

    voice_id: str
    tts_model: str
    text_to_frames: dict[str, object] = field(default_factory=dict)

    def settings_key(self) -> str:
        raw = f"{self.tts_model}|{self.voice_id}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def invalidate_if_settings_changed(self, *, voice_id: str, tts_model: str) -> None:
        if voice_id != self.voice_id or tts_model != self.tts_model:
            self.voice_id = voice_id
            self.tts_model = tts_model
            self.text_to_frames.clear()

    def get(self, text: str) -> object | None:
        return self.text_to_frames.get(text)

    def put(self, text: str, audio: object) -> None:
        self.text_to_frames[text] = audio


@dataclass
class GreetingSelector:
    """Pick a short greeting; rotate variants so repeat testers hear variety."""

    variants: tuple[str, ...] = GREETING_VARIANTS
    resume_text: str = RESUME_GREETING
    generic_text: str = GENERIC_NO_CONTEXT
    _index: int = 0
    _session_had_voice: bool = False

    def mark_session_voice_active(self) -> None:
        self._session_had_voice = True

    def next_greeting(self, *, has_context: bool, resume: bool | None = None) -> str:
        if resume is None:
            resume = self._session_had_voice
        if resume:
            return self.resume_text
        if not has_context:
            return self.generic_text
        text = self.variants[self._index % len(self.variants)]
        self._index += 1
        return text
