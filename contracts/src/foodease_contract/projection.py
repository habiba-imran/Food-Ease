"""Explicit payload projections for contract verification, not runtime wiring.

No action is executed here. Missing filter state must be supplied from the
website authority, never guessed from rendered text or an LLM.
"""

from __future__ import annotations

import copy
from typing import Any

from foodease_contract.models import ContextSnapshot


def website_context(
    raw: dict[str, Any],
    *,
    category: str | None,
    max_price_pkr: float | None,
) -> dict[str, Any]:
    if raw.get("schema_version") != "1.0":
        raise ValueError("projection expects the current website v1 snapshot")
    projected = copy.deepcopy(raw)
    projected.update(schema_version="2.0", category=category, max_price_pkr=max_price_pkr)
    return ContextSnapshot.model_validate(projected).model_dump(mode="json")


def website_result_state(operation: str, raw: dict[str, Any]) -> dict[str, Any]:
    state = copy.deepcopy(raw)
    if operation in {"search_menu", "filter_menu"}:
        state["result_count"] = len(state["items"])
        state["items"] = state["items"][:25]
    return state


def legacy_mock_cart(raw: dict[str, Any]) -> dict[str, Any]:
    """Named opt-in migration; wire v2 never accepts the cart alias itself."""
    state = copy.deepcopy(raw)
    if "cart" not in state or "lines" in state:
        raise ValueError("expected legacy cart alias without canonical lines")
    state["lines"] = state.pop("cart")
    for line in state["lines"]:
        if "line_total" not in line:
            # Derived from verified unit price/quantity only, never model pricing.
            line["line_total"] = line["unit_price"] * line["quantity"]
    return state
