"""Dual forms: spoken_text (TTS) and display_text (captions) — VA-08 / V6.5."""

from __future__ import annotations

from dataclasses import dataclass

from foodease_agent.i18n import speech_text
from foodease_agent.speech_text.chunking import chunk_for_speech
from foodease_agent.speech_text.pronunciation import apply_pronunciations
from foodease_agent.speech_text.sanitizer import sanitize_assistant_text
from foodease_agent.speech_text.verbalizer import verbalize_text


@dataclass(frozen=True)
class SpeechForms:
    spoken_text: str
    display_text: str
    chunks: tuple[str, ...]


def shape_assistant_reply(
    text: str,
    *,
    known_item_ids: set[str] | None = None,
    language: str = "en",
) -> SpeechForms:
    """Sanitizer → verbalizer → pronunciation → chunks.

    ``display_text`` is the readable written form of the **same words/numbers**
    as ``spoken_text`` (respellings kept identical so captions match TTS).
    """
    clean = sanitize_assistant_text(text, known_item_ids=known_item_ids)
    spoken = (
        speech_text(clean, language)
        if language == "ur"
        else (apply_pronunciations(verbalize_text(clean)))
    )
    chunks = tuple(chunk_for_speech(spoken))
    spoken_joined = " ".join(chunks) if chunks else spoken
    # Same words and numbers (V6.5) — captions use the spoken wording.
    display = spoken_joined
    return SpeechForms(
        spoken_text=spoken_joined,
        display_text=display,
        chunks=chunks,
    )
