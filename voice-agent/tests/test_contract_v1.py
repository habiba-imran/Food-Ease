"""Contract v1 verification tests (V2.1–V2.4)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from foodease_agent.contract.enums import EventType, Operation
from foodease_agent.contract.export_schemas import SCHEMA_DIR, export_all
from foodease_agent.contract.models import (
    ARGS_BY_OPERATION,
    ActionRequestPayload,
    Envelope,
    json_schema_for,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "contract" / "v1" / "examples"


def test_schema_drift_envelope() -> None:
    """V2.3: committed envelope schema matches Pydantic export."""
    assert SCHEMA_DIR.exists(), "Run: uv run python -m foodease_agent.contract.export_schemas"
    on_disk = json.loads((SCHEMA_DIR / "envelope.json").read_text(encoding="utf-8"))
    fresh = json_schema_for(Envelope)
    assert on_disk == fresh


def test_export_schemas_roundtrip() -> None:
    paths = export_all()
    assert len(paths) >= 20
    on_disk = json.loads((SCHEMA_DIR / "envelope.json").read_text(encoding="utf-8"))
    assert on_disk == json_schema_for(Envelope)


@pytest.mark.parametrize("path", sorted(EXAMPLES.glob("*.json")) if EXAMPLES.exists() else [])
def test_golden_examples_validate(path: Path) -> None:
    """V2.1: every golden example validates as an Envelope."""
    data = json.loads(path.read_text(encoding="utf-8"))
    Envelope.model_validate(data)


def test_examples_exist_for_required_scenarios() -> None:
    required = {
        "action_add_item.json",
        "action_set_quantity.json",
        "result_stale_context.json",
        "result_rejected.json",
        "result_requires_confirmation.json",
        "result_timeout_unknown.json",
        "result_duplicate_action_id.json",
        "checkout_summary_with_token.json",
        "checkout_summary_without_token.json",
        "checkout_submit_with_token.json",
        "checkout_submit_without_token.json",
        "context_snapshot_reconnect.json",
    }
    present = {p.name for p in EXAMPLES.glob("*.json")}
    missing = required - present
    assert not missing, f"Missing golden examples: {missing}"


def test_optional_fields_have_without_examples() -> None:
    """V2.4: optional confirmation_token has golden examples without it."""
    assert (EXAMPLES / "checkout_summary_without_token.json").exists()
    assert (EXAMPLES / "checkout_submit_without_token.json").exists()
    summary_path = EXAMPLES / "checkout_summary_without_token.json"
    submit_path = EXAMPLES / "checkout_submit_without_token.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    submit = json.loads(submit_path.read_text(encoding="utf-8"))
    assert "confirmation_token" not in summary["payload"]
    assert "confirmation_token" not in submit["payload"]["arguments"]


def test_negative_unknown_operation() -> None:
    with pytest.raises(ValidationError):
        ActionRequestPayload.model_validate(
            {
                "action_id": "a1",
                "operation": "drop_table",
                "arguments": {},
            }
        )


def test_negative_missing_action_id() -> None:
    with pytest.raises(ValidationError):
        ActionRequestPayload.model_validate(
            {
                "operation": Operation.GET_CART.value,
                "arguments": {},
            }
        )


@pytest.mark.parametrize("qty", [0, 99999, -1])
def test_negative_quantity(qty: int) -> None:
    with pytest.raises(ValidationError):
        ActionRequestPayload.model_validate(
            {
                "action_id": "a1",
                "operation": Operation.CART_SET_QUANTITY.value,
                "arguments": {"item_id": "wrap-hot-chicken", "quantity": qty},
            }
        )


def test_negative_wrong_types() -> None:
    with pytest.raises(ValidationError):
        ActionRequestPayload.model_validate(
            {
                "action_id": "a1",
                "operation": Operation.CART_ADD_ITEM.value,
                "arguments": {"item_id": "wrap-hot-chicken", "quantity": "two"},
            }
        )


def test_negative_bad_item_id() -> None:
    with pytest.raises(ValidationError):
        ActionRequestPayload.model_validate(
            {
                "action_id": "a1",
                "operation": Operation.SELECT_ITEM.value,
                "arguments": {"item_id": "Hot Chicken!!"},
            }
        )


def test_all_operations_have_arg_models() -> None:
    assert set(ARGS_BY_OPERATION) == set(Operation)


def test_envelope_rejects_unknown_event_type() -> None:
    with pytest.raises(ValidationError):
        Envelope.model_validate(
            {
                "schema_version": "1.0",
                "session_id": "s",
                "event_id": "e",
                "timestamp": "2026-10-02T12:00:00Z",
                "type": "agent.hack",
                "payload": {},
            }
        )


def test_event_types_cover_va11_va12() -> None:
    required = {
        "agent.status",
        "transcript.user.partial",
        "transcript.user.final",
        "transcript.assistant",
        "agent.action_request",
        "agent.clarification_required",
        "agent.control",
        "agent.error",
        "app.context_snapshot",
        "app.context_updated",
        "app.action_result",
        "app.control",
        "app.text_input",
    }
    assert required == {e.value for e in EventType}
