"""V6.1 verbalizer (≥40 cases) and V6.5 parity / wait-feedback guards."""

from __future__ import annotations

import pytest

from foodease_agent.speech_text.chunking import chunk_for_speech, join_list_items
from foodease_agent.speech_text.delivery import DEFAULT_DELIVERY, cartesia_generation_config
from foodease_agent.speech_text.shaping import shape_assistant_reply
from foodease_agent.speech_text.verbalizer import (
    number_words,
    speak_pkr,
    speak_position,
    speak_quantity,
    speak_range_pkr,
    verbalize_text,
)
from foodease_agent.speech_text.wait_feedback import (
    WaitFeedbackGate,
    is_safe_wait_message,
    wait_feedback_line,
)

# --- V6.1: ≥40 cases ---

PKR_CASES: list[tuple[int | float, str]] = [
    (150, "one hundred fifty rupees"),
    (1500, "one thousand five hundred rupees"),
    (100, "one hundred rupees"),
    (1, "one rupee"),
    (2, "two rupees"),
    (20, "twenty rupees"),
    (21, "twenty one rupees"),
    (99, "ninety nine rupees"),
    (1000, "one thousand rupees"),
    (850, "eight hundred fifty rupees"),
    (600, "six hundred rupees"),
    (1200, "one thousand two hundred rupees"),
    (1800, "one thousand eight hundred rupees"),
    (50, "fifty rupees"),
    (80, "eighty rupees"),
    (250, "two hundred fifty rupees"),
    (999, "nine hundred ninety nine rupees"),
    (2000, "two thousand rupees"),
    (10_000, "ten thousand rupees"),
    (12_500, "twelve thousand five hundred rupees"),
    (7, "seven rupees"),
    (11, "eleven rupees"),
    (15, "fifteen rupees"),
    (30, "thirty rupees"),
    (45, "forty five rupees"),
    (350.5, "three hundred fifty point five zero rupees"),
    (350.05, "three hundred fifty point zero five rupees"),
    (220, "two hundred twenty rupees"),
    (280, "two hundred eighty rupees"),
    (320, "three hundred twenty rupees"),
    (420, "four hundred twenty rupees"),
    (480, "four hundred eighty rupees"),
    (550, "five hundred fifty rupees"),
    (650, "six hundred fifty rupees"),
    (700, "seven hundred rupees"),
    (750, "seven hundred fifty rupees"),
]


@pytest.mark.parametrize(("amount", "expected"), PKR_CASES)
def test_speak_pkr_cases(amount: int | float, expected: str) -> None:
    assert speak_pkr(amount) == expected


def test_no_ambiguous_one_fifty_style() -> None:
    # Must never produce the ambiguous short forms
    assert "one fifty" not in speak_pkr(150)
    assert "eight fifty" not in speak_pkr(850)
    assert speak_pkr(150) != speak_pkr(1500)


QTY_CASES = [
    (1, "one"),
    (2, "two"),
    (12, "twelve"),
    (21, "twenty one"),
    (100, "one hundred"),
]


@pytest.mark.parametrize(("n", "expected"), QTY_CASES)
def test_speak_quantity(n: int, expected: str) -> None:
    assert speak_quantity(n) == expected


def test_speak_range_and_position() -> None:
    assert speak_range_pkr(100, 150) == (
        "from one hundred rupees to one hundred fifty rupees"
    )
    assert speak_position(2, 4) == "the second of four"
    assert speak_position(1, 3) == "the first of three"
    assert number_words(0) == "zero"


def test_verbalize_text_rewrites_money_and_qty() -> None:
    out = verbalize_text("Total PKR 850 for 2 items")
    assert "eight hundred fifty rupees" in out
    assert "two items" in out
    assert "850" not in out


def test_v65_spoken_display_parity() -> None:
    forms = shape_assistant_reply("Your total is PKR 1500. The second of four is ready.")
    assert forms.spoken_text == forms.display_text
    assert "one thousand five hundred rupees" in forms.spoken_text
    assert "the second of four" in forms.spoken_text.lower() or "second" in forms.spoken_text


def test_chunking_first_sentence_preference() -> None:
    chunks = chunk_for_speech("Short lead. Then a longer follow-up sentence here.")
    assert chunks[0] == "Short lead."
    joined = join_list_items(["Zinger Burger", "Veggie Wrap"], lead_in="Two options")
    assert joined.startswith("Two options.")
    assert "Zinger Burger." in joined


def test_wait_feedback_no_success_wording() -> None:
    line = wait_feedback_line()
    assert is_safe_wait_message(line)
    assert not is_safe_wait_message("Done. Added to your cart.")
    assert not is_safe_wait_message("Order placed successfully.")
    gate = WaitFeedbackGate(threshold_s=1.5)
    assert gate.maybe_line(1.0) is None
    first = gate.maybe_line(1.5)
    assert first is not None
    assert gate.maybe_line(10.0) is None  # once only


def test_delivery_emotion_off_by_default() -> None:
    assert DEFAULT_DELIVERY.emotion_enabled is False
    assert cartesia_generation_config() == {}


def test_v61_case_count_at_least_40() -> None:
    # Parametrized PKR + qty + range/position + verbalize extras
    total = len(PKR_CASES) + len(QTY_CASES) + 4  # range, 2 positions, zero
    assert total >= 40
