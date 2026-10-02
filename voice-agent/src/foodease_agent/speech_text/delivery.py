"""Cartesia delivery profile — emotion off by default (6C.2)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeliveryProfile:
    """Phase 6 starts with default context-driven delivery + punctuation pauses."""

    emotion_enabled: bool = False
    emotion_welcome: str | None = None
    emotion_apology: str | None = None
    # Listening panel (6E) may flip these via ADR later.
    pace_bias: str = "default"  # default | slightly_slower


DEFAULT_DELIVERY = DeliveryProfile()


def cartesia_generation_config(profile: DeliveryProfile = DEFAULT_DELIVERY) -> dict:
    """Build optional Cartesia generation_config. Empty when emotion is off."""
    if not profile.emotion_enabled:
        return {}
    # Valid emotion values depend on Cartesia docs for the pinned model — unused until 6E.
    cfg: dict = {}
    if profile.emotion_welcome:
        cfg["emotion"] = profile.emotion_welcome
    return cfg
