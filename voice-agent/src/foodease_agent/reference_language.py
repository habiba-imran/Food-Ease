"""Conservative reference validation, never conversation intent routing."""

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
    return " ".join(words.get(word, word) for word in normalize(text).split())
