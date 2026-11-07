"""Sanitize assistant text — never leak IDs, URLs, JSON, internal status names."""

from __future__ import annotations

import re

_STATUS_NAMES = re.compile(
    r"\b(success|failed|rejected|stale_context|requires_confirmation|timeout_unknown|"
    r"action_id|context_revision|schema_version)\b",
    re.I,
)
_URL = re.compile(r"https?://\S+|www\.\S+", re.I)
_ITEM_ID = re.compile(r"\b[a-z][a-z0-9_\-]{2,63}\b")  # coarse; allowlist known phrases
_JSONISH = re.compile(r"[{}\[\]]")

# Words that look like IDs but are fine in speech
_ALLOW = {
    "pkr",
    "cart",
    "menu",
    "home",
    "back",
    "wrap",
    "burger",
    "spicy",
    "total",
    "order",
    "demo",
    "rupees",
    "rupee",
}


def sanitize_assistant_text(text: str, *, known_item_ids: set[str] | None = None) -> str:
    # Director/SSML instructions are internal, never pronounce their attributes.
    out = re.sub(
        r"<(?:[^>]+)>|\[(?:warm|calm|happy|sad|laugh(?:ter)?|pause|emotion[^\]]*)\]",
        "",
        text,
        flags=re.I,
    )
    out = re.sub(r"[*`#]+", "", out)
    out = _URL.sub("", out)
    out = _STATUS_NAMES.sub("", out)
    out = _JSONISH.sub("", out)
    if known_item_ids:
        for iid in known_item_ids:
            out = out.replace(iid, "")
    # Drop bare snake-case tokens that look like ids
    tokens = []
    for tok in out.split():
        low = tok.lower().strip(".,!?")
        if low in _ALLOW:
            tokens.append(tok)
        elif "_" in low and re.fullmatch(r"[a-z0-9_\-]+", low):
            continue
        else:
            tokens.append(tok)
    return re.sub(r"\s+", " ", " ".join(tokens)).strip()


def count_sentences(text: str) -> int:
    parts = re.split(r"[.!?]+", text.strip())
    return len([p for p in parts if p.strip()])
