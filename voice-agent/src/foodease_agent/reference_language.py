"""Conservative reference validation, never conversation intent routing."""

import re

_ORDINALS = {
    "پہلا": "first",
    "دوسرا": "second",
    "تیسرا": "third",
    "چوتھا": "fourth",
    "پانچواں": "fifth",
}


def normalize(text: str) -> str:
    return " ".join(text.strip().split()).rstrip(".!?۔؟")


def reference_text(text: str) -> str:
    words = {
        "pehla": "first",
        "pehle": "first",
        "pehli": "first",
        "doosra": "second",
        "dusra": "second",
        "doosri": "second",
        "teesra": "third",
        "tisra": "third",
        "chotha": "fourth",
        "chautha": "fourth",
        "paanchwa": "fifth",
        "woh": "that",
        "wo": "that",
        "yeh": "this",
        "ye": "this",
        "isko": "it",
        "usko": "it",
        "uske": "it",
        "iske": "it",
        "اس": "it",
        "اسکو": "it",
        "اسکے": "it",
        **_ORDINALS,
        "پہلے": "first",
        "دوسرے": "second",
        "تیسرے": "third",
        "چوتھے": "fourth",
        "پانچویں": "fifth",
        "یہ": "this",
        "وہ": "that",
        "اسے": "it",
        "اسی": "that",
        "سستا": "cheapest",
        "سستی": "cheapest",
    }
    tokens = re.sub(r"[^\w\s]", " ", normalize(text).lower()).split()
    return " ".join(words.get(word, word) for word in tokens)
