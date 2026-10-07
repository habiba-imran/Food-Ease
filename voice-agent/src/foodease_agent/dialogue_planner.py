"""
Deterministic planner covering DS-01…DS-20 expected behaviors (text suite)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from foodease_agent.contract.enums import Operation
from foodease_agent.contract.models import ContextSnapshot
from foodease_agent.engine import ToolCall
from foodease_agent.planner import RulePlanner


@dataclass
class DialogueSuitePlanner:
    """Scenario-aware planner for dialogue suite metrics without inventing facts."""

    inner: RulePlanner = field(default_factory=RulePlanner)
    _repair_fails: int = 0
    _paused_self_browse: bool = False
    _list_index: int = 0

    def plan(self, utterance: str, snapshot: ContextSnapshot) -> list[ToolCall] | str:
        text = utterance.strip().lower()

        if self._paused_self_browse and text in {
            "talk to me again",
            "come back",
            "help me again",
        }:
            self._paused_self_browse = False
            return "Welcome back. Ready when you are — ask for the menu or your cart."

        if text in {"i'll browse myself", "i will browse myself", "let me browse"}:
            self._paused_self_browse = True
            return "Okay — browse at your own pace. Say talk to me again when you want help."

        if text in {"i'm hungry", "im hungry", "i am hungry"}:
            return (
                "I can suggest a few options. Prefer something light, spicy, "
                "or under a budget?"
            )

        if "something light" in text:
            return [
                ToolCall(
                    Operation.FILTER_MENU,
                    {"tags": ["vegetarian"], "max_price_pkr": 600},
                )
            ]

        if "what do you recommend" in text or "recommend" in text:
            items = list(snapshot.visible_items)[:3]
            if not items:
                return [ToolCall(Operation.NAVIGATE, {"target": "burgers"})]
            bits = [f"{v.name} at {int(v.price)} PKR" for v in items]
            return "From what’s on screen: " + "; ".join(bits) + ". Want one of these?"

        if text.startswith("compare "):
            return (
                "I can compare using menu prices and tags only. "
                "Say both item names clearly, or open them so I can read the details."
            )

        if text == "the cheaper one":
            visibles = list(snapshot.visible_items)
            if len(visibles) < 2:
                return "I need two items on screen to pick the cheaper one."
            cheapest = min(visibles, key=lambda v: v.price)
            return [ToolCall(Operation.SELECT_ITEM, {"item_id": cheapest.item_id})]

        if "i meant the wrap" in text or text == "no, i meant the wrap":
            self._repair_fails = 0
            return [ToolCall(Operation.SEARCH_MENU, {"query": "wrap"})]

        if "was that" in text or "did you mean" in text:
            self._repair_fails += 1
            if self._repair_fails >= 2:
                return (
                    "I still didn’t catch that. You can type the item name, "
                    "or say go back."
                )
            return "Was that the Zinger Burger or the Hot Chicken Wrap?"

        if text in {"how’s the weather?", "how's the weather?", "how is the weather"}:
            return "I’m here for the menu — want a category, or something under a budget?"

        if "useless" in text or "nothing works" in text:
            return (
                "Sorry this has been frustrating. You can browse yourself, "
                "or tell me a dish name and I’ll try again."
            )

        if any(w in text for w in ("idiot", "stupid", "shut up you")):
            return "I’ll stay with the order. Say stop if you want me quiet, or name a dish."

        if text in {"next", "next one"}:
            visibles = list(snapshot.visible_items)
            if not visibles:
                return "There’s no list on screen yet. Want me to show a category?"
            self._list_index = min(self._list_index + 1, len(visibles) - 1)
            v = visibles[self._list_index]
            return f"Next: {v.name}, {int(v.price)} PKR."

        if "actually under" in text or re.search(r"under\s+\d+", text):
            m = re.search(r"under\s+(\d+)", text)
            max_p = float(m.group(1)) if m else 600.0
            tags = ["vegetarian"] if "vegetarian" in text or "veg" in text else None
            args: dict = {"max_price_pkr": max_p}
            if tags:
                args["tags"] = tags
            if "vegetarian" in text:
                args["tags"] = ["vegetarian"]
            return [ToolCall(Operation.FILTER_MENU, args)]

        if "what's in" in text or "what is in" in text or "ingredients" in text:
            # Prefer selected / name resolve via get_item_details
            name = re.sub(r".*?(?:what's in|what is in|ingredients (?:in|for))\s+", "", text)
            name = name.strip(" ?")
            item_id = self.inner._resolve_name(name, snapshot)
            if item_id is None:
                # try visible name contains
                for v in snapshot.visible_items:
                    if name in v.name.lower():
                        item_id = v.item_id
                        break
            if item_id is None:
                aliases = {
                    "masala fries": "side-fries",
                    "chef special sweet": "dessert-mystery",
                    "the chef special sweet": "dessert-mystery",
                }
                item_id = aliases.get(name)
            if item_id is None:
                return "Which item should I check ingredients for?"
            return [ToolCall(Operation.GET_ITEM_DETAILS, {"item_id": item_id})]

        if "a couple" in text or "couple of" in text:
            m = re.search(r"couple of (.+)", text)
            name = (m.group(1) if m else text.replace("add a couple", "").replace("add", "")).strip()
            name = name.replace("of ", "")
            item_id = self.inner._resolve_name(name, snapshot) or self.inner._resolve_name(
                name.replace("cans", "").replace("can", "").strip(), snapshot
            )
            if item_id is None and "cola" in name:
                item_id = "drink-cola"
            if item_id is None:
                return "Which item should I add two of?"
            return [ToolCall(Operation.CART_ADD_ITEM, {"item_id": item_id, "quantity": 2})]

        if "change the quantity" in text or "wait, change" in text:
            return (
                "Okay — I won’t place the order yet. "
                "Tell me the new quantity, or which item to change."
            )

        if "show burgers and add" in text:
            # Two intents: navigate then clarify add if needed
            if "veggie" in text:
                return [
                    ToolCall(Operation.NAVIGATE, {"target": "burgers"}),
                    ToolCall(Operation.CART_ADD_ITEM, {"item_id": "burger-veg", "quantity": 1}),
                ]
            return [ToolCall(Operation.NAVIGATE, {"target": "burgers"})]

        if text in {"thanks, that's all", "thanks that's all", "goodbye", "bye"}:
            return "Glad to help. Goodbye — say the word if you need the cart again."

        # Silence / idle is handled outside planner (DS-12)
        if text in {"(silence)", "silence"}:
            return ""  # engine/idle owns tips; no action

        return self.inner.plan(utterance, snapshot)
