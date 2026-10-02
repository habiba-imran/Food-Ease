"""Sentence chunking for early TTS start and list pacing."""

from __future__ import annotations

import re


def chunk_for_speech(text: str, *, max_first_chars: int = 80) -> list[str]:
    """Split into sentences; keep the first chunk short when possible."""
    cleaned = re.sub(r"\s+", " ", text.strip())
    if not cleaned:
        return []
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", cleaned) if p.strip()]
    if not parts:
        return [cleaned]
    first = parts[0]
    if len(first) > max_first_chars and "," in first:
        # Prefer early pause after a clause in a long first sentence
        left, right = first.split(",", 1)
        return [left.strip() + ".", right.strip()] + parts[1:]
    return parts


def join_list_items(items: list[str], *, lead_in: str | None = None) -> str:
    """One list item per sentence for natural TTS pauses."""
    sentences: list[str] = []
    if lead_in:
        sentences.append(lead_in.rstrip(".") + ".")
    for _i, item in enumerate(items, start=1):
        body = item.rstrip(".")
        sentences.append(f"{body}.")
    return " ".join(sentences)
