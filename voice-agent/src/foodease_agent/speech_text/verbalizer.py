"""Speak PKR amounts, quantities, and positions unambiguously (V6.1)."""

from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal

_ONES = (
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
)
_TENS = (
    "",
    "",
    "twenty",
    "thirty",
    "forty",
    "fifty",
    "sixty",
    "seventy",
    "eighty",
    "ninety",
)
_ORDINAL = {
    1: "first",
    2: "second",
    3: "third",
    4: "fourth",
    5: "fifth",
    6: "sixth",
    7: "seventh",
    8: "eighth",
    9: "ninth",
    10: "tenth",
    11: "eleventh",
    12: "twelfth",
}


def _under_100(n: int) -> str:
    if n < 20:
        return _ONES[n]
    tens, ones = divmod(n, 10)
    if ones == 0:
        return _TENS[tens]
    return f"{_TENS[tens]} {_ONES[ones]}"


def _under_1000(n: int) -> str:
    if n < 100:
        return _under_100(n)
    hundreds, rest = divmod(n, 100)
    head = f"{_ONES[hundreds]} hundred"
    if rest == 0:
        return head
    return f"{head} {_under_100(rest)}"


def number_words(n: int) -> str:
    """Integer to unambiguous English words (no 'one fifty' style)."""
    if n < 0:
        return "minus " + number_words(-n)
    if n < 1000:
        return _under_1000(n)
    if n < 100_000:
        thousands, rest = divmod(n, 1000)
        head = f"{_under_1000(thousands)} thousand"
        if rest == 0:
            return head
        return f"{head} {_under_1000(rest)}"
    # Large but still demo-safe
    return number_words(n // 1000) + " thousand " + (
        number_words(n % 1000) if n % 1000 else ""
    ).strip()


def speak_quantity(n: int | float) -> str:
    if isinstance(n, float) and not n.is_integer():
        # Speak one decimal place max for demo quantities
        whole = int(n)
        tenths = int(round((n - whole) * 10))
        return f"{number_words(whole)} point {number_words(tenths)}"
    return number_words(int(n))


def speak_pkr(amount: int | float | Decimal | str) -> str:
    """Always end with 'rupees'. Never 'eight fifty' or 'one fifty'."""
    d = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    whole = int(d)
    cents = int((d - whole) * 100)
    if cents == 0:
        words = number_words(whole)
    else:
        # Read both fractional digits: .05 must never become .5 in speech.
        fraction = " ".join(_ONES[int(digit)] for digit in f"{cents:02d}")
        words = f"{number_words(whole)} point {fraction}"
    unit = "rupee" if whole == 1 and cents == 0 else "rupees"
    return f"{words} {unit}"


def speak_range_pkr(low: int | float, high: int | float) -> str:
    return f"from {speak_pkr(low)} to {speak_pkr(high)}"


def speak_position(index: int, total: int) -> str:
    """1-based index → 'the second of four'."""
    if index < 1 or total < 1 or index > total:
        raise ValueError(f"invalid position {index} of {total}")
    ord_word = _ORDINAL.get(index, f"{number_words(index)}th")
    return f"the {ord_word} of {number_words(total)}"


_NUM = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
_PKR_NUM = re.compile(
    rf"(?<!\w)(?:(?P<pre>PKR|Rs\.?)\s*(?P<num>{_NUM})"
    rf"|(?P<num2>{_NUM})\s*(?P<suf>PKR|Rs\.?|rupees?))(?!\w)",
    re.I,
)
_QTY = re.compile(r"\b(?P<n>\d+)\s+(?P<unit>items?|pieces?|pcs?)\b", re.I)


def verbalize_text(text: str) -> str:
    """Replace currency amounts and explicit quantities with spoken forms."""

    def money(m: re.Match[str]) -> str:
        raw = (m.group("num") or m.group("num2") or "").replace(",", "")
        return speak_pkr(raw)

    out = _PKR_NUM.sub(money, text)

    def qty(m: re.Match[str]) -> str:
        n = int(m.group("n"))
        unit = m.group("unit").lower()
        if unit.startswith("pc"):
            unit = "pieces" if n != 1 else "piece"
        elif unit.startswith("item"):
            unit = "items" if n != 1 else "item"
        elif unit.startswith("piece"):
            unit = "pieces" if n != 1 else "piece"
        return f"{speak_quantity(n)} {unit}"

    out = _QTY.sub(qty, out)
    return re.sub(r"\s+", " ", out).strip()
