"""Session-only preferences."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SessionPreferences:
    vegetarian: bool | None = None
    budget_pkr: float | None = None
    detail_level: str = "normal"  # brief | normal | more
    browsing_self: bool = False
    ended: bool = False
    extra: dict[str, str] = field(default_factory=dict)

    def clear(self) -> None:
        self.vegetarian = None
        self.budget_pkr = None
        self.detail_level = "normal"
        self.extra.clear()
