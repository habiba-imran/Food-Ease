"""Phase 1 contract checks against pinned historical website data, without providers.

Current authority API conformance is in website/tests/test_session_authority.py.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from pydantic import ValidationError
from tools.freeze_contract_v2 import build_artifacts, capture_website, check_artifacts

from foodease_agent.contract.models import ContextSnapshot as LegacySnapshot
from foodease_agent.contract.models import FilterMenuArgs as LegacyFilters
from foodease_agent.contract.v2.models import (
    ARG_MODELS,
    MAX_WIRE_BYTES,
    ActionRequest,
    ActionResult,
    ActionResultEvent,
    CartSummary,
    ContextEvent,
    ContextSnapshot,
    LookupResponse,
    SessionBinding,
    assert_authorized,
    assert_correlated,
    assert_lookup_correlated,
    assert_revision,
    decode_event,
    encode_event,
    normalize_filters,
    request_fingerprint,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def captured() -> dict:
    return capture_website()


def make_request(operation: str, arguments: dict | None = None) -> ActionRequest:
    return ActionRequest.model_validate(
        {
            "action_id": "a",
            "operation": operation,
            "arguments": arguments or {},
        }
    )


def test_original_website_mismatches_are_reproduced(captured: dict) -> None:
    with pytest.raises(ValidationError, match="line_total"):
        LegacySnapshot.model_validate(captured["legacy_nonempty_context"])
    with pytest.raises(ValidationError):
        LegacyFilters.model_validate({"category": "burgers", "vegetarian": True})
    # Existing broker reads cart, but the real domain emits lines.
    raw = captured["legacy_nonempty_cart"]
    assert raw["lines"] and not raw.get("cart")


def test_all_real_operations_validate_in_canonical_contract(captured: dict) -> None:
    assert len(captured["exchanges"]) == len(ARG_MODELS) == 13
    assert {x["request"]["payload"]["operation"] for x in captured["exchanges"]} == set(ARG_MODELS)
    for exchange in captured["exchanges"]:
        request = decode_event(exchange["request"])
        result = decode_event(exchange["result"])
        assert_correlated(request, result)
        assert isinstance(result, ActionResultEvent)
        assert result.payload.status == "success"
        assert decode_event(json.loads(encode_event(result))) == result
    empty, nonempty = captured["contexts"]
    first, second = decode_event(empty), decode_event(nonempty)
    assert isinstance(first, ContextEvent) and isinstance(second, ContextEvent)
    assert not first.payload.cart.lines
    assert second.payload.cart.lines[0].line_total == 850


def test_generated_schemas_and_handoff_copies_do_not_drift() -> None:
    check_artifacts()
    assert build_artifacts() == build_artifacts()


def test_every_example_validates_against_json_schema() -> None:
    artifacts = build_artifacts()
    schema = json.loads(artifacts["schemas/event.json"])
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    statuses = set()
    for name, content in artifacts.items():
        if name.startswith("examples/"):
            event = json.loads(content)
            validator.validate(event)
            parsed = decode_event(event)
            assert len(encode_event(parsed)) <= MAX_WIRE_BYTES
            if event["type"] == "app.action_result":
                statuses.add(event["payload"]["status"])
    assert statuses == {
        "success",
        "failed",
        "rejected",
        "stale_context",
        "requires_confirmation",
        "timeout_unknown",
    }


@pytest.mark.parametrize("quantity", [0, 100, -1, "2", 1.5, True])
def test_quantities_are_strict(quantity: object) -> None:
    with pytest.raises(ValidationError):
        make_request(
            "cart.add_item",
            {
                "item_id": "drink-cola",
                "quantity": quantity,
            },
        )


@pytest.mark.parametrize(
    "arguments",
    [
        {},
        {"confirmed": True},
        {"confirmed": False, "confirmation_token": "t", "summary_revision": 1},
        {"confirmed": "true", "confirmation_token": "t", "summary_revision": 1},
    ],
)
def test_checkout_requires_explicit_token_and_summary(arguments: dict) -> None:
    with pytest.raises(ValidationError):
        make_request("checkout.submit_demo_order", arguments)


def test_filter_normalization_is_explicit_and_preserves_category_budget() -> None:
    args = normalize_filters({"category": "burgers", "vegetarian": True, "max_price_pkr": 800})
    parsed = make_request("filter_menu", args)
    assert parsed.arguments == {
        "tags": ["vegetarian"],
        "category": "burgers",
        "max_price_pkr": 800.0,
    }
    with pytest.raises(ValueError):
        normalize_filters({"vegetarian": False, "tags": ["vegetarian"]})
    with pytest.raises(ValidationError):
        normalize_filters({"vegetarian": "yes"})
    for tags in ("spicy", {"spicy": True}, 3):
        with pytest.raises(ValidationError):
            normalize_filters({"vegetarian": True, "tags": tags})


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", "1.0"),
        ("schema_version", "3.0"),
        ("timestamp", "2026-10-17T12:00:00"),
        ("session_id", ""),
        ("unexpected", "forbidden"),
        ("context_revision", None),
        ("turn_id", None),
    ],
)
def test_invalid_envelope_metadata_is_rejected(captured: dict, field: str, value: object) -> None:
    event = copy.deepcopy(captured["exchanges"][0]["request"])
    event[field] = value
    with pytest.raises((ValidationError, ValueError)):
        decode_event(event)


@pytest.mark.parametrize("timestamp", [1234567890, "2026-10-17 12:00:00Z"])
def test_timestamp_requires_rfc3339_string(captured: dict, timestamp: object) -> None:
    event = copy.deepcopy(captured["exchanges"][0]["request"])
    event["timestamp"] = timestamp
    with pytest.raises(ValidationError):
        decode_event(event)


def test_context_session_and_revision_must_match_envelope(captured: dict) -> None:
    event = copy.deepcopy(captured["contexts"][0])
    event["payload"]["session_id"] = "another-session"
    with pytest.raises(ValidationError):
        decode_event(event)
    event = copy.deepcopy(captured["contexts"][0])
    event["context_revision"] += 1
    with pytest.raises(ValidationError):
        decode_event(event)


@pytest.mark.parametrize("target", ["session_id", "turn_id", "reply_to"])
def test_response_correlation(captured: dict, target: str) -> None:
    exchange = captured["exchanges"][0]
    result = copy.deepcopy(exchange["result"])
    result[target] = "wrong"
    with pytest.raises(ValueError):
        assert_correlated(decode_event(exchange["request"]), decode_event(result))


@pytest.mark.parametrize("target", ["action_id", "operation"])
def test_response_payload_correlation(captured: dict, target: str) -> None:
    exchange = captured["exchanges"][0]
    result = decode_event(exchange["result"])
    assert isinstance(result, ActionResultEvent)
    # Bypass model construction only to isolate the cross-message correlation guard.
    result.payload = result.payload.model_copy(update={target: "wrong"})
    with pytest.raises(ValueError):
        assert_correlated(decode_event(exchange["request"]), result)


def test_revision_equality_future_stale_and_read_exceptions() -> None:
    request = make_request(
        "cart.add_item",
        {
            "item_id": "drink-cola",
        },
    )
    assert_revision(request, expected=4, current=4)
    for revision in (3, 5):
        with pytest.raises(ValueError, match="stale_context"):
            assert_revision(request, expected=revision, current=4)
    read = make_request("get_cart")
    assert_revision(read, expected=2, current=4)
    with pytest.raises(ValueError, match="stale_context"):
        assert_revision(read, expected=5, current=4)


def test_idempotency_fingerprint_includes_session_operation_and_arguments() -> None:
    request = make_request("get_cart")
    assert request_fingerprint("s", request) == request_fingerprint("s", request)
    assert request_fingerprint("s", request) != request_fingerprint("other", request)
    changed = make_request("navigate", {"target": "home"})
    assert request_fingerprint("s", request) != request_fingerprint("s", changed)


def test_nonfinite_prices_and_false_cart_math_are_rejected(captured: dict) -> None:
    raw = copy.deepcopy(captured["legacy_nonempty_cart"])
    raw["total"] = float("nan")
    with pytest.raises(ValidationError):
        CartSummary.model_validate(raw)
    raw["total"] = 123
    with pytest.raises(ValidationError):
        CartSummary.model_validate(raw)


def test_byte_limit_counts_utf8_not_characters(captured: dict) -> None:
    event = copy.deepcopy(captured["contexts"][0])
    event["payload"]["language"] = "ض" * MAX_WIRE_BYTES
    with pytest.raises(ValueError, match="payload_too_large"):
        decode_event(event)


def test_unknown_fields_and_operation_fail_before_domain() -> None:
    with pytest.raises(ValidationError):
        make_request("execute_js")
    with pytest.raises(ValidationError):
        make_request(
            "cart.add_item",
            {
                "item_id": "drink-cola",
                "price": 1,
            },
        )


def test_lookup_has_explicit_not_seen_pending_expired_and_found(captured: dict) -> None:
    result = captured["exchanges"][0]["result"]
    identity = {
        "schema_version": "2.0",
        "session_id": result["session_id"],
        "event_id": "lookup-response",
        "reply_to": "lookup-request",
        "timestamp": "2026-10-17T12:00:00Z",
    }
    for status in ("not_seen", "pending", "expired"):
        assert LookupResponse(**identity, action_id="a", state=status).result is None
    response = LookupResponse(
        **identity, action_id=result["payload"]["action_id"], state="found", result=result
    )
    assert_lookup_correlated(
        {
            "session_id": result["session_id"],
            "event_id": "lookup-request",
            "action_id": result["payload"]["action_id"],
        },
        response,
    )
    with pytest.raises(ValidationError):
        LookupResponse(**identity, action_id="wrong", state="found", result=result)
    with pytest.raises(ValidationError):
        LookupResponse(**identity, action_id="a", state="found")
    with pytest.raises(ValueError):
        assert_lookup_correlated(
            {
                "session_id": "different",
                "event_id": "lookup-request",
                "action_id": response.action_id,
            },
            response,
        )
    unknown = copy.deepcopy(result)
    unknown["payload"].update(status="timeout_unknown", verified_state=None, error_code="timeout")
    with pytest.raises(ValidationError):
        LookupResponse(
            **identity, action_id=unknown["payload"]["action_id"], state="found", result=unknown
        )


def test_sender_and_session_are_bound(captured: dict) -> None:
    binding = SessionBinding(
        session_id="contract-demo", user_identity="u", app_identity="app", agent_identity="agent"
    )
    request = decode_event(captured["exchanges"][0]["request"])
    assert_authorized(request, binding, sender_identity="agent")
    for sender in ("u", "app", "stranger"):
        with pytest.raises(ValueError):
            assert_authorized(request, binding, sender_identity=sender)
    with pytest.raises(ValueError):
        assert_authorized(
            request, binding.model_copy(update={"session_id": "wrong"}), sender_identity="agent"
        )


def test_nested_snapshot_cannot_cross_session(captured: dict) -> None:
    event = copy.deepcopy(
        next(
            x["result"]
            for x in captured["exchanges"]
            if x["request"]["payload"]["operation"] == "get_current_context"
        )
    )
    event["payload"]["verified_state"]["snapshot"]["session_id"] = "other"
    with pytest.raises(ValidationError):
        decode_event(event)


def test_json_schema_rejects_malformed_argument_payloads(captured: dict) -> None:
    from jsonschema import ValidationError as SchemaError

    validator = Draft202012Validator(json.loads(build_artifacts()["schemas/event.json"]))
    event = copy.deepcopy(
        next(
            x["request"]
            for x in captured["exchanges"]
            if x["request"]["payload"]["operation"] == "cart.add_item"
        )
    )
    event["payload"]["arguments"]["quantity"] = "2"
    with pytest.raises(SchemaError):
        validator.validate(event)


def test_lookup_schema_includes_action_result_constraints() -> None:
    schema = json.loads(build_artifacts()["schemas/lookup_response.json"])
    assert "allOf" in schema["$defs"]["ActionResult"]


def test_failure_cannot_carry_a_successful_verified_state() -> None:
    with pytest.raises(ValidationError):
        ActionResult.model_validate(
            {
                "action_id": "a",
                "operation": "get_cart",
                "status": "timeout_unknown",
                "verified_state": {"cart": []},
                "error_code": "timeout",
            }
        )


def test_context_limits(captured: dict) -> None:
    raw = decode_event(captured["contexts"][1]).payload.model_dump(mode="json")
    raw["visible_items"] *= 26
    with pytest.raises(ValidationError):
        ContextSnapshot.model_validate(raw)


def test_negative_golden_fixtures_are_rejected() -> None:
    for name, content in build_artifacts().items():
        if name.startswith("negative/"):
            invalid = json.loads(content)
            with pytest.raises((ValidationError, ValueError)):
                if invalid["kind"] == "pair":
                    assert_correlated(
                        decode_event(invalid["request"]), decode_event(invalid["result"])
                    )
                else:
                    decode_event(invalid["event"])


def test_all_thirteen_event_types_have_validated_fixtures() -> None:
    from foodease_agent.contract.enums import EventType

    kinds = {
        json.loads(content)["type"]
        for name, content in build_artifacts().items()
        if name.startswith("examples/")
    }
    assert kinds == {kind.value for kind in EventType}


def test_lookup_fixtures_validate_against_schema_and_models() -> None:
    artifacts = build_artifacts()
    validator = Draft202012Validator(
        json.loads(artifacts["schemas/lookup_response.json"]), format_checker=FormatChecker()
    )
    for name, content in artifacts.items():
        if name.startswith("lookup_examples/"):
            payload = json.loads(content)
            validator.validate(payload)
            LookupResponse.model_validate(payload)


def test_drift_check_detects_modified_and_missing_handoff(tmp_path: Path) -> None:
    artifacts = build_artifacts()
    for name, content in artifacts.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    check_artifacts((tmp_path,))
    (tmp_path / "schemas/event.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="drift"):
        check_artifacts((tmp_path,))


def test_mock_cart_alias_requires_explicit_projection(captured: dict) -> None:
    from foodease_agent.contract.v2.projection import legacy_mock_cart

    raw = copy.deepcopy(captured["legacy_nonempty_cart"])
    raw["cart"] = raw.pop("lines")
    with pytest.raises(ValidationError):
        CartSummary.model_validate(raw)
    assert CartSummary.model_validate(legacy_mock_cart(raw)).total == 900


def test_read_and_clear_search_bounds() -> None:
    assert make_request("search_menu", {"query": ""}).arguments["query"] == ""
    with pytest.raises(ValidationError):
        make_request("search_menu", {"query": "a" * 201})


def test_checkout_summary_requires_token_and_demo_receipt_is_simulated(captured: dict) -> None:
    summary = copy.deepcopy(captured["exchanges"][-2]["result"])
    summary["payload"]["confirmation_token"] = None
    with pytest.raises(ValidationError):
        decode_event(summary)
    receipt = copy.deepcopy(captured["exchanges"][-1]["result"])
    receipt["payload"]["verified_state"]["demo"] = False
    with pytest.raises(ValidationError):
        decode_event(receipt)
