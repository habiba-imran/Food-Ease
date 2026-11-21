"""Small streaming output gate: sanitize and refuse unverified outcome claims."""

from __future__ import annotations

import re
from collections.abc import AsyncIterable
from typing import Any

from livekit.agents import FlushSentinel, llm

from foodease_agent.speech_text.sanitizer import sanitize_assistant_text
from foodease_agent.speech_text.shaping import shape_assistant_reply

_OUTCOMES = (
    (r"(?:کارٹ|ٹوکری).{0,20}خالی\s*(?:کر\s*(?:دیا|دی)|ہو\s*گیا)", {"cart.clear"}),
    (
        r"(?:کھول|بند|دکھا)\s*(?:دیا|دی)|(?:لے|لائی)\s*(?:آئی|آیا|گئی)",
        {
            "navigate",
            "filter_menu",
            "search_menu",
            "select_item",
            "checkout.get_summary",
            "cart.get_clear_summary",
        },
    ),
    (r"\b(?:cleared|emptied) .{0,20}cart\b|\bcart .{0,20}(?:cleared|emptied)\b", {"cart.clear"}),
    (
        r"\b(?:opened|closed|navigated|scrolled)\b",
        {
            "navigate",
            "filter_menu",
            "search_menu",
            "select_item",
            "checkout.get_summary",
            "cart.get_clear_summary",
        },
    ),
    (r"ایڈ\s*کر\s*(?:دیا|دی|چکا|چکی)", {"cart.add_item"}),
    (r"(?:کارٹ|ٹوکری)\s*میں\s*(?:آ|آ)\s*(?:گیا|گئی|گئے)", {"cart.add_item"}),
    (r"آرڈر\s*(?:ہو\s*گیا|کر\s*دیا|دے\s*دیا)", {"checkout.submit_demo_order"}),
    (r"^\s*(?:(?:جی|اچھا)[،,\s]*)?ہو\s*گیا[!۔.\s]*$", set()),
    (r"شامل\s*کر\s*(?:دیا|دی|چکا|چکی)", {"cart.add_item"}),
    (r"(?:ہٹا|نکال|حذف)\s*(?:دیا|دی|کر\s*(?:دیا|دی))", {"cart.remove_item"}),
    (r"تعداد.{0,40}(?:بدل|تبدیل|کر دی|کر دیا)", {"cart.set_quantity"}),
    (r"آرڈر.{0,35}(?:درج\s*(?:ہو|کر\s*دیا)|مکمل ہو|تصدیق ہو)", {"checkout.submit_demo_order"}),
    (r"\b(?:added|put .+ (?:in|into) (?:your|the) cart)\b", {"cart.add_item"}),
    (r"\b(?:removed|deleted)\b", {"cart.remove_item"}),
    (r"\b(?:updated|changed|set) .{0,40}quantity\b", {"cart.set_quantity"}),
    (
        r"\b(?:order .{0,20}(?:placed|submitted|confirmed)|placed .{0,20}order)\b",
        {"checkout.submit_demo_order"},
    ),
    (r"^\s*(?:done|all set)[.!]?\s*$", set()),
)


def checked_sentence(runtime: Any, turn: Any, text: str) -> str:
    if turn is None or turn.control_done or not runtime.can_speak(turn):
        return ""
    text = sanitize_assistant_text(
        text,
        known_item_ids={row.item_id for row in runtime.snapshot.visible_items}
        | {row.item_id for row in runtime.snapshot.cart.lines},
    )
    witnesses = {
        result.payload.operation
        for result in runtime.broker.results.values()
        if result.turn_id == turn.id
        and result.context_revision == turn.revision
        and result.payload.status == "success"
    }
    for pattern, operations in _OUTCOMES:
        if re.search(pattern, text, re.I) and (
            not witnesses if not operations else not witnesses.intersection(operations)
        ):
            return shape_assistant_reply(
                "I haven’t verified that change yet. Please check the page.",
                language=runtime.language,
            ).spoken_text
    return shape_assistant_reply(text, language=runtime.language).spoken_text


async def guarded_output(source: AsyncIterable, runtime: Any, turn: Any):
    """Keep tool chunks streaming unchanged; bound sentence buffering for speech.

    This is an additional outcome/sanitization check, not a general natural-language
    fact verifier. Authoritative tool facts and the instruction boundary remain required.
    """
    buffered = ""
    scope_checked = False
    async for chunk in source:
        if isinstance(chunk, llm.ChatChunk):
            delta = chunk.delta
            if delta and delta.content:
                buffered += delta.content
                yield chunk.model_copy(update={"delta": delta.model_copy(update={"content": None})})
            else:
                yield chunk
        elif isinstance(chunk, str):
            buffered += chunk
        else:
            if buffered:
                yield checked_sentence(runtime, turn, buffered)
                buffered = ""
            yield chunk
        if not scope_checked and buffered:
            if match := re.match(r"^\s*<voice_scope:([a-z]+)>\s*", buffered):
                scope = match[1]
                if scope in {"general", "menu", "item", "cart", "view", "unknown"}:
                    runtime.manual.generated_scope(turn, scope)
                buffered = buffered[match.end():]
                scope_checked = True
            elif buffered.lstrip().startswith("<") and ">" not in buffered and len(buffered) < 80:
                continue  # private marker may span several provider chunks
            else:
                scope_checked = True  # missing/invalid metadata stays conservative
        while match := re.search(r"[.!?۔؟](?:\s|$)", buffered):
            sentence, buffered = buffered[: match.end()], buffered[match.end() :]
            if checked := checked_sentence(runtime, turn, sentence):
                yield checked + " "
                yield FlushSentinel()
        if len(buffered) > 1200:
            if checked := checked_sentence(runtime, turn, buffered[:1200]):
                yield checked + " "
            buffered = ""  # bounded pathological provider fragments
    if buffered.startswith("<voice_scope:"):
        return  # never speak an incomplete private marker
    if buffered and (checked := checked_sentence(runtime, turn, buffered)):
        yield checked
