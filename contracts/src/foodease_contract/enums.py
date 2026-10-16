"""Stable semantic enums for the shared integration contract 2.0."""

from __future__ import annotations

from enum import StrEnum

SCHEMA_VERSION = "2.0"

# item_id: application IDs only (no label matching).
ITEM_ID_PATTERN = r"^[a-z][a-z0-9_\-]{1,63}$"

# Quantity inclusive range (rejects 0 and absurdly large values like 99999).
QUANTITY_MIN = 1
QUANTITY_MAX = 99

# Bounded visible catalog rows in a context snapshot (prompt-safe).
VISIBLE_ITEMS_MAX = 25


class ProductState(StrEnum):
    """VA-07 product-level UI meanings."""

    OFF_AWAITING_CONSENT = "off/awaiting_consent"
    CONNECTING = "connecting"
    READY_LISTENING = "ready/listening"
    USER_SPEAKING = "user_speaking"
    THINKING = "thinking"
    ASSISTANT_SPEAKING = "assistant_speaking"
    WAITING_FOR_ACTION_RESULT = "waiting_for_action_result"
    IDLE = "idle"
    MUTED_PAUSED = "muted/paused"
    RECONNECTING = "reconnecting"
    ERROR = "error"
    ENDED = "ended"


class EventType(StrEnum):
    AGENT_STATUS = "agent.status"
    TRANSCRIPT_USER_PARTIAL = "transcript.user.partial"
    TRANSCRIPT_USER_FINAL = "transcript.user.final"
    TRANSCRIPT_ASSISTANT = "transcript.assistant"
    AGENT_ACTION_REQUEST = "agent.action_request"
    AGENT_CLARIFICATION_REQUIRED = "agent.clarification_required"
    AGENT_CONTROL = "agent.control"
    AGENT_ERROR = "agent.error"
    APP_CONTEXT_SNAPSHOT = "app.context_snapshot"
    APP_CONTEXT_UPDATED = "app.context_updated"
    APP_ACTION_RESULT = "app.action_result"
    APP_CONTROL = "app.control"
    APP_TEXT_INPUT = "app.text_input"


class Operation(StrEnum):
    NAVIGATE = "navigate"
    SEARCH_MENU = "search_menu"
    FILTER_MENU = "filter_menu"
    SELECT_ITEM = "select_item"
    GET_ITEM_DETAILS = "get_item_details"
    GET_CART = "get_cart"
    CART_ADD_ITEM = "cart.add_item"
    CART_SET_QUANTITY = "cart.set_quantity"
    CART_REMOVE_ITEM = "cart.remove_item"
    CHECKOUT_GET_SUMMARY = "checkout.get_summary"
    CHECKOUT_SUBMIT_DEMO_ORDER = "checkout.submit_demo_order"
    UNDO_LAST_REVERSIBLE_ACTION = "undo_last_reversible_action"
    GET_CURRENT_CONTEXT = "get_current_context"


class ActionResultStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    REJECTED = "rejected"
    STALE_CONTEXT = "stale_context"
    REQUIRES_CONFIRMATION = "requires_confirmation"
    TIMEOUT_UNKNOWN = "timeout_unknown"


class UserSafeErrorCode(StrEnum):
    """User-safe codes only — never provider stack traces."""

    UNKNOWN_OPERATION = "unknown_operation"
    INVALID_ARGUMENTS = "invalid_arguments"
    MISSING_ACTION_ID = "missing_action_id"
    STALE_CONTEXT = "stale_context"
    NOT_AVAILABLE = "not_available"
    OUT_OF_STOCK = "out_of_stock"
    CONFIRMATION_REQUIRED = "confirmation_required"
    CONFIRMATION_EXPIRED = "confirmation_expired"
    TIMEOUT = "timeout"
    REJECTED = "rejected"
    INTERNAL = "internal"
    RATE_LIMITED = "rate_limited"


class AssistantTranscriptPhase(StrEnum):
    STARTED = "started"
    UPDATED = "updated"
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"


class AgentControlIntent(StrEnum):
    MUTE = "mute"
    UNMUTE = "unmute"
    PAUSE = "pause"
    RESUME = "resume"
    END = "end"
    SWITCH_MODE = "switch_mode"


class AppControlIntent(StrEnum):
    START = "start"
    PAUSE = "pause"
    MUTE = "mute"
    UNMUTE = "unmute"
    END = "end"
    EXPLAIN = "explain"
    SWITCH_MODE = "switch_mode"
