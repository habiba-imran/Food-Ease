"""Reference resolution for 'the second one', etc."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PresentedItem:
    item_id: str
    name: str
    price: float


@dataclass
class ReferenceResolver:
    items: list[PresentedItem] = field(default_factory=list)
    revision: int | None = None

    def set_list(self, items: list[PresentedItem], *, revision: int) -> None:
        self.items = list(items)
        self.revision = revision

    def clear(self) -> None:
        self.items = []
        self.revision = None

    def resolve(self, utterance: str, *, current_revision: int) -> PresentedItem | str | None:
        """Return item, clarification string, or None if not a reference."""
        text = utterance.strip().lower()
        if self.revision is not None and current_revision != self.revision:
            if any(p in text for p in ("second", "first", "third", "cheaper", "other", "that one", "that")):
                return "clarify: that list is out of date — ask which item by name"
        if not self.items:
            return None

        if "second" in text and len(self.items) >= 2:
            return self.items[1]
        if "first" in text and self.items:
            return self.items[0]
        if "third" in text and len(self.items) >= 3:
            return self.items[2]
        if "cheaper" in text or "cheapest" in text:
            return min(self.items, key=lambda i: i.price)
        if "other" in text and len(self.items) == 2:
            return self.items[1]
        if text in {"that", "that one"} and len(self.items) == 1:
            return self.items[0]
        if text in {"that", "that one"} and len(self.items) > 1:
            return "clarify: which one — name two options"
        return None
