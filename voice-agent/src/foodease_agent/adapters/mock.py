"""In-process MockAdapter — deterministic fake app for tests."""

from __future__ import annotations

import asyncio
import copy
from collections.abc import Awaitable
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from typing import Any

from foodease_agent.adapters.base import (
    ContextCallback,
    ControlCallback,
    TextInputCallback,
)
from foodease_agent.contract.enums import (
    VISIBLE_ITEMS_MAX,
    ActionResultStatus,
    Operation,
    UserSafeErrorCode,
)
from foodease_agent.contract.models import (
    ActionRequestPayload,
    ActionResultPayload,
    AppControlPayload,
    AppTextInputPayload,
    CartLine,
    CartSummary,
    ContextSnapshot,
    FeeLine,
    VisibleItem,
)

# Menu lives under tests/fixtures; adapters load via import path set in tests.
# For package use, also ship a copy reference through a lazy import helper.


def _load_menu() -> tuple[Any, Any, float]:
    from foodease_agent.adapters.mock_catalog import MENU, MENU_BY_ID, SERVICE_FEE_PKR

    return MENU, MENU_BY_ID, SERVICE_FEE_PKR


class ScenarioMode(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    REJECTED = "rejected"
    STALE_CONTEXT = "stale_context"
    REQUIRES_CONFIRMATION = "requires_confirmation"
    DELAYED = "delayed"
    NEVER_REPLY = "never_reply"


@dataclass
class ScenarioConfig:
    mode: ScenarioMode = ScenarioMode.SUCCESS
    reason: str = "rejected by scenario"
    delay_ms: int = 0
    operations: set[Operation] | None = None  # None = all ops


@dataclass
class _CartLineState:
    item_id: str
    quantity: int


@dataclass
class MockAdapter:
    """Deterministic in-process application stand-in."""

    session_id: str = "mock-session"
    default_timeout_s: float = 2.0
    _revision: int = 0
    _page: str = "home"
    _back_stack: list[str] = field(default_factory=list)
    _category: str | None = None
    _focus_item_id: str | None = None
    _search_query: str | None = None
    _filter_tags: list[str] = field(default_factory=list)
    _max_price: float | None = None
    _cart: list[_CartLineState] = field(default_factory=list)
    _order_confirmed: bool = False
    _pending_confirmation_token: str | None = None
    _undo_stack: list[dict[str, Any]] = field(default_factory=list)
    _action_log: dict[str, ActionResultPayload] = field(default_factory=dict)
    _scenario: ScenarioConfig = field(default_factory=ScenarioConfig)
    _context_subs: list[ContextCallback] = field(default_factory=list)
    _control_subs: list[ControlCallback] = field(default_factory=list)
    _text_subs: list[TextInputCallback] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._menu, self._menu_by_id, self._service_fee = _load_menu()
        self._bump(emit=False)

    # --- scenario / GUI simulation ---

    def set_scenario(self, config: ScenarioConfig) -> None:
        self._scenario = config

    def clear_scenario(self) -> None:
        self._scenario = ScenarioConfig()

    async def simulate_gui_navigation(self, page: str) -> ContextSnapshot:
        """T09: GUI navigates without the agent."""
        self._navigate(page, from_gui=True)
        snap = self._snapshot()
        await self._emit_context(snap)
        return snap

    async def simulate_cart_change(
        self, item_id: str, quantity: int | None = None, *, remove: bool = False
    ) -> ContextSnapshot:
        """T13: GUI cart edit invalidates prior confirmation."""
        self._pending_confirmation_token = None
        if remove:
            self._cart = [c for c in self._cart if c.item_id != item_id]
        else:
            assert quantity is not None
            self._set_qty(item_id, quantity)
        self._bump()
        snap = self._snapshot()
        await self._emit_context(snap)
        return snap

    # --- AppAdapter API ---

    async def get_snapshot(self) -> ContextSnapshot:
        return self._snapshot()

    async def submit_action(
        self,
        request: ActionRequestPayload,
        *,
        timeout_s: float | None = None,
    ) -> ActionResultPayload:
        # Idempotency: duplicate action_id returns prior outcome.
        if request.action_id in self._action_log:
            return copy.deepcopy(self._action_log[request.action_id])

        timeout = self.default_timeout_s if timeout_s is None else timeout_s
        scenario = self._scenario
        applies = scenario.operations is None or request.operation in scenario.operations

        if applies and scenario.mode == ScenarioMode.NEVER_REPLY:
            try:
                await asyncio.wait_for(asyncio.sleep(timeout + 0.05), timeout=timeout)
            except TimeoutError:
                result = ActionResultPayload(
                    action_id=request.action_id,
                    status=ActionResultStatus.TIMEOUT_UNKNOWN,
                    error_code=UserSafeErrorCode.TIMEOUT,
                    error_message="No reply from the application.",
                )
                self._action_log[request.action_id] = result
                return copy.deepcopy(result)

        if applies and scenario.mode == ScenarioMode.DELAYED:
            await asyncio.sleep(scenario.delay_ms / 1000.0)

        if applies and scenario.mode == ScenarioMode.FAILED:
            result = ActionResultPayload(
                action_id=request.action_id,
                status=ActionResultStatus.FAILED,
                error_code=UserSafeErrorCode.INTERNAL,
                error_message="The application failed to complete that action.",
            )
            self._action_log[request.action_id] = result
            return copy.deepcopy(result)

        if applies and scenario.mode == ScenarioMode.REJECTED:
            result = ActionResultPayload(
                action_id=request.action_id,
                status=ActionResultStatus.REJECTED,
                error_code=UserSafeErrorCode.REJECTED,
                error_message=scenario.reason,
            )
            self._action_log[request.action_id] = result
            return copy.deepcopy(result)

        if applies and scenario.mode == ScenarioMode.STALE_CONTEXT:
            result = ActionResultPayload(
                action_id=request.action_id,
                status=ActionResultStatus.STALE_CONTEXT,
                error_code=UserSafeErrorCode.STALE_CONTEXT,
                error_message="Context is out of date. Refresh and try again.",
            )
            self._action_log[request.action_id] = result
            return copy.deepcopy(result)

        if applies and scenario.mode == ScenarioMode.REQUIRES_CONFIRMATION:
            result = ActionResultPayload(
                action_id=request.action_id,
                status=ActionResultStatus.REQUIRES_CONFIRMATION,
                error_code=UserSafeErrorCode.CONFIRMATION_REQUIRED,
                error_message="Please confirm the current checkout summary.",
                verified_state=self._cart_verified(),
            )
            self._action_log[request.action_id] = result
            return copy.deepcopy(result)

        result = await self._execute(request)
        self._action_log[request.action_id] = result
        await self._emit_context(self._snapshot())
        return copy.deepcopy(result)

    def subscribe_context(self, callback: ContextCallback) -> None:
        self._context_subs.append(callback)

    def subscribe_control(self, callback: ControlCallback) -> None:
        self._control_subs.append(callback)

    def subscribe_text_input(self, callback: TextInputCallback) -> None:
        self._text_subs.append(callback)

    async def inject_text_input(self, text: str) -> None:
        payload = AppTextInputPayload(text=text)
        for cb in self._text_subs:
            maybe = cb(payload)
            if asyncio.iscoroutine(maybe) or isinstance(maybe, Awaitable):
                await maybe  # type: ignore[arg-type]

    async def inject_control(self, payload: AppControlPayload) -> None:
        for cb in self._control_subs:
            maybe = cb(payload)
            if asyncio.iscoroutine(maybe) or isinstance(maybe, Awaitable):
                await maybe  # type: ignore[arg-type]

    # --- internals ---

    def _money(self, value: float) -> float:
        return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    def _bump(self, *, emit: bool = True) -> None:
        self._revision += 1

    async def _emit_context(self, snap: ContextSnapshot) -> None:
        for cb in self._context_subs:
            maybe = cb(snap)
            if asyncio.iscoroutine(maybe) or isinstance(maybe, Awaitable):
                await maybe  # type: ignore[arg-type]

    def _cart_subtotal(self) -> float:
        total = 0.0
        for line in self._cart:
            item = self._menu_by_id[line.item_id]
            total += item.price * line.quantity
        return self._money(total)

    def _cart_total(self) -> float:
        if not self._cart:
            return 0.0
        return self._money(self._cart_subtotal() + self._service_fee)

    def _cart_verified(self) -> dict[str, Any]:
        lines = []
        for line in self._cart:
            item = self._menu_by_id[line.item_id]
            lines.append(
                {
                    "item_id": line.item_id,
                    "name": item.name,
                    "quantity": line.quantity,
                    "unit_price": item.price,
                }
            )
        return {
            "cart": lines,
            "currency": "PKR",
            "subtotal": self._cart_subtotal(),
            "fees": [{"code": "service", "label": "Service fee", "amount": self._service_fee}]
            if self._cart
            else [],
            "total": self._cart_total(),
        }

    def _visible_items(self) -> list[VisibleItem]:
        items = list(self._menu)
        if self._category:
            items = [m for m in items if m.category == self._category]
        if self._search_query:
            q = self._search_query.lower()
            items = [m for m in items if q in m.name.lower() or q in m.description.lower()]
        if self._filter_tags:
            tags = set(self._filter_tags)
            items = [m for m in items if tags.issubset(set(m.tags))]
        if self._max_price is not None:
            items = [m for m in items if m.price <= self._max_price]
        out: list[VisibleItem] = []
        for m in items[:VISIBLE_ITEMS_MAX]:
            out.append(
                VisibleItem(
                    item_id=m.item_id,
                    name=m.name,
                    price=m.price,
                    currency=m.currency,
                    descriptors=list(m.tags),
                    available=m.available,
                )
            )
        return out

    def _snapshot(self) -> ContextSnapshot:
        cart_lines = [
            CartLine(
                item_id=line.item_id,
                name=self._menu_by_id[line.item_id].name,
                quantity=line.quantity,
                unit_price=self._menu_by_id[line.item_id].price,
            )
            for line in self._cart
        ]
        fees = (
            [FeeLine(code="service", label="Service fee", amount=self._service_fee)]
            if self._cart
            else []
        )
        nav = ["home", "back", "cart", "checkout", "burgers", "wraps", "drinks", "desserts"]
        return ContextSnapshot(
            session_id=self.session_id,
            revision=self._revision,
            route=self._page,
            focus_item_id=self._focus_item_id,
            valid_actions=[op.value for op in Operation],
            valid_navigation_targets=nav,
            filter_tags=list(self._filter_tags),
            search_query=self._search_query,
            visible_items=self._visible_items(),
            cart=CartSummary(
                lines=cart_lines,
                currency="PKR",
                subtotal=self._cart_subtotal(),
                fees=fees,
                total=self._cart_total(),
            ),
            checkout_available=bool(self._cart),
            action_pending=False,
            language="en",
        )

    def _navigate(self, target: str, *, from_gui: bool = False) -> None:
        if target == "back":
            if self._back_stack:
                self._page = self._back_stack.pop()
            else:
                self._page = "home"
            self._category = None
            self._focus_item_id = None
        else:
            if not from_gui:
                self._back_stack.append(self._page)
            self._page = target
            categories = {
                "burgers",
                "wraps",
                "rolls",
                "karahi",
                "biryani",
                "drinks",
                "desserts",
                "sides",
                "platters",
            }
            if target in categories:
                self._category = target
                self._page = "category"
            elif target == "home":
                self._category = None
                self._search_query = None
                self._filter_tags = []
                self._max_price = None
                self._focus_item_id = None
            elif target == "cart":
                self._focus_item_id = None
            elif target == "checkout":
                self._page = "checkout"
        self._bump()

    def _set_qty(self, item_id: str, quantity: int) -> None:
        for line in self._cart:
            if line.item_id == item_id:
                line.quantity = quantity
                return
        self._cart.append(_CartLineState(item_id=item_id, quantity=quantity))

    async def _execute(self, request: ActionRequestPayload) -> ActionResultPayload:
        op = request.operation
        args = request.arguments

        if op == Operation.GET_CURRENT_CONTEXT:
            return ActionResultPayload(
                action_id=request.action_id,
                status=ActionResultStatus.SUCCESS,
                verified_state={"snapshot": self._snapshot().model_dump(mode="json")},
            )

        if op == Operation.GET_CART:
            return ActionResultPayload(
                action_id=request.action_id,
                status=ActionResultStatus.SUCCESS,
                verified_state=self._cart_verified(),
            )

        if op == Operation.NAVIGATE:
            self._navigate(str(args["target"]))
            return ActionResultPayload(
                action_id=request.action_id,
                status=ActionResultStatus.SUCCESS,
                verified_state={"route": self._page, "revision": self._revision},
            )

        if op == Operation.SEARCH_MENU:
            self._search_query = str(args["query"])
            self._page = "category"
            self._bump()
            return ActionResultPayload(
                action_id=request.action_id,
                status=ActionResultStatus.SUCCESS,
                verified_state={
                    "query": self._search_query,
                    "items": [v.model_dump(mode="json") for v in self._visible_items()],
                },
            )

        if op == Operation.FILTER_MENU:
            self._filter_tags = list(args.get("tags") or [])
            self._max_price = args.get("max_price_pkr")
            self._page = "category"
            self._bump()
            return ActionResultPayload(
                action_id=request.action_id,
                status=ActionResultStatus.SUCCESS,
                verified_state={
                    "tags": self._filter_tags,
                    "max_price_pkr": self._max_price,
                    "items": [v.model_dump(mode="json") for v in self._visible_items()],
                },
            )

        if op == Operation.SELECT_ITEM:
            item_id = str(args["item_id"])
            if item_id not in self._menu_by_id:
                return ActionResultPayload(
                    action_id=request.action_id,
                    status=ActionResultStatus.REJECTED,
                    error_code=UserSafeErrorCode.INVALID_ARGUMENTS,
                    error_message="Unknown item.",
                )
            self._focus_item_id = item_id
            self._page = "item"
            self._bump()
            return ActionResultPayload(
                action_id=request.action_id,
                status=ActionResultStatus.SUCCESS,
                verified_state={"item_id": item_id, "route": "item"},
            )

        if op == Operation.GET_ITEM_DETAILS:
            item_id = str(args["item_id"])
            item = self._menu_by_id.get(item_id)
            if item is None:
                return ActionResultPayload(
                    action_id=request.action_id,
                    status=ActionResultStatus.REJECTED,
                    error_code=UserSafeErrorCode.INVALID_ARGUMENTS,
                    error_message="Unknown item.",
                )
            details: dict[str, Any] = {
                "item_id": item.item_id,
                "name": item.name,
                "price": item.price,
                "currency": item.currency,
                "description": item.description,
                "available": item.available,
                "tags": list(item.tags),
            }
            if item.ingredients is None:
                details["ingredients"] = None
                details["ingredients_available"] = False
            else:
                details["ingredients"] = list(item.ingredients)
                details["ingredients_available"] = True
            return ActionResultPayload(
                action_id=request.action_id,
                status=ActionResultStatus.SUCCESS,
                verified_state=details,
            )

        if op == Operation.CART_ADD_ITEM:
            item_id = str(args["item_id"])
            qty = int(args["quantity"])
            item = self._menu_by_id.get(item_id)
            if item is None:
                return ActionResultPayload(
                    action_id=request.action_id,
                    status=ActionResultStatus.REJECTED,
                    error_code=UserSafeErrorCode.INVALID_ARGUMENTS,
                    error_message="Unknown item.",
                )
            if not item.available:
                return ActionResultPayload(
                    action_id=request.action_id,
                    status=ActionResultStatus.REJECTED,
                    error_code=UserSafeErrorCode.OUT_OF_STOCK,
                    error_message="That item is out of stock.",
                )
            self._undo_stack.append({"cart": copy.deepcopy(self._cart)})
            existing = next((c for c in self._cart if c.item_id == item_id), None)
            if existing:
                existing.quantity = min(99, existing.quantity + qty)
            else:
                self._cart.append(_CartLineState(item_id=item_id, quantity=qty))
            self._pending_confirmation_token = None
            self._bump()
            return ActionResultPayload(
                action_id=request.action_id,
                status=ActionResultStatus.SUCCESS,
                verified_state=self._cart_verified(),
            )

        if op == Operation.CART_SET_QUANTITY:
            item_id = str(args["item_id"])
            qty = int(args["quantity"])
            if item_id not in {c.item_id for c in self._cart}:
                return ActionResultPayload(
                    action_id=request.action_id,
                    status=ActionResultStatus.REJECTED,
                    error_code=UserSafeErrorCode.INVALID_ARGUMENTS,
                    error_message="Item is not in the cart.",
                )
            self._undo_stack.append({"cart": copy.deepcopy(self._cart)})
            self._set_qty(item_id, qty)
            self._pending_confirmation_token = None
            self._bump()
            return ActionResultPayload(
                action_id=request.action_id,
                status=ActionResultStatus.SUCCESS,
                verified_state=self._cart_verified(),
            )

        if op == Operation.CART_REMOVE_ITEM:
            item_id = str(args["item_id"])
            self._undo_stack.append({"cart": copy.deepcopy(self._cart)})
            self._cart = [c for c in self._cart if c.item_id != item_id]
            self._pending_confirmation_token = None
            self._bump()
            return ActionResultPayload(
                action_id=request.action_id,
                status=ActionResultStatus.SUCCESS,
                verified_state=self._cart_verified(),
            )

        if op == Operation.CHECKOUT_GET_SUMMARY:
            if not self._cart:
                return ActionResultPayload(
                    action_id=request.action_id,
                    status=ActionResultStatus.REJECTED,
                    error_code=UserSafeErrorCode.NOT_AVAILABLE,
                    error_message="Cart is empty.",
                )
            token = f"tok_{self._revision}_{len(self._cart)}"
            self._pending_confirmation_token = token
            self._page = "checkout"
            self._bump()
            state = self._cart_verified()
            state["summary_revision"] = self._revision
            return ActionResultPayload(
                action_id=request.action_id,
                status=ActionResultStatus.SUCCESS,
                confirmation_token=token,
                verified_state=state,
            )

        if op == Operation.CHECKOUT_SUBMIT_DEMO_ORDER:
            if not self._cart:
                return ActionResultPayload(
                    action_id=request.action_id,
                    status=ActionResultStatus.REJECTED,
                    error_code=UserSafeErrorCode.NOT_AVAILABLE,
                    error_message="Cart is empty.",
                )
            if not args.get("confirmed"):
                return ActionResultPayload(
                    action_id=request.action_id,
                    status=ActionResultStatus.REQUIRES_CONFIRMATION,
                    error_code=UserSafeErrorCode.CONFIRMATION_REQUIRED,
                    error_message="Confirmation required.",
                )
            token = args.get("confirmation_token")
            if token is not None and token != self._pending_confirmation_token:
                return ActionResultPayload(
                    action_id=request.action_id,
                    status=ActionResultStatus.REJECTED,
                    error_code=UserSafeErrorCode.CONFIRMATION_EXPIRED,
                    error_message="Confirmation expired. Get a new summary.",
                )
            order = self._cart_verified()
            self._cart = []
            self._pending_confirmation_token = None
            self._order_confirmed = True
            self._page = "order_confirmation"
            self._bump()
            return ActionResultPayload(
                action_id=request.action_id,
                status=ActionResultStatus.SUCCESS,
                verified_state={"demo_order": order, "demo": True},
            )

        if op == Operation.UNDO_LAST_REVERSIBLE_ACTION:
            if not self._undo_stack:
                return ActionResultPayload(
                    action_id=request.action_id,
                    status=ActionResultStatus.REJECTED,
                    error_code=UserSafeErrorCode.NOT_AVAILABLE,
                    error_message="Nothing to undo.",
                )
            prev = self._undo_stack.pop()
            self._cart = prev["cart"]
            self._bump()
            return ActionResultPayload(
                action_id=request.action_id,
                status=ActionResultStatus.SUCCESS,
                verified_state=self._cart_verified(),
            )

        return ActionResultPayload(
            action_id=request.action_id,
            status=ActionResultStatus.REJECTED,
            error_code=UserSafeErrorCode.UNKNOWN_OPERATION,
            error_message="Unknown operation.",
        )
