"""Executable final integration contract. No network or domain execution here."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Literal, Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    StrictStr,
    TypeAdapter,
    field_validator,
    model_validator,
)

from foodease_contract.enums import (
    ActionResultStatus,
    AgentControlIntent,
    AssistantTranscriptPhase,
    Operation,
    ProductState,
    UserSafeErrorCode,
)

VERSION = "2.0"
# Project budget below LiveKit's documented 15 KiB RPC string maximum.
MAX_WIRE_BYTES = 14 * 1024
Id = Annotated[StrictStr, Field(min_length=1, max_length=128)]
ItemId = Annotated[StrictStr, Field(pattern=r"^[a-z][a-z0-9_\-]{1,63}$")]
Revision = Annotated[StrictInt, Field(ge=0)]
Quantity = Annotated[StrictInt, Field(ge=1, le=99)]
Money = Annotated[float, Field(ge=0, multiple_of=0.01, strict=True, allow_inf_nan=False)]
Route = Literal["home", "menu", "item", "cart", "checkout", "confirmation"]
RFC3339_PATTERN = r"^\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})$"
Timestamp = Annotated[AwareDatetime, Field(json_schema_extra={"pattern": RFC3339_PATTERN})]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, validate_default=True)

    @field_validator("timestamp", mode="before", check_fields=False)
    @classmethod
    def rfc3339_timestamp(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            return value
        if not isinstance(value, str) or not re.fullmatch(RFC3339_PATTERN, value):
            raise ValueError("timestamp must be an RFC3339 string with timezone")
        return value


class NoArgs(Model):
    pass


class NavigateArgs(Model):
    target: Annotated[StrictStr, Field(min_length=1, max_length=64)]


class SearchArgs(Model):
    # Empty query deliberately clears the current search.
    query: Annotated[StrictStr, Field(max_length=200)]


class FilterArgs(Model):
    tags: list[Annotated[StrictStr, Field(min_length=1, max_length=64)]] = Field(
        default_factory=list,
        max_length=16,
    )
    category: ItemId | None = None
    max_price_pkr: Money | None = None

    @field_validator("tags")
    @classmethod
    def unique_tags(cls, tags: list[str]) -> list[str]:
        if len(tags) != len(set(tags)):
            raise ValueError("duplicate tags")
        return tags


class ItemArgs(Model):
    item_id: ItemId


class AddArgs(ItemArgs):
    quantity: Quantity = 1


class SetQuantityArgs(ItemArgs):
    quantity: Quantity


class SubmitArgs(Model):
    confirmed: StrictBool = Field(json_schema_extra={"const": True})
    confirmation_token: Id
    summary_revision: Revision

    @field_validator("confirmed")
    @classmethod
    def explicit_confirmation(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("explicit current-summary confirmation required")
        return value


ARG_MODELS: dict[str, type[Model]] = {
    "navigate": NavigateArgs,
    "search_menu": SearchArgs,
    "filter_menu": FilterArgs,
    "select_item": ItemArgs,
    "get_item_details": ItemArgs,
    "get_cart": NoArgs,
    "cart.add_item": AddArgs,
    "cart.set_quantity": SetQuantityArgs,
    "cart.remove_item": ItemArgs,
    "checkout.get_summary": NoArgs,
    "checkout.submit_demo_order": SubmitArgs,
    "undo_last_reversible_action": NoArgs,
    "get_current_context": NoArgs,
}
READ_OPERATIONS = frozenset({"get_item_details", "get_cart", "get_current_context"})


class ActionRequest(Model):
    action_id: Id
    operation: Operation
    arguments: dict[str, Any]

    @field_validator("arguments")
    @classmethod
    def checked_arguments(cls, value: dict[str, Any], info: Any) -> dict[str, Any]:
        operation = info.data.get("operation")
        if operation is None:
            return value
        return ARG_MODELS[operation].model_validate(value).model_dump(mode="json")


class VisibleItem(Model):
    item_id: ItemId
    name: Annotated[StrictStr, Field(min_length=1, max_length=200)]
    price: Money
    currency: Literal["PKR"]
    descriptors: list[StrictStr] = Field(max_length=16)
    available: StrictBool


class ItemDetails(VisibleItem):
    description: Annotated[StrictStr, Field(max_length=2000)]
    ingredients: list[StrictStr] | None
    ingredients_available: StrictBool

    @model_validator(mode="after")
    def ingredient_truth(self) -> Self:
        if self.ingredients_available != (self.ingredients is not None):
            raise ValueError("ingredient availability contradicts ingredients")
        return self


class CartLine(Model):
    item_id: ItemId
    name: StrictStr
    quantity: Quantity
    unit_price: Money
    line_total: Money

    @model_validator(mode="after")
    def line_math(self) -> Self:
        if Decimal(str(self.unit_price)) * self.quantity != Decimal(str(self.line_total)):
            raise ValueError("line_total does not match unit price and quantity")
        return self


class Fee(Model):
    code: Id
    label: StrictStr
    amount: Money


class CartSummary(Model):
    lines: list[CartLine] = Field(max_length=32)
    currency: Literal["PKR"]
    subtotal: Money
    fees: list[Fee] = Field(max_length=16)
    total: Money

    @model_validator(mode="after")
    def cart_math(self) -> Self:
        subtotal = sum((Decimal(str(line.line_total)) for line in self.lines), Decimal(0))
        total = subtotal + sum((Decimal(str(fee.amount)) for fee in self.fees), Decimal(0))
        if Decimal(str(self.subtotal)) != subtotal or Decimal(str(self.total)) != total:
            raise ValueError("cart arithmetic mismatch")
        if len({line.item_id for line in self.lines}) != len(self.lines):
            raise ValueError("duplicate cart item")
        return self


class ContextSnapshot(Model):
    schema_version: Literal["2.0"]
    session_id: Id
    revision: Revision
    route: Route
    focus_item_id: ItemId | None
    valid_actions: list[Operation] = Field(max_length=13)
    valid_navigation_targets: list[StrictStr] = Field(max_length=64)
    filter_tags: list[StrictStr] = Field(max_length=16)
    category: ItemId | None
    max_price_pkr: Money | None
    search_query: Annotated[StrictStr, Field(max_length=200)] | None
    visible_items: list[VisibleItem] = Field(max_length=25)
    cart: CartSummary
    checkout_available: StrictBool
    action_pending: StrictBool
    language: Annotated[StrictStr, Field(min_length=1, max_length=35)]


class NavigationResult(Model):
    route: Route


class ItemsResult(Model):
    items: list[VisibleItem] = Field(max_length=25)
    result_count: Annotated[StrictInt, Field(ge=0)]

    @model_validator(mode="after")
    def count_matches(self) -> Self:
        if len(self.items) > self.result_count:
            raise ValueError("result_count smaller than bounded result list")
        return self


class CheckoutSummary(CartSummary):
    summary_revision: Revision


class DemoReceipt(Model):
    demo_order_id: Id
    demo: StrictBool = Field(json_schema_extra={"const": True})
    order: CartSummary

    @field_validator("demo")
    @classmethod
    def demo_only(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("only simulated orders are supported")
        return value


class ContextResult(Model):
    snapshot: ContextSnapshot


RESULT_MODELS: dict[str, type[Model]] = {
    "navigate": NavigationResult,
    "search_menu": ItemsResult,
    "filter_menu": ItemsResult,
    "select_item": VisibleItem,
    "get_item_details": ItemDetails,
    "get_cart": CartSummary,
    "cart.add_item": CartSummary,
    "cart.set_quantity": CartSummary,
    "cart.remove_item": CartSummary,
    "checkout.get_summary": CheckoutSummary,
    "checkout.submit_demo_order": DemoReceipt,
    "undo_last_reversible_action": CartSummary,
    "get_current_context": ContextResult,
}
ErrorCode = Literal[
    "unknown_operation",
    "invalid_arguments",
    "missing_action_id",
    "stale_context",
    "not_available",
    "out_of_stock",
    "confirmation_required",
    "confirmation_expired",
    "timeout",
    "rejected",
    "internal",
    "rate_limited",
    "idempotency_conflict",
    "session_mismatch",
    "unauthorized_sender",
    "payload_too_large",
    "unsupported_version",
]


class ActionResult(Model):
    action_id: Id
    operation: Operation
    status: ActionResultStatus
    verified_state: dict[str, Any] | None = None
    error_code: ErrorCode | None = None
    error_message: Annotated[StrictStr, Field(max_length=500)] | None = None
    confirmation_token: Id | None = None

    @model_validator(mode="after")
    def result_truth(self) -> Self:
        if self.status == "success":
            if self.verified_state is None or self.error_code is not None:
                raise ValueError("success requires verified state and no error")
            self.verified_state = (
                RESULT_MODELS[self.operation]
                .model_validate(
                    self.verified_state,
                )
                .model_dump(mode="json")
            )
            if self.operation == "checkout.get_summary" and not self.confirmation_token:
                raise ValueError("checkout summary requires an app-issued token")
        elif self.verified_state is not None or self.error_code is None:
            raise ValueError("non-success requires an error code and no verified success state")
        if self.confirmation_token is not None and (
            self.operation != "checkout.get_summary" or self.status != "success"
        ):
            raise ValueError("only successful checkout summaries carry a confirmation token")
        required_error = {
            "timeout_unknown": "timeout",
            "stale_context": "stale_context",
            "requires_confirmation": "confirmation_required",
        }.get(self.status)
        if required_error is not None and self.error_code != required_error:
            raise ValueError("status/error code mismatch")
        return self


class EventBase(Model):
    schema_version: Literal["2.0"]
    session_id: Id
    event_id: Id
    turn_id: Id | None = None
    timestamp: Timestamp
    context_revision: Revision | None = None


class TurnEvent(EventBase):
    turn_id: Id = Field(...)


class ActionRequestEvent(TurnEvent):
    type: Literal["agent.action_request"]
    context_revision: Revision = Field(...)
    payload: ActionRequest


class ActionResultEvent(TurnEvent):
    type: Literal["app.action_result"]
    context_revision: Revision = Field(...)
    reply_to: Id
    payload: ActionResult

    @model_validator(mode="after")
    def nested_context(self) -> Self:
        if self.payload.operation == "get_current_context" and self.payload.status == "success":
            snapshot = (self.payload.verified_state or {})["snapshot"]
            if snapshot["session_id"] != self.session_id:
                raise ValueError("nested context session_mismatch")
            if snapshot["revision"] != self.context_revision:
                raise ValueError("nested context revision mismatch")
        return self


class ContextEvent(EventBase):
    type: Literal["app.context_snapshot", "app.context_updated"]
    context_revision: Revision = Field(...)
    payload: ContextSnapshot

    @model_validator(mode="after")
    def same_snapshot(self) -> Self:
        if self.session_id != self.payload.session_id:
            raise ValueError("context session_mismatch")
        if self.context_revision != self.payload.revision:
            raise ValueError("context revision mismatch")
        return self


class UserTranscript(Model):
    utterance_id: Id
    text: Annotated[StrictStr, Field(max_length=2000)]
    source: Literal["speech"]


class UserTranscriptEvent(TurnEvent):
    type: Literal["transcript.user.partial", "transcript.user.final"]
    payload: UserTranscript


class AssistantTranscript(Model):
    utterance_id: Id
    text: Annotated[StrictStr, Field(max_length=2000)]
    phase: AssistantTranscriptPhase


class AssistantTranscriptEvent(TurnEvent):
    type: Literal["transcript.assistant"]
    payload: AssistantTranscript


class TextInput(Model):
    text: Annotated[StrictStr, Field(min_length=1, max_length=2000)]


class TextInputEvent(TurnEvent):
    type: Literal["app.text_input"]
    context_revision: Revision = Field(...)
    payload: TextInput


class Control(Model):
    intent: Literal[
        "start",
        "pause",
        "resume",
        "mute",
        "unmute",
        "end",
        "explain",
        "switch_mode",
        "pause_tips",
        "resume_tips",
    ]
    mode: Literal["manual", "voice", "typed"] | None = None

    @model_validator(mode="after")
    def mode_required(self) -> Self:
        if self.intent == "switch_mode" and self.mode is None:
            raise ValueError("switch_mode requires mode")
        return self


class AppControlEvent(EventBase):
    type: Literal["app.control"]
    payload: Control


class AgentControl(Model):
    intent: AgentControlIntent
    mode: Literal["manual", "voice", "typed"] | None = None

    @model_validator(mode="after")
    def mode_required(self) -> Self:
        if self.intent == "switch_mode" and self.mode is None:
            raise ValueError("switch_mode requires mode")
        return self


class AgentControlEvent(EventBase):
    type: Literal["agent.control"]
    payload: AgentControl


class AgentStatus(Model):
    state: ProductState
    detail: Annotated[StrictStr, Field(max_length=500)] | None = None


class AgentStatusEvent(EventBase):
    type: Literal["agent.status"]
    payload: AgentStatus


class AgentError(Model):
    code: UserSafeErrorCode
    message: Annotated[StrictStr, Field(max_length=500)]
    fatal: StrictBool


class AgentErrorEvent(EventBase):
    type: Literal["agent.error"]
    payload: AgentError


class Choice(Model):
    id: Id
    label: Annotated[StrictStr, Field(min_length=1, max_length=200)]


class Clarification(Model):
    question: Annotated[StrictStr, Field(min_length=1, max_length=500)]
    choices: list[Choice] = Field(max_length=8)


class ClarificationEvent(TurnEvent):
    type: Literal["agent.clarification_required"]
    payload: Clarification


Event = Annotated[
    ActionRequestEvent
    | ActionResultEvent
    | ContextEvent
    | UserTranscriptEvent
    | AssistantTranscriptEvent
    | TextInputEvent
    | AppControlEvent
    | AgentControlEvent
    | AgentStatusEvent
    | AgentErrorEvent
    | ClarificationEvent,
    Field(discriminator="type"),
]
EVENT_ADAPTER: TypeAdapter[Event] = TypeAdapter(Event)


class LookupRequest(Model):
    schema_version: Literal["2.0"]
    session_id: Id
    event_id: Id
    timestamp: Timestamp
    action_id: Id


class LookupResponse(Model):
    schema_version: Literal["2.0"]
    session_id: Id
    event_id: Id
    reply_to: Id
    timestamp: Timestamp
    action_id: Id
    state: Literal["not_seen", "pending", "found", "expired"]
    result: ActionResultEvent | None = None

    @model_validator(mode="after")
    def found_result(self) -> Self:
        if (self.state == "found") != (self.result is not None):
            raise ValueError("only found includes the original result")
        if self.result is not None and self.result.payload.action_id != self.action_id:
            raise ValueError("lookup action mismatch")
        if self.result is not None and self.result.session_id != self.session_id:
            raise ValueError("lookup session mismatch")
        if self.result is not None and self.result.payload.status == "timeout_unknown":
            raise ValueError("unknown execution outcome must remain pending, not found")
        return self


class SessionBinding(Model):
    session_id: Id
    user_identity: Id
    app_identity: Id
    agent_identity: Id

    @model_validator(mode="after")
    def distinct_seats(self) -> Self:
        if len({self.user_identity, self.app_identity, self.agent_identity}) != 3:
            raise ValueError("participant identities must be distinct")
        return self


def wire_bytes(raw: dict[str, Any]) -> bytes:
    encoded = json.dumps(raw, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
    if len(encoded) > MAX_WIRE_BYTES:
        raise ValueError("payload_too_large")
    return encoded


def decode_event(raw: dict[str, Any] | bytes | str) -> Event:
    if isinstance(raw, (bytes, str)):
        if len(raw.encode() if isinstance(raw, str) else raw) > MAX_WIRE_BYTES:
            raise ValueError("payload_too_large")
        return EVENT_ADAPTER.validate_json(raw)
    wire_bytes(raw)
    return EVENT_ADAPTER.validate_python(raw)


def encode_event(event: Event) -> bytes:
    # Revalidate even models constructed/copied by a caller.
    checked = EVENT_ADAPTER.validate_python(event.model_dump(mode="json"))
    return wire_bytes(checked.model_dump(mode="json"))


def assert_correlated(request: Event, result: Event) -> None:
    if not isinstance(request, ActionRequestEvent) or not isinstance(result, ActionResultEvent):
        raise ValueError("action request/result pair required")
    if (
        result.session_id != request.session_id
        or result.turn_id != request.turn_id
        or result.reply_to != request.event_id
        or result.payload.action_id != request.payload.action_id
        or result.payload.operation != request.payload.operation
    ):
        raise ValueError("uncorrelated action result")


def assert_revision(request: ActionRequest, *, expected: int, current: int) -> None:
    if expected > current or (request.operation not in READ_OPERATIONS and expected != current):
        raise ValueError("stale_context")


def assert_authorized(event: Event, binding: SessionBinding, *, sender_identity: str) -> None:
    if event.session_id != binding.session_id:
        raise ValueError("session_mismatch")
    if event.type in {"app.context_snapshot", "app.context_updated", "app.action_result"}:
        expected = binding.app_identity
    elif event.type in {"app.control", "app.text_input"}:
        expected = binding.user_identity
    else:
        # User/assistant transcription events are emitted by the bound worker.
        expected = binding.agent_identity
    if sender_identity != expected:
        raise ValueError("unauthorized_sender")


def assert_lookup_correlated(request: dict[str, Any], result: LookupResponse) -> None:
    if (
        result.session_id != request["session_id"]
        or result.reply_to != request["event_id"]
        or result.action_id != request["action_id"]
    ):
        raise ValueError("uncorrelated lookup result")


def request_fingerprint(session_id: str, request: ActionRequest) -> str:
    # IDs, envelope timestamps and revision are not business intent. Replays retain
    # the original action_id; changed operation/arguments under that ID conflict.
    content = {
        "session_id": session_id,
        "operation": request.operation,
        "arguments": request.arguments,
    }
    return hashlib.sha256(json.dumps(content, sort_keys=True, allow_nan=False).encode()).hexdigest()


def normalize_filters(arguments: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(arguments)
    vegetarian = normalized.pop("vegetarian", None)
    parsed = FilterArgs.model_validate(normalized)
    if vegetarian is not None:
        if type(vegetarian) is not bool:
            # Use the same typed validation error as malformed canonical fields.
            StrictVegetarian.model_validate({"vegetarian": vegetarian})
        tags = list(parsed.tags)
        if vegetarian is False and "vegetarian" in tags:
            raise ValueError("contradictory vegetarian filters")
        if vegetarian and "vegetarian" not in tags:
            tags.append("vegetarian")
        parsed = FilterArgs.model_validate({**parsed.model_dump(mode="json"), "tags": tags})
    return parsed.model_dump(mode="json")


class StrictVegetarian(Model):
    vegetarian: StrictBool
