"""Interaction-risk tiers (code, not prompt)."""

from __future__ import annotations

from enum import IntEnum

from foodease_agent.contract.enums import Operation


class RiskTier(IntEnum):
    READ = 0
    REVERSIBLE_CART = 1
    DESTRUCTIVE_OR_AMBIGUOUS = 2
    CHECKOUT_SUBMIT = 3


TIER0 = {
    Operation.NAVIGATE,
    Operation.SEARCH_MENU,
    Operation.FILTER_MENU,
    Operation.SELECT_ITEM,
    Operation.GET_ITEM_DETAILS,
    Operation.GET_CART,
    Operation.GET_CURRENT_CONTEXT,
    Operation.CHECKOUT_GET_SUMMARY,
    Operation.UNDO_LAST_REVERSIBLE_ACTION,
}

TIER1 = {
    Operation.CART_ADD_ITEM,
    Operation.CART_SET_QUANTITY,
}

TIER2 = {
    Operation.CART_REMOVE_ITEM,
}

TIER3 = {
    Operation.CHECKOUT_SUBMIT_DEMO_ORDER,
}


def tier_for(operation: Operation) -> RiskTier:
    if operation in TIER0:
        return RiskTier.READ
    if operation in TIER1:
        return RiskTier.REVERSIBLE_CART
    if operation in TIER2:
        return RiskTier.DESTRUCTIVE_OR_AMBIGUOUS
    if operation in TIER3:
        return RiskTier.CHECKOUT_SUBMIT
    raise ValueError(f"Unknown operation: {operation}")


def allows_read_retry(operation: Operation) -> bool:
    return tier_for(operation) == RiskTier.READ
