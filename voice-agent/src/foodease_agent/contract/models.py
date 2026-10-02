"""Contract v1 Pydantic models — single source of truth for JSON Schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel, field_validator

from foodease_agent.contract.enums import (
    ITEM_ID_PATTERN,
    QUANTITY_MAX,
    QUANTITY_MIN,
    SCHEMA_VERSION,
    VISIBLE_ITEMS_MAX,
    ActionResultStatus,
    AgentControlIntent,
    AppControlIntent,
    AssistantTranscriptPhase,
    EventType,
    Operation,
    ProductState,
    UserSafeErrorCode,
)

ItemId = Annotated[str, Field(pattern=ITEM_ID_PATTERN)]
Quantity = Annotated[int, Field(ge=QUANTITY_MIN, le=QUANTITY_MAX)]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


# --- Action arguments (one model per operation) ---


class NavigateArgs(ContractModel):
    target: str = Field(
        description="Semantic navigation target ID (e.g. home, back, cart, checkout)."
    )


class SearchMenuArgs(ContractModel):
    query: str = Field(min_length=1, max_length=200)


class FilterMenuArgs(ContractModel):
    tags: list[str] = Field(default_factory=list, max_length=16)
    max_price_pkr: float | None = Field(default=None, ge=0)


class SelectItemArgs(ContractModel):
    item_id: ItemId


class GetItemDetailsArgs(ContractModel):
    item_id: ItemId


class GetCartArgs(ContractModel):
    pass


class CartAddItemArgs(ContractModel):
    item_id: ItemId
    quantity: Quantity = 1


class CartSetQuantityArgs(ContractModel):
    item_id: ItemId
    quantity: Quantity


class CartRemoveItemArgs(ContractModel):
    item_id: ItemId


class CheckoutGetSummaryArgs(ContractModel):
    pass


class CheckoutSubmitDemoOrderArgs(ContractModel):
    confirmed: bool = True
    confirmation_token: str | None = Field(
        default=None,
        description="Optional app-issued token; agent works when absent.",
        json_schema_extra={"x-habiba-default": "optional; agent binds confirmation itself"},
    )


class UndoLastReversibleActionArgs(ContractModel):
    pass


class GetCurrentContextArgs(ContractModel):
    pass


ARGS_BY_OPERATION: dict[Operation, type[ContractModel]] = {
    Operation.NAVIGATE: NavigateArgs,
    Operation.SEARCH_MENU: SearchMenuArgs,
    Operation.FILTER_MENU: FilterMenuArgs,
    Operation.SELECT_ITEM: SelectItemArgs,
    Operation.GET_ITEM_DETAILS: GetItemDetailsArgs,
    Operation.GET_CART: GetCartArgs,
    Operation.CART_ADD_ITEM: CartAddItemArgs,
    Operation.CART_SET_QUANTITY: CartSetQuantityArgs,
    Operation.CART_REMOVE_ITEM: CartRemoveItemArgs,
    Operation.CHECKOUT_GET_SUMMARY: CheckoutGetSummaryArgs,
    Operation.CHECKOUT_SUBMIT_DEMO_ORDER: CheckoutSubmitDemoOrderArgs,
    Operation.UNDO_LAST_REVERSIBLE_ACTION: UndoLastReversibleActionArgs,
    Operation.GET_CURRENT_CONTEXT: GetCurrentContextArgs,
}


# --- Context snapshot (VA-09) ---


class VisibleItem(ContractModel):
    item_id: ItemId
    name: str
    price: float = Field(ge=0)
    currency: str = "PKR"
    descriptors: list[str] = Field(default_factory=list)
    available: bool = True


class CartLine(ContractModel):
    item_id: ItemId
    name: str
    quantity: Quantity
    unit_price: float = Field(ge=0)


class FeeLine(ContractModel):
    code: str
    label: str
    amount: float


class CartSummary(ContractModel):
    lines: list[CartLine] = Field(default_factory=list)
    currency: str = "PKR"
    subtotal: float | None = None
    fees: list[FeeLine] = Field(default_factory=list)
    total: float | None = None


class ContextSnapshot(ContractModel):
    """VA-09 application context. Bounded visible_items — not a full catalog dump."""

    schema_version: Literal["1.0"] = SCHEMA_VERSION
    session_id: str
    revision: int = Field(ge=0)
    route: str
    focus_item_id: ItemId | None = None
    valid_actions: list[str] = Field(default_factory=list)
    valid_navigation_targets: list[str] = Field(
        default_factory=list,
        description="Semantic IDs including back/home when available.",
        json_schema_extra={"x-habiba-default": "include back and home when the app supports them"},
    )
    filter_tags: list[str] = Field(default_factory=list)
    search_query: str | None = None
    visible_items: list[VisibleItem] = Field(default_factory=list, max_length=VISIBLE_ITEMS_MAX)
    cart: CartSummary = Field(default_factory=CartSummary)
    checkout_available: bool = False
    action_pending: bool = False
    language: str = "en"
    spoken_feedback_preference: str | None = None


# --- Event payloads ---


class AgentStatusPayload(ContractModel):
    state: ProductState
    detail: str | None = None


class TranscriptUserPayload(ContractModel):
    text: str
    is_final: bool


class TranscriptAssistantPayload(ContractModel):
    text: str
    phase: AssistantTranscriptPhase


class ActionRequestPayload(ContractModel):
    action_id: str = Field(min_length=1)
    operation: Operation
    arguments: dict[str, Any] = Field(default_factory=dict)

    @field_validator("arguments")
    @classmethod
    def validate_arguments_for_operation(
        cls, arguments: dict[str, Any], info: Any
    ) -> dict[str, Any]:
        operation = info.data.get("operation")
        if operation is None:
            return arguments
        model = ARGS_BY_OPERATION[Operation(operation)]
        parsed = model.model_validate(arguments)
        return parsed.model_dump(mode="json", exclude_none=True)


class ClarificationChoice(ContractModel):
    id: str
    label: str


class ClarificationRequiredPayload(ContractModel):
    question: str
    choices: list[ClarificationChoice] = Field(default_factory=list, max_length=8)


class AgentControlPayload(ContractModel):
    intent: AgentControlIntent
    mode: str | None = None


class AgentErrorPayload(ContractModel):
    code: UserSafeErrorCode
    message: str
    fatal: bool = False


class ActionResultPayload(ContractModel):
    action_id: str = Field(min_length=1)
    status: ActionResultStatus
    verified_state: dict[str, Any] | None = None
    error_code: UserSafeErrorCode | None = None
    error_message: str | None = None
    confirmation_token: str | None = Field(
        default=None,
        description="Optional; may appear on checkout.get_summary success.",
        json_schema_extra={"x-habiba-default": "optional on the wire"},
    )


class AppControlPayload(ContractModel):
    intent: AppControlIntent
    mode: str | None = None


class AppTextInputPayload(ContractModel):
    text: str = Field(min_length=1, max_length=2000)


class ContextEnvelopePayload(ContractModel):
    """Wrapper used when the payload is a full ContextSnapshot."""

    snapshot: ContextSnapshot


# --- Envelope ---


class Envelope(ContractModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    session_id: str
    event_id: str
    turn_id: str | None = None
    timestamp: datetime
    context_revision: int | None = Field(
        default=None,
        ge=0,
        description="App snapshot revision this event is based on, when applicable.",
    )
    type: EventType
    payload: dict[str, Any]

    @field_validator("payload")
    @classmethod
    def validate_payload_shape(cls, payload: dict[str, Any], info: Any) -> dict[str, Any]:
        event_type = info.data.get("type")
        if event_type is None:
            return payload
        model = PAYLOAD_BY_TYPE.get(EventType(event_type))
        if model is None:
            return payload
        parsed = model.model_validate(payload)
        return parsed.model_dump(mode="json", exclude_none=True)


PAYLOAD_BY_TYPE: dict[EventType, type[ContractModel]] = {
    EventType.AGENT_STATUS: AgentStatusPayload,
    EventType.TRANSCRIPT_USER_PARTIAL: TranscriptUserPayload,
    EventType.TRANSCRIPT_USER_FINAL: TranscriptUserPayload,
    EventType.TRANSCRIPT_ASSISTANT: TranscriptAssistantPayload,
    EventType.AGENT_ACTION_REQUEST: ActionRequestPayload,
    EventType.AGENT_CLARIFICATION_REQUIRED: ClarificationRequiredPayload,
    EventType.AGENT_CONTROL: AgentControlPayload,
    EventType.AGENT_ERROR: AgentErrorPayload,
    EventType.APP_CONTEXT_SNAPSHOT: ContextSnapshot,
    EventType.APP_CONTEXT_UPDATED: ContextSnapshot,
    EventType.APP_ACTION_RESULT: ActionResultPayload,
    EventType.APP_CONTROL: AppControlPayload,
    EventType.APP_TEXT_INPUT: AppTextInputPayload,
}


class EnvelopeRoot(RootModel[Envelope]):
    root: Envelope


def json_schema_for(model: type[BaseModel]) -> dict[str, Any]:
    return model.model_json_schema(mode="validation")
