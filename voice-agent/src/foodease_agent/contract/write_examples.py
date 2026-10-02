"""Write golden envelope examples under contract/v1/examples/."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from foodease_agent.contract.enums import (
    ActionResultStatus,
    EventType,
    Operation,
    ProductState,
    UserSafeErrorCode,
)
from foodease_agent.contract.models import Envelope

ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = ROOT / "contract" / "v1" / "examples"

TS = datetime(2026, 10, 2, 12, 0, 0, tzinfo=UTC)
SESSION = "demo-session-7"


def env(
    event_type: EventType,
    payload: dict,
    *,
    event_id: str,
    turn_id: str | None = "turn-15",
    context_revision: int | None = 8,
) -> dict:
    envelope = Envelope(
        session_id=SESSION,
        event_id=event_id,
        turn_id=turn_id,
        timestamp=TS,
        context_revision=context_revision,
        type=event_type,
        payload=payload,
    )
    return envelope.model_dump(mode="json")


def snapshot(revision: int = 8) -> dict:
    return {
        "schema_version": "1.0",
        "session_id": SESSION,
        "revision": revision,
        "route": "menu",
        "focus_item_id": None,
        "valid_actions": ["search_menu", "filter_menu", "cart.add_item", "navigate"],
        "valid_navigation_targets": ["home", "back", "cart", "checkout"],
        "filter_tags": [],
        "search_query": None,
        "visible_items": [
            {
                "item_id": "wrap-hot-chicken",
                "name": "Hot Chicken Wrap",
                "price": 850,
                "currency": "PKR",
                "descriptors": ["spicy"],
                "available": True,
            }
        ],
        "cart": {
            "lines": [],
            "currency": "PKR",
            "subtotal": 0,
            "fees": [],
            "total": 0,
        },
        "checkout_available": False,
        "action_pending": False,
        "language": "en",
        "spoken_feedback_preference": None,
    }


def write(name: str, data: dict) -> None:
    EXAMPLES.mkdir(parents=True, exist_ok=True)
    path = EXAMPLES / name
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print("wrote", path.relative_to(ROOT))


def main() -> None:
    write(
        "action_add_item.json",
        env(
            EventType.AGENT_ACTION_REQUEST,
            {
                "action_id": "action-add-1",
                "operation": Operation.CART_ADD_ITEM.value,
                "arguments": {"item_id": "wrap-hot-chicken", "quantity": 2},
            },
            event_id="event-add-1",
        ),
    )
    write(
        "action_set_quantity.json",
        env(
            EventType.AGENT_ACTION_REQUEST,
            {
                "action_id": "action-qty-1",
                "operation": Operation.CART_SET_QUANTITY.value,
                "arguments": {"item_id": "wrap-hot-chicken", "quantity": 1},
            },
            event_id="event-qty-1",
        ),
    )
    write(
        "result_success.json",
        env(
            EventType.APP_ACTION_RESULT,
            {
                "action_id": "action-qty-1",
                "status": ActionResultStatus.SUCCESS.value,
                "verified_state": {
                    "cart": [
                        {
                            "item_id": "wrap-hot-chicken",
                            "name": "Hot Chicken Wrap",
                            "quantity": 1,
                            "unit_price": 850,
                        }
                    ],
                    "currency": "PKR",
                    "total": 850,
                },
            },
            event_id="event-qty-1-result",
            context_revision=9,
        ),
    )
    write(
        "result_stale_context.json",
        env(
            EventType.APP_ACTION_RESULT,
            {
                "action_id": "action-stale-1",
                "status": ActionResultStatus.STALE_CONTEXT.value,
                "error_code": UserSafeErrorCode.STALE_CONTEXT.value,
                "error_message": "Cart changed in the app. Please try again.",
            },
            event_id="event-stale-1",
            context_revision=10,
        ),
    )
    write(
        "result_rejected.json",
        env(
            EventType.APP_ACTION_RESULT,
            {
                "action_id": "action-rej-1",
                "status": ActionResultStatus.REJECTED.value,
                "error_code": UserSafeErrorCode.OUT_OF_STOCK.value,
                "error_message": "That item is not available.",
            },
            event_id="event-rej-1",
        ),
    )
    write(
        "result_requires_confirmation.json",
        env(
            EventType.APP_ACTION_RESULT,
            {
                "action_id": "action-confirm-1",
                "status": ActionResultStatus.REQUIRES_CONFIRMATION.value,
                "error_code": UserSafeErrorCode.CONFIRMATION_REQUIRED.value,
                "error_message": "Please confirm the demo order total.",
                "verified_state": {"total": 1700, "currency": "PKR"},
            },
            event_id="event-confirm-1",
        ),
    )
    write(
        "result_timeout_unknown.json",
        env(
            EventType.APP_ACTION_RESULT,
            {
                "action_id": "action-timeout-1",
                "status": ActionResultStatus.TIMEOUT_UNKNOWN.value,
                "error_code": UserSafeErrorCode.TIMEOUT.value,
                "error_message": "No confirmation from the app yet.",
            },
            event_id="event-timeout-1",
        ),
    )
    write(
        "result_duplicate_action_id.json",
        env(
            EventType.APP_ACTION_RESULT,
            {
                "action_id": "action-qty-1",
                "status": ActionResultStatus.SUCCESS.value,
                "verified_state": {
                    "note": "Prior outcome returned; no second mutation",
                    "total": 850,
                    "currency": "PKR",
                },
            },
            event_id="event-dup-1",
            context_revision=9,
        ),
    )
    write(
        "checkout_summary_with_token.json",
        env(
            EventType.APP_ACTION_RESULT,
            {
                "action_id": "action-sum-1",
                "status": ActionResultStatus.SUCCESS.value,
                "confirmation_token": "tok_demo_abc",
                "verified_state": {"total": 1700, "currency": "PKR"},
            },
            event_id="event-sum-1",
            context_revision=11,
        ),
    )
    write(
        "checkout_summary_without_token.json",
        env(
            EventType.APP_ACTION_RESULT,
            {
                "action_id": "action-sum-2",
                "status": ActionResultStatus.SUCCESS.value,
                "verified_state": {"total": 1700, "currency": "PKR"},
            },
            event_id="event-sum-2",
            context_revision=11,
        ),
    )
    write(
        "checkout_submit_with_token.json",
        env(
            EventType.AGENT_ACTION_REQUEST,
            {
                "action_id": "action-submit-1",
                "operation": Operation.CHECKOUT_SUBMIT_DEMO_ORDER.value,
                "arguments": {"confirmed": True, "confirmation_token": "tok_demo_abc"},
            },
            event_id="event-submit-1",
            context_revision=11,
        ),
    )
    write(
        "checkout_submit_without_token.json",
        env(
            EventType.AGENT_ACTION_REQUEST,
            {
                "action_id": "action-submit-2",
                "operation": Operation.CHECKOUT_SUBMIT_DEMO_ORDER.value,
                "arguments": {"confirmed": True},
            },
            event_id="event-submit-2",
            context_revision=11,
        ),
    )
    write(
        "context_snapshot_reconnect.json",
        env(
            EventType.APP_CONTEXT_SNAPSHOT,
            snapshot(revision=12),
            event_id="event-snap-reconnect",
            turn_id=None,
            context_revision=12,
        ),
    )
    write(
        "agent_status_listening.json",
        env(
            EventType.AGENT_STATUS,
            {"state": ProductState.READY_LISTENING.value, "detail": "ready"},
            event_id="event-status-1",
            turn_id=None,
            context_revision=None,
        ),
    )


if __name__ == "__main__":
    main()
