"""Deterministic planners for tests and the text CLI (no LLM required)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from foodease_agent.contract.enums import Operation
from foodease_agent.contract.models import ContextSnapshot
from foodease_agent.engine import ToolCall


@dataclass
class ScriptedPlanner:
    """V4.1 fake LLM: map exact utterances to planned tool calls or text."""

    scripts: dict[str, list[ToolCall] | str] = field(default_factory=dict)

    def plan(self, utterance: str, snapshot: ContextSnapshot) -> list[ToolCall] | str:
        key = utterance.strip().lower()
        if key in self.scripts:
            return self.scripts[key]
        return "I am not sure how to help with that yet."


@dataclass
class RulePlanner:
    """Simple pattern planner for CLI demos and text-mode acceptance scripts."""

    def plan(self, utterance: str, snapshot: ContextSnapshot) -> list[ToolCall] | str:
        text = utterance.strip().lower()

        if text in {"where am i?", "where am i"}:
            return f"You are on the {snapshot.route} page."

        if "vegetarian" in text or "veggie" in text:
            args: dict = {"tags": ["vegetarian"]}
            m = re.search(r"under\s+(\d+)", text)
            if m:
                args["max_price_pkr"] = float(m.group(1))
            return [ToolCall(Operation.FILTER_MENU, args)]

        if text.startswith("show ") or text.startswith("search "):
            q = text.split(" ", 1)[1]
            return [ToolCall(Operation.SEARCH_MENU, {"query": q})]

        if "spicy" in text:
            return [ToolCall(Operation.FILTER_MENU, {"tags": ["spicy"]})]

        m_add = re.search(r"add\s+(\d+)\s+(.+)", text)
        if m_add:
            qty = int(m_add.group(1))
            name = m_add.group(2).strip()
            item_id = self._resolve_name(name, snapshot)
            if item_id is None:
                return "Which item should I add? Please say the full name."
            return [ToolCall(Operation.CART_ADD_ITEM, {"item_id": item_id, "quantity": qty})]

        if text.startswith("add "):
            name = text[4:].strip()
            item_id = self._resolve_name(name, snapshot)
            if item_id is None:
                return "Which item should I add?"
            return [ToolCall(Operation.CART_ADD_ITEM, {"item_id": item_id, "quantity": 1})]

        m_qty = re.search(r"(?:make it|set(?: quantity)?(?: to)?)\s+(\d+)", text)
        if m_qty and snapshot.cart.lines:
            qty = int(m_qty.group(1))
            item_id = snapshot.cart.lines[-1].item_id
            return [ToolCall(Operation.CART_SET_QUANTITY, {"item_id": item_id, "quantity": qty})]

        if text.startswith("remove "):
            name = text[7:].strip()
            item_id = self._resolve_name(name, snapshot) or next(
                (line.item_id for line in snapshot.cart.lines if name in line.name.lower()),
                None,
            )
            if item_id is None:
                return "Which cart item should I remove?"
            return [ToolCall(Operation.CART_REMOVE_ITEM, {"item_id": item_id})]

        if "checkout" in text or "place" in text and "order" in text:
            return [ToolCall(Operation.CHECKOUT_SUBMIT_DEMO_ORDER, {"confirmed": False})]

        if "cart" in text:
            return [ToolCall(Operation.GET_CART, {})]

        if text.startswith("go ") or text in {"home", "cart", "checkout"}:
            target = text.replace("go to ", "").replace("go ", "").strip()
            return [ToolCall(Operation.NAVIGATE, {"target": target})]

        return "I can help you browse the menu, update the cart, or place a demo order."

    def _resolve_name(self, name: str, snapshot: ContextSnapshot) -> str | None:
        name = name.lower().strip()
        # Prefer cart lines, then visible items
        for line in snapshot.cart.lines:
            if name in line.name.lower() or line.name.lower() in name:
                return line.item_id
        matches = [v for v in snapshot.visible_items if name in v.name.lower() or v.name.lower() in name]
        if len(matches) == 1:
            return matches[0].item_id
        if len(matches) > 1:
            return None
        # Fallback to common demo ids when browsing home (not yet filtered into visible)
        aliases = {
            "hot chicken wrap": "wrap-hot-chicken",
            "chicken wrap": "wrap-chicken",
            "veggie wrap": "wrap-veg",
            "sweet lassi": "drink-lassi-small",
            "zinger burger": "zinger-classic",
            "cola": "drink-cola",
            "masala fries": "side-fries",
        }
        return aliases.get(name)
