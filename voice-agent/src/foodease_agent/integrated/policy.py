"""Provider-free policy reused by live tools and text-driven worker tests."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from foodease_contract.models import CartSummary

from foodease_agent.confirmation import ConfirmationMachine
from foodease_agent.i18n import label, render, speech_text


@dataclass
class Turn:
    id: str
    revision: int
    epoch: int
    source: str
    text: str
    committed: bool = True
    discarded: bool = False
    speech: Any = None
    blocked: bool = False
    steps: int = 0
    effects: set[str] = field(default_factory=set)
    read_all: bool = False
    control_done: bool = False


def explicit_yes(text: str) -> bool:
    # Deliberately finite: additions/corrections/"yesterday" are never consent.
    return text.strip().lower().rstrip(".!?۔؟").strip() in {
        "yes",
        "yes please",
        "yeah",
        "yep",
        "confirm",
        "confirmed",
        "place it",
        "place the order",
        "submit",
        "go ahead",
        "do it",
        "ہاں",
        "جی ہاں",
        "جی",
        "تصدیق کریں",
        "آرڈر درج کر دیں",
        "آرڈر کر دیں",
    }


def cart_hash(cart: CartSummary) -> str:
    return ConfirmationMachine.hash_summary(cart.model_dump(mode="json"))


def money(value: float, language: str = "en") -> str:
    return speech_text(f"{value:g} روپے", language) if language == "ur" else f"{value:g} rupees"


def cart_speech(facts: dict[str, Any], *, confirmation=False, language: str = "en") -> str:
    cart = CartSummary.model_validate({k: v for k, v in facts.items() if k != "summary_revision"})
    if not cart.lines:
        return render("Your cart is empty. You can choose something from the menu.", language)
    lines = "; ".join(
        f"{label(line.name, language)}، تعداد {line.quantity}، {money(line.line_total, language)}"
        if language == "ur"
        else f"{line.quantity} {line.name}, {money(line.line_total)}"
        for line in cart.lines
    )
    fees = "; ".join(
        f"{label(fee.label, language)}, {money(fee.amount, language)}" for fee in cart.fees
    )
    text = render("Your cart has {lines}. ", language, lines=lines)
    if fees:
        text += render("Fees: {fees}. ", language, fees=fees)
    text += render("The total is {total}.", language, total=money(cart.total, language))
    if confirmation:
        text += render(" Shall I place this demo order?", language)
    return speech_text(text, language)


def safe_failure(reason: str) -> dict[str, Any]:
    guidance = {
        "confirmation_required": "Please ask me to read your current order before confirming it.",
        "stale_context": "The page changed. Please tell me which item you mean now.",
        "inactive_turn": "That request is no longer active. Please ask again.",
        "invalid_arguments": "I need a valid item or quantity before I can do that.",
        "pending": "I’m still checking the previous request. I won’t send it again.",
        "step_blocked": (
            "I’ve stopped this request to avoid repeating or guessing a change. "
            "Please check the page and tell me what you’d like next."
        ),
        "timeout_unknown": (
            "I couldn’t verify the outcome. Please check the page before trying again."
        ),
        "not_available": "That option isn’t available right now.",
        "out_of_stock": "That item is sold out. Would you like to choose another?",
    }.get(reason, "I couldn’t verify that request. Please check the page.")
    return {"status": reason, "facts": None, "say": guidance}


def has_reference(text: str) -> bool:
    return bool(
        re.search(
            r"\b(first|second|third|fourth|fifth|cheaper|cheapest|other|that|this|it|"
            r"پہلا|دوسرا|تیسرا|چوتھا|پانچواں|پہلے|دوسرے|تیسرے|چوتھے|پانچویں|"
            r"یہ|وہ|اسے|اسی|سستا|سستی)\b",
            text,
            re.I,
        )
    )
