"""FoodEase shopping domain.

This module is the website's source of truth for menu search, cart math,
checkout confirmation, revision state, and future agent action handling.
"""

from __future__ import annotations

import copy
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from foodease_contract.models import ActionRequest
from pydantic import ValidationError

from foodease_website.catalog import CatalogSeed, MenuItem

SUCCESS = "success"
REJECTED = "rejected"
STALE_CONTEXT = "stale_context"
REQUIRES_CONFIRMATION = "requires_confirmation"

MUTATING_OPERATIONS = {
    "navigate",
    "search_menu",
    "filter_menu",
    "select_item",
    "cart.add_item",
    "cart.set_quantity",
    "cart.remove_item",
    "checkout.get_summary",
    "checkout.submit_demo_order",
    "undo_last_reversible_action",
}

ALL_OPERATIONS = [
    "navigate",
    "search_menu",
    "filter_menu",
    "select_item",
    "get_item_details",
    "get_cart",
    "cart.add_item",
    "cart.set_quantity",
    "cart.remove_item",
    "checkout.get_summary",
    "checkout.submit_demo_order",
    "undo_last_reversible_action",
    "get_current_context",
]


@dataclass
class CartLineState:
    item_id: str
    quantity: int


@dataclass
class FoodEaseDomain:
    catalog: CatalogSeed
    session_id: str = "foodease-local-session"
    revision: int = 0
    route: str = "home"
    focus_item_id: str | None = None
    search_query: str | None = None
    filter_tags: list[str] = field(default_factory=list)
    max_price_pkr: float | None = None
    category: str | None = None
    cart: dict[str, CartLineState] = field(default_factory=dict)
    action_log: dict[str, dict[str, Any]] = field(default_factory=dict)
    undo_stack: list[dict[str, CartLineState]] = field(default_factory=list)
    pending_confirmation_token: str | None = None
    pending_confirmation_revision: int | None = None
    pending_confirmation_cart: dict[str, Any] | None = None
    demo_order_count: int = 0
    cart_revision: int = 0
    clock: Callable[[], float] = time.monotonic
    confirmation_ttl: float = 300
    confirmation_expires_at: float = 0
    view_history: list[dict[str, Any]] = field(default_factory=list)
    fingerprints: dict[str, tuple[str, dict[str, Any]]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.menu_by_id = {item.item_id: item for item in self.catalog.items}
        self.revision = 1

    def execute_action(
        self,
        action_id: str,
        operation: str,
        arguments: dict[str, Any] | None = None,
        *,
        context_revision: int | None = None,
    ) -> dict[str, Any]:
        if not action_id:
            return self._result(action_id, REJECTED, error_code="missing_action_id")
        if operation not in ALL_OPERATIONS:
            return self._result(action_id, REJECTED, error_code="unknown_operation")
        try:
            request = ActionRequest.model_validate(
                {
                    "action_id": action_id,
                    "operation": operation,
                    "arguments": arguments if arguments is not None else {},
                }
            )
        except ValidationError:
            return self._result(action_id, REJECTED, error_code="invalid_arguments")
        args = request.arguments
        fingerprint = (operation, args)
        if action_id in self.action_log:
            if self.fingerprints.get(action_id) != fingerprint:
                return self._result(action_id, REJECTED, error_code="idempotency_conflict")
            return copy.deepcopy(self.action_log[action_id])
        self.fingerprints[action_id] = fingerprint
        if self._is_stale(operation, context_revision):
            result = self._result(
                action_id,
                STALE_CONTEXT,
                error_code="stale_context",
                error_message="Context is out of date. Refresh and try again.",
            )
            self.action_log[action_id] = result
            return copy.deepcopy(result)

        result = self._dispatch(action_id, operation, args)
        self.action_log[action_id] = result
        return copy.deepcopy(result)

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema_version": "2.0",
            "session_id": self.session_id,
            "revision": self.revision,
            "route": self.route,
            "focus_item_id": self.focus_item_id,
            "valid_actions": ALL_OPERATIONS,
            "valid_navigation_targets": self._navigation_targets(),
            "filter_tags": self.filter_tags,
            "category": self.category,
            "max_price_pkr": self.max_price_pkr,
            "search_query": self.search_query,
            "visible_items": [self._visible_item(item) for item in self.visible_items()[:25]],
            "cart": self.cart_summary(),
            "checkout_available": bool(self.cart),
            "action_pending": False,
            "language": "en",
        }

    def visible_items(self) -> list[MenuItem]:
        items = list(self.catalog.items)
        if self.category:
            items = [item for item in items if item.category == self.category]
        if self.search_query:
            query = self.search_query.lower()
            items = [
                item
                for item in items
                if query in item.name.lower() or query in item.description.lower()
            ]
        if self.filter_tags:
            tags = set(self.filter_tags)
            items = [item for item in items if tags.issubset(set(item.tags))]
        if self.max_price_pkr is not None:
            items = [item for item in items if item.unit_price_pkr <= self.max_price_pkr]
        return items

    def cart_summary(self) -> dict[str, Any]:
        lines = []
        subtotal = Decimal(0)
        for line in self.cart.values():
            item = self.menu_by_id[line.item_id]
            amount = Decimal(str(item.unit_price_pkr)) * line.quantity
            subtotal += amount
            lines.append(
                {
                    "item_id": item.item_id,
                    "name": item.name,
                    "quantity": line.quantity,
                    "unit_price": item.unit_price_pkr,
                    "line_total": float(amount),
                }
            )
        fees = (
            [{"code": "service", "label": "Service fee", "amount": self.catalog.service_fee_pkr}]
            if lines
            else []
        )
        return {
            "lines": lines,
            "currency": self.catalog.currency,
            "subtotal": float(subtotal),
            "fees": fees,
            "total": float(subtotal + Decimal(str(self.catalog.service_fee_pkr if lines else 0))),
        }

    def _dispatch(self, action_id: str, operation: str, args: dict[str, Any]) -> dict[str, Any]:
        if operation == "get_current_context":
            return self._result(action_id, SUCCESS, verified_state={"snapshot": self.snapshot()})
        if operation == "get_cart":
            return self._result(action_id, SUCCESS, verified_state=self.cart_summary())
        if operation == "navigate":
            return self._navigate(action_id, str(args.get("target", "")))
        if operation == "search_menu":
            self._save_view()
            self.search_query = str(args.get("query", "")).strip()
            self.route = "menu"
            self.focus_item_id = None
            self._bump()
            return self._result(
                action_id,
                SUCCESS,
                verified_state={
                    "items": [self._visible_item(item) for item in self.visible_items()[:25]],
                    "result_count": len(self.visible_items()),
                },
            )
        if operation == "filter_menu":
            known_tags = {tag for item in self.catalog.items for tag in item.tags}
            if (
                not set(args["tags"]).issubset(known_tags)
                or args["category"] is not None
                and args["category"] not in self.catalog.categories
            ):
                return self._result(action_id, REJECTED, error_code="invalid_arguments")
            self._save_view()
            self.filter_tags = list(args.get("tags") or [])
            self.max_price_pkr = args.get("max_price_pkr")
            self.category = args.get("category")
            self.route = "menu"
            self.focus_item_id = None
            self._bump()
            return self._result(
                action_id,
                SUCCESS,
                verified_state={
                    "items": [self._visible_item(item) for item in self.visible_items()[:25]],
                    "result_count": len(self.visible_items()),
                },
            )
        if operation == "select_item":
            return self._select_item(action_id, str(args.get("item_id", "")))
        if operation == "get_item_details":
            return self._item_details(action_id, str(args.get("item_id", "")))
        if operation == "cart.add_item":
            return self._add_item(
                action_id, str(args.get("item_id", "")), int(args.get("quantity", 1))
            )
        if operation == "cart.set_quantity":
            return self._set_quantity(
                action_id, str(args.get("item_id", "")), int(args.get("quantity", 0))
            )
        if operation == "cart.remove_item":
            return self._remove_item(action_id, str(args.get("item_id", "")))
        if operation == "checkout.get_summary":
            return self._checkout_summary(action_id)
        if operation == "checkout.submit_demo_order":
            return self._submit_demo_order(action_id, args)
        if operation == "undo_last_reversible_action":
            return self._undo(action_id)
        return self._result(action_id, REJECTED, error_code="unknown_operation")

    def _navigate(self, action_id: str, target: str) -> dict[str, Any]:
        if target == "back":
            if not self.view_history:
                return self._result(action_id, REJECTED, error_code="not_available")
            for key, value in self.view_history.pop().items():
                setattr(self, key, value)
            self._bump()
            return self._result(action_id, SUCCESS, verified_state={"route": self.route})
        if target not in {*self.catalog.categories, "home", "menu", "cart", "checkout"}:
            return self._result(action_id, REJECTED, error_code="invalid_arguments")
        self._save_view()
        self.focus_item_id = None
        if target in self.catalog.categories:
            self.category = target
            self.route = "menu"
        elif target in {"home", "menu", "cart", "checkout"}:
            self.route = target
            if target == "home":
                self.category = None
                self.search_query = None
                self.filter_tags = []
                self.max_price_pkr = None
                self.focus_item_id = None
        else:
            return self._result(action_id, REJECTED, error_code="invalid_arguments")
        self._bump()
        return self._result(action_id, SUCCESS, verified_state={"route": self.route})

    def _select_item(self, action_id: str, item_id: str) -> dict[str, Any]:
        if item_id not in self.menu_by_id:
            return self._result(action_id, REJECTED, error_code="invalid_arguments")
        self._save_view()
        self.focus_item_id = item_id
        self.route = "item"
        self._bump()
        return self._result(
            action_id, SUCCESS, verified_state=self._visible_item(self.menu_by_id[item_id])
        )

    def _item_details(self, action_id: str, item_id: str) -> dict[str, Any]:
        item = self.menu_by_id.get(item_id)
        if item is None:
            return self._result(action_id, REJECTED, error_code="invalid_arguments")
        return self._result(
            action_id,
            SUCCESS,
            verified_state={
                **self._visible_item(item),
                "description": item.description,
                "ingredients": item.ingredients,
                "ingredients_available": item.ingredients is not None,
            },
        )

    def _add_item(self, action_id: str, item_id: str, quantity: int) -> dict[str, Any]:
        item = self.menu_by_id.get(item_id)
        if item is None or quantity < 1 or quantity > 99:
            return self._result(action_id, REJECTED, error_code="invalid_arguments")
        if not item.available:
            return self._result(action_id, REJECTED, error_code="out_of_stock")
        current = self.cart.get(item_id)
        new_quantity = (current.quantity if current else 0) + quantity
        if new_quantity > 99:
            return self._result(action_id, REJECTED, error_code="invalid_arguments")
        self._save_undo()
        self.cart[item_id] = CartLineState(item_id=item_id, quantity=new_quantity)
        self._invalidate_confirmation()
        self._bump()
        return self._result(action_id, SUCCESS, verified_state=self.cart_summary())

    def _set_quantity(self, action_id: str, item_id: str, quantity: int) -> dict[str, Any]:
        if item_id not in self.cart or quantity < 1 or quantity > 99:
            return self._result(action_id, REJECTED, error_code="invalid_arguments")
        self._save_undo()
        self.cart[item_id] = CartLineState(item_id=item_id, quantity=quantity)
        self._invalidate_confirmation()
        self._bump()
        return self._result(action_id, SUCCESS, verified_state=self.cart_summary())

    def _remove_item(self, action_id: str, item_id: str) -> dict[str, Any]:
        if item_id not in self.cart:
            return self._result(action_id, REJECTED, error_code="invalid_arguments")
        self._save_undo()
        self.cart.pop(item_id)
        self._invalidate_confirmation()
        self._bump()
        return self._result(action_id, SUCCESS, verified_state=self.cart_summary())

    def _checkout_summary(self, action_id: str) -> dict[str, Any]:
        if not self.cart:
            return self._result(action_id, REJECTED, error_code="not_available")
        self._save_view()
        self.route = "checkout"
        self.focus_item_id = None
        self.pending_confirmation_revision = self.cart_revision
        self.pending_confirmation_cart = copy.deepcopy(self.cart_summary())
        self.pending_confirmation_token = secrets.token_urlsafe(32)
        self.confirmation_expires_at = self.clock() + self.confirmation_ttl
        self._bump()
        state = self.cart_summary()
        state["summary_revision"] = self.pending_confirmation_revision
        return self._result(
            action_id,
            SUCCESS,
            verified_state=state,
            confirmation_token=self.pending_confirmation_token,
        )

    def _submit_demo_order(self, action_id: str, args: dict[str, Any]) -> dict[str, Any]:
        if not self.cart:
            return self._result(action_id, REJECTED, error_code="not_available")
        if not args.get("confirmed"):
            return self._result(
                action_id, REQUIRES_CONFIRMATION, error_code="confirmation_required"
            )
        token = args.get("confirmation_token")
        if (
            not token
            or not self.pending_confirmation_token
            or not secrets.compare_digest(token.encode(), self.pending_confirmation_token.encode())
            or args.get("summary_revision") != self.pending_confirmation_revision
            or self.cart_revision != self.pending_confirmation_revision
            or self.cart_summary() != self.pending_confirmation_cart
            or self.clock() >= self.confirmation_expires_at
        ):
            return self._result(action_id, REJECTED, error_code="confirmation_expired")
        if self.pending_confirmation_revision is None:
            return self._result(
                action_id, REQUIRES_CONFIRMATION, error_code="confirmation_required"
            )
        order = self.cart_summary()
        self.demo_order_count += 1
        order_id = f"DEMO-{secrets.token_hex(12)}"
        self.cart.clear()
        self.undo_stack.clear()
        self.route = "confirmation"
        self.focus_item_id = None
        self._invalidate_confirmation()
        self._bump()
        return self._result(
            action_id,
            SUCCESS,
            verified_state={"demo_order_id": order_id, "demo": True, "order": order},
        )

    def _undo(self, action_id: str) -> dict[str, Any]:
        if not self.undo_stack:
            return self._result(action_id, REJECTED, error_code="not_available")
        self.cart = self.undo_stack.pop()
        self._invalidate_confirmation()
        self._bump()
        return self._result(action_id, SUCCESS, verified_state=self.cart_summary())

    def _is_stale(self, operation: str, context_revision: int | None) -> bool:
        return (
            type(context_revision) is not int
            or context_revision > self.revision
            or operation in MUTATING_OPERATIONS
            and context_revision != self.revision
        )

    def _save_undo(self) -> None:
        self.undo_stack.append(copy.deepcopy(self.cart))
        del self.undo_stack[:-64]

    def _invalidate_confirmation(self) -> None:
        self.cart_revision += 1
        self.pending_confirmation_token = None
        self.pending_confirmation_revision = None
        self.pending_confirmation_cart = None
        self.confirmation_expires_at = 0

    def _save_view(self) -> None:
        self.view_history.append(
            copy.deepcopy(
                {
                    key: getattr(self, key)
                    for key in (
                        "route",
                        "category",
                        "search_query",
                        "filter_tags",
                        "max_price_pkr",
                        "focus_item_id",
                    )
                }
            )
        )
        del self.view_history[:-64]

    def _clear_stale_focus(self) -> None:
        if self.focus_item_id and self.focus_item_id not in {
            item.item_id for item in self.visible_items()
        }:
            self.focus_item_id = None

    def _navigation_targets(self) -> list[str]:
        return ["home", "menu", "back", "cart", "checkout", *self.catalog.categories]

    def _bump(self) -> None:
        self.revision += 1

    def _visible_item(self, item: MenuItem) -> dict[str, Any]:
        return {
            "item_id": item.item_id,
            "name": item.name,
            "price": item.unit_price_pkr,
            "currency": item.currency,
            "descriptors": item.tags,
            "available": item.available,
        }

    def _result(
        self,
        action_id: str,
        status: str,
        *,
        verified_state: dict[str, Any] | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        confirmation_token: str | None = None,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "action_id": action_id,
            "status": status,
            "verified_state": verified_state,
            "error_code": error_code,
            "error_message": error_message,
        }
        if confirmation_token is not None:
            result["confirmation_token"] = confirmation_token
        return result
