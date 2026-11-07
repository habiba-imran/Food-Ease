"""Bounded semantic page and delivered-list memory; no shopping intent planner."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from foodease_contract.models import ContextSnapshot, VisibleItem

from foodease_agent.i18n import label, render
from foodease_agent.reference_language import reference_text
from foodease_agent.speech_text.pronunciation import apply_pronunciations


def heard_items(text: str, rows: list[VisibleItem]) -> list[VisibleItem]:
    """Match complete product names in actual completed output, in delivered order."""
    matches = []
    for row in rows:
        for name in {row.name, apply_pronunciations(row.name), label(row.name, "ur")}:
            for match in re.finditer(r"(?<!\w)" + re.escape(name) + r"(?!\w)", text, re.I):
                matches.append((match.start(), match.end(), row))
    matches.sort(key=lambda item: (item[0], -(item[1] - item[0])))
    result, occupied = [], []
    for start, end, row in matches:
        if not any(start < right and end > left for left, right in occupied) and (
            row.item_id not in {item.item_id for item in result}
        ):
            result.append(row)
            occupied.append((start, end))
    return result


@dataclass
class BrowseMemory:
    rows: list[VisibleItem] = field(default_factory=list)
    pages: list[list[str]] = field(default_factory=list)
    index: int = -1
    revision: int = -1

    def reset(self, rows: list[VisibleItem], revision: int) -> None:
        self.rows, self.pages, self.index, self.revision = list(rows), [], -1, revision

    def delivered(self, text: str, revision: int) -> list[VisibleItem]:
        if revision != self.revision:
            return []
        rows = heard_items(text, self.rows)
        if rows:
            ids = [row.item_id for row in rows]
            if ids in self.pages:
                self.index = self.pages.index(ids)
            else:
                self.pages = self.pages[: self.index + 1] + [ids]
                self.index = len(self.pages) - 1
        return rows

    def window(self, direction: str) -> list[VisibleItem]:
        if direction == "previous":
            if self.index < 1:
                return []
            ids = self.pages[self.index - 1]
            return [next(row for row in self.rows if row.item_id == item) for item in ids]
        used = {item for page in self.pages[: self.index + 1] for item in page}
        return [row for row in self.rows if row.item_id not in used][:3]


@dataclass
class SemanticPage:
    snapshot: ContextSnapshot
    details: dict = field(default_factory=dict)

    def data(self) -> dict:
        state = self.snapshot
        focused = next(
            (
                row.model_dump(mode="json")
                for row in state.visible_items
                if row.item_id == state.focus_item_id
            ),
            None,
        )
        if state.focus_item_id in self.details:
            focused = self.details[state.focus_item_id]
        buttons = ["browse menu", "read cart"]
        if focused:
            buttons += ["read item details"]
            if focused.get("available"):
                buttons += ["add to cart"]
        if state.checkout_available:
            buttons += ["checkout"]
        return {
            "location": state.route,
            "selection": focused,
            "buttons": buttons,
            "navigation": state.valid_navigation_targets,
            "filters": {
                "tags": state.filter_tags,
                "category": state.category,
                "budget_pkr": state.max_price_pkr,
                "search": state.search_query,
            },
            "visible_count": len(state.visible_items),
            "results": [row.model_dump(mode="json") for row in state.visible_items[:3]],
            "cart": state.cart.model_dump(mode="json"),
            "details": self.details,
            "note": "Visible count is bounded; it is not the whole catalog count.",
        }

    def speech(self, *, language: str = "en") -> str:
        data = self.data()
        if language == "ur":
            text = render("You’re on the {route} page.", language, route=data["location"]) + " "
            if selected := data["selection"]:
                text += render(
                    "{name} costs {price} rupees.",
                    language,
                    name=selected["name"],
                    price=f"{selected['price']:g}",
                )
            elif self.snapshot.route in {"cart", "checkout"}:
                from foodease_agent.integrated.policy import cart_speech

                text += cart_speech(data["cart"], language=language)
            else:
                text += list_speech(self.snapshot.visible_items[:3], language=language)
            if self.snapshot.max_price_pkr is not None:
                text += f" قیمت کی حد {self.snapshot.max_price_pkr:g} روپے ہے۔"
            if self.snapshot.category:
                text += " منتخب قسم: " + label(self.snapshot.category, language) + "۔"
            if self.snapshot.filter_tags:
                text += " آپ کی غذائی ترجیحات لاگو ہیں۔"
            return text + " آپ کھانے دیکھ سکتے ہیں یا ٹوکری سن سکتے ہیں۔"
        text = f"You’re on the {data['location']} page. "
        if selected := data["selection"]:
            text += f"{selected['name']} is selected, at {selected['price']:g} rupees. "
        elif self.snapshot.route in {"home", "menu", "categories"}:
            text += list_speech(self.snapshot.visible_items[:3]) + " "
        elif self.snapshot.route in {"cart", "checkout"}:
            count = sum(row.quantity for row in self.snapshot.cart.lines)
            text += (
                f"Your cart has {count} items. "
                f"The total including fees is {self.snapshot.cart.total:g} rupees. "
            )
        filters = data["filters"]
        active = list(filters["tags"])
        if filters["category"]:
            active.append(filters["category"])
        if active:
            text += "Current filters: " + ", ".join(active) + ". "
        if filters["budget_pkr"] is not None:
            text += f"The budget is {filters['budget_pkr']:g} rupees or less. "
        if filters["search"]:
            text += f"The current search is {filters['search']}. "
        text += "You can " + ", ".join(data["buttons"][:3]) + "."
        return text


def list_speech(rows: list[VisibleItem], *, language: str = "en", read_all=False) -> str:
    if not rows:
        return render("There are no matching options on this view.", language)
    if read_all or language == "ur":
        return " ".join(
            render(
                "{name}, {price} rupees." if row.available else "{name}, {price} rupees; sold out.",
                language,
                name=row.name,
                price=f"{row.price:g}",
            )
            for row in (rows if read_all else rows[:3])
        )
    labels = ("First", "Second", "Third")
    return " ".join(
        f"{labels[index]}: {row.name}, {row.price:g} rupees"
        + ("; sold out." if not row.available else ".")
        for index, row in enumerate(rows[:3])
    )


def reference_item(text: str, rows: list, focus: str | None = None) -> str | None:
    value = reference_text(text.lower())
    ordinals = re.findall(r"\b(first|second|third|fourth|fifth)\b", value)
    if len(set(ordinals)) == 1:
        index = ("first", "second", "third", "fourth", "fifth").index(ordinals[0])
        return rows[index].item_id if index < len(rows) else None
    if ordinals or "other" in value:
        return None
    if re.search(r"\bcheap(?:er|est)\b", value) and rows:
        cheapest = min(row.price for row in rows)
        best = [row.item_id for row in rows if row.price == cheapest]
        return best[0] if len(best) == 1 else None
    if re.search(r"\b(that|this|it)\b", value):
        return focus or (rows[0].item_id if len(rows) == 1 else None)
    return None
