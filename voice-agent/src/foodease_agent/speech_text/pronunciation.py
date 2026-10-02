"""Dish/brand pronunciation — respelling fallback when Cartesia dict unavailable."""

from __future__ import annotations

# Spoken respellings for TTS (Phase 6C). Keys are catalog display names.
PRONUNCIATION: dict[str, str] = {
    "Zinger Burger": "Zinger Burger",
    "Zinger Burger Supreme": "Zinger Burger Supreme",
    "Seekh Kabab Roll": "Seek Kabab Roll",
    "Paneer Roll": "Puh-neer Roll",
    "Chicken Karahi": "Chicken Ka-raa-hee",
    "Mutton Karahi": "Mutton Ka-raa-hee",
    "Chicken Biryani": "Chicken Bir-yah-nee",
    "Beef Biryani": "Beef Bir-yah-nee",
    "Sweet Lassi": "Sweet Lussee",
    "Karak Chai": "Ka-rak Chai",
    "Gulab Jamun (2pc)": "Gulab Ja-moon, two pieces",
    "Rice Kheer": "Rice Keer",
    "Masala Fries": "Ma-saa-la Fries",
    "Mint Raita": "Mint Rye-ta",
}


def pronounce_name(name: str) -> str:
    return PRONUNCIATION.get(name, name)


def apply_pronunciations(text: str) -> str:
    out = text
    # Longer names first to avoid partial replacements
    for display, spoken in sorted(PRONUNCIATION.items(), key=lambda kv: -len(kv[0])):
        out = out.replace(display, spoken)
    return out
