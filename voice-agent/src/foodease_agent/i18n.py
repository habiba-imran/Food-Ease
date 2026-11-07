"""Presentation translations, not shopping intent or synonym rules."""

from __future__ import annotations

import json
import re
from decimal import Decimal
from functools import lru_cache
from importlib.resources import files


@lru_cache
def urdu_resources() -> dict:
    return json.loads(
        files("foodease_agent").joinpath("locales/ur.json").read_text(encoding="utf-8")
    )


def label(text: str, language: str = "en") -> str:
    return urdu_resources()["labels"].get(text, text) if language == "ur" else text


def render(template: str, language: str = "en", **values) -> str:
    if language == "ur":
        template = urdu_resources()["messages"].get(template, template)
        values = {
            key: label(value, language) if isinstance(value, str) else value
            for key, value in values.items()
        }
    return template.format(**values) if values else template


_NUMBERS = (
    "صفر|ایک|دو|تین|چار|پانچ|چھ|سات|آٹھ|نو|دس|گیارہ|بارہ|تیرہ|چودہ|پندرہ|سولہ|سترہ|اٹھارہ|انیس|"
    "بیس|اکیس|بائیس|تئیس|چوبیس|پچیس|چھبیس|ستائیس|اٹھائیس|انتیس|تیس|اکتیس|بتیس|تینتیس|چونتیس|"
    "پینتیس|چھتیس|سینتیس|اڑتیس|انتالیس|چالیس|اکتالیس|بیالیس|تینتالیس|چوالیس|پینتالیس|چھیالیس|"
    "سینتالیس|اڑتالیس|انچاس|پچاس|اکیاون|باون|ترپن|چوّن|پچپن|چھپن|ستاون|اٹھاون|انسٹھ|ساٹھ|اکسٹھ|"
    "باسٹھ|تریسٹھ|چونسٹھ|پینسٹھ|چھیاسٹھ|سڑسٹھ|اڑسٹھ|انہتر|ستر|اکہتر|بہتر|تہتر|چوہتر|پچہتر|چھہتر|"
    "ستتر|اٹھہتر|اناسی|اسی|اکیاسی|بیاسی|تراسی|چوراسی|پچاسی|چھیاسی|ستاسی|اٹھاسی|نواسی|نوے|اکانوے|"
    "بانوے|ترانوے|چورانوے|پچانوے|چھیانوے|ستانوے|اٹھانوے|ننانوے"
).split("|")


def urdu_number(number: int) -> str:
    if number < 100:
        return _NUMBERS[number]
    for size, unit in ((10_000_000, "کروڑ"), (100_000, "لاکھ"), (1000, "ہزار"), (100, "سو")):
        if number >= size:
            head, rest = divmod(number, size)
            return urdu_number(head) + " " + unit + (" " + urdu_number(rest) if rest else "")
    raise ValueError("unsupported number")


def urdu_text(text: str) -> str:
    text = render(text, "ur")
    # Group separators are presentation, not a decimal or extra amount.
    text = re.sub(r"(?<=\d)[,٬](?=\d{3}(?:\D|$))", "", text)
    text = re.sub(r"\b(?:PKR|Rs\.?)\s*(\d+(?:\.\d{1,2})?)", r"\1 روپے", text, flags=re.I)
    text = re.sub(r"(\d+(?:\.\d{1,2})?)\s*\b(?:PKR|Rs\.?)\b", r"\1 روپے", text, flags=re.I)
    # Catalog translations are display labels. They never choose IDs or change filters.
    for original, translated in sorted(
        urdu_resources()["labels"].items(), key=lambda row: -len(row[0])
    ):
        text = re.sub(r"(?<!\w)" + re.escape(original) + r"(?!\w)", translated, text)

    def number(match: re.Match) -> str:
        value = Decimal(match[0])
        whole = urdu_number(int(value))
        fraction = match[0].partition(".")[2]
        return whole + (
            " اعشاریہ " + " ".join(_NUMBERS[int(digit)] for digit in fraction)
            if fraction and int(fraction)
            else ""
        )

    text = re.sub(r"(?<!\w)\d+(?:\.\d{1,2})?(?!\w)", number, text)
    return text


def speech_text(text: str, language: str = "en") -> str:
    if language != "ur":
        return text
    text = urdu_text(text)
    if re.search(r"[A-Za-z]", text):
        return "معاف کیجیے، بات واضح نہیں ہوئی۔ ایک بار پھر بتا دیں؟"
    return text
