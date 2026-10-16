"""Generate/check v2 schemas and historical real-website fixtures in both handoff trees.

Only model/data code runs. No .env, worker, HTTP server or provider is used.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from foodease_agent.contract.v2.models import (
    ARG_MODELS,
    EVENT_ADAPTER,
    MAX_WIRE_BYTES,
    RESULT_MODELS,
    ActionResult,
    ContextSnapshot,
    LookupRequest,
    LookupResponse,
)

ROOT = Path(__file__).resolve().parents[2]
TREES = (ROOT / "voice-agent/contract/v2", ROOT / "zainab-pack/contract/v2")
TIMESTAMP = "2026-10-17T12:00:00Z"  # Fixed fixture time, not a runtime measurement.
SESSION = "contract-demo"


def metadata(kind: str, event_id: str, revision: int = 1) -> dict[str, Any]:
    return {
        "schema_version": "2.0",
        "session_id": SESSION,
        "event_id": event_id,
        "turn_id": "contract-turn",
        "timestamp": TIMESTAMP,
        "context_revision": revision,
        "type": kind,
    }


def capture_website() -> dict[str, Any]:
    """Load the hash-pinned real-domain capture recorded during Phase 1.

    Phase 2 deliberately changes session IDs, random tokens and summary revision
    semantics. Historical golden examples must not silently become a new capture.
    Current authority conformance runs against the actual HTTP API in website/tests.
    """
    pins = json.loads(
        (Path(__file__).with_name("contract_v2_capture_sha256.json")).read_text(encoding="utf-8")
    )

    def recorded(name: str) -> dict[str, Any]:
        content = (TREES[0] / "examples" / name).read_bytes()
        if hashlib.sha256(content).hexdigest() != pins[name]:
            raise ValueError(f"Phase 1 capture changed: {name}")
        return json.loads(content)

    exchanges = [
        {kind: recorded(f"{index:02d}_{kind}.json") for kind in ("request", "result")}
        for index in range(1, 14)
    ]
    contexts = [recorded(f"context_{index}.json") for index in range(2)]
    legacy = copy.deepcopy(contexts[1]["payload"])
    legacy["schema_version"] = "1.0"
    legacy.pop("category")
    legacy.pop("max_price_pkr")
    negatives, revisions = {}, {}
    for status in ("rejected", "stale_context", "requires_confirmation"):
        event = recorded(f"status_{status}.json")
        raw = event["payload"]
        raw.pop("operation")
        negatives[status] = raw
        revisions[status] = event["context_revision"]
    return {
        "exchanges": exchanges,
        "contexts": contexts,
        "legacy_nonempty_context": legacy,
        "legacy_nonempty_cart": legacy["cart"],
        "negative_results": negatives,
        "negative_revisions": revisions,
    }


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"


def event_schema() -> dict[str, Any]:
    schema = EVENT_ADAPTER.json_schema()
    definitions = schema["$defs"]
    # Pydantic validators enforce operation-dependent dicts at runtime. Export
    # equivalent JSON Schema conditionals so non-Python clients enforce them too.
    for model, mapping, field in (
        ("ActionRequest", ARG_MODELS, "arguments"),
        ("ActionResult", RESULT_MODELS, "verified_state"),
    ):
        conditions = []
        for operation, payload_model in mapping.items():
            payload_schema = payload_model.model_json_schema()
            definitions.update(payload_schema.pop("$defs", {}))
            definitions[payload_model.__name__] = payload_schema
            conditions.append(
                {
                    "if": {
                        "properties": {
                            "operation": {"const": operation},
                            **({"status": {"const": "success"}} if model == "ActionResult" else {}),
                        }
                    },
                    "then": {"properties": {field: payload_schema}},
                }
            )
        definitions[model]["allOf"] = conditions
    definitions["SubmitArgs"] = ARG_MODELS["checkout.submit_demo_order"].model_json_schema()
    # A validator rejects false; publish that requirement as a literal in JSON Schema.
    for condition in definitions["ActionRequest"]["allOf"]:
        args_schema = condition["then"]["properties"]["arguments"]
        if "confirmed" in args_schema.get("properties", {}):
            args_schema["properties"]["confirmed"]["const"] = True
    definitions["ActionResult"]["allOf"].extend(
        [
            {
                "if": {"properties": {"status": {"const": "success"}}},
                "then": {
                    "required": ["verified_state"],
                    "properties": {"error_code": {"type": "null"}},
                },
                "else": {
                    "required": ["error_code"],
                    "properties": {
                        "error_code": {"type": "string"},
                        "verified_state": {"type": "null"},
                    },
                },
            },
            {
                "if": {
                    "properties": {
                        "status": {"const": "success"},
                        "operation": {"const": "checkout.get_summary"},
                    }
                },
                "then": {
                    "required": ["confirmation_token"],
                    "properties": {"confirmation_token": {"type": "string", "minLength": 1}},
                },
            },
        ]
    )
    for status, code in {
        "timeout_unknown": "timeout",
        "stale_context": "stale_context",
        "requires_confirmation": "confirmation_required",
    }.items():
        definitions["ActionResult"]["allOf"].append(
            {
                "if": {"properties": {"status": {"const": status}}},
                "then": {"properties": {"error_code": {"const": code}}},
            }
        )
    definitions["ActionResult"]["allOf"].append(
        {
            "if": {
                "not": {
                    "properties": {
                        "status": {"const": "success"},
                        "operation": {"const": "checkout.get_summary"},
                    }
                }
            },
            "then": {"properties": {"confirmation_token": {"type": "null"}}},
        }
    )
    definitions["DemoReceipt"]["properties"]["demo"]["const"] = True
    for name in ("Control", "AgentControl"):
        definitions[name]["allOf"] = [
            {
                "if": {"properties": {"intent": {"const": "switch_mode"}}},
                "then": {"required": ["mode"], "properties": {"mode": {"type": "string"}}},
            }
        ]
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    return schema


def build_artifacts() -> dict[str, str]:
    captured = capture_website()
    event = event_schema()
    artifacts = {"schemas/event.json": dump(event)}
    for name, model in {
        "context": ContextSnapshot,
        "lookup_request": LookupRequest,
        "lookup_response": LookupResponse,
    }.items():
        schema = model.model_json_schema()
        if name == "lookup_response":
            schema["$defs"].update(event["$defs"])
            schema["allOf"] = [
                {
                    "if": {"properties": {"state": {"const": "found"}}},
                    "then": {"required": ["result"], "properties": {"result": {"type": "object"}}},
                    "else": {"properties": {"result": {"type": "null"}}},
                }
            ]
            schema["allOf"][0]["then"]["properties"]["result"]["properties"] = {
                "payload": {"properties": {"status": {"not": {"const": "timeout_unknown"}}}},
            }
        artifacts[f"schemas/{name}.json"] = dump(schema)
    for operation, model in ARG_MODELS.items():
        schema = model.model_json_schema()
        if operation == "checkout.submit_demo_order":
            schema["properties"]["confirmed"]["const"] = True
        artifacts[f"schemas/args_{operation.replace('.', '_')}.json"] = dump(schema)
    for index, exchange in enumerate(captured["exchanges"], 1):
        for kind, event in exchange.items():
            artifacts[f"examples/{index:02d}_{kind}.json"] = dump(event)
    for index, event in enumerate(captured["contexts"]):
        artifacts[f"examples/context_{index}.json"] = dump(event)
    # Only failed/timeout are synthetic; the other statuses come from the domain.
    for status, error in {
        "failed": "internal",
        "rejected": "out_of_stock",
        "stale_context": "stale_context",
        "requires_confirmation": "confirmation_required",
        "timeout_unknown": "timeout",
    }.items():
        raw = captured["negative_results"].get(status)
        payload = (
            {
                **raw,
                "operation": (
                    "checkout.submit_demo_order"
                    if status == "requires_confirmation"
                    else "cart.add_item"
                ),
            }
            if raw is not None
            else ActionResult.model_validate(
                {
                    "action_id": "status-action",
                    "operation": "cart.add_item",
                    "status": status,
                    "error_code": error,
                }
            ).model_dump(mode="json")
        )
        event = {
            **metadata(
                "app.action_result",
                f"result-{status}",
                captured["negative_revisions"].get(status, 1),
            ),
            "reply_to": "request-status",
            "payload": payload,
        }
        artifacts[f"examples/status_{status}.json"] = dump(event)
    event_payloads = {
        "agent.status": {"state": "ready/listening"},
        "transcript.user.partial": {"utterance_id": "user-1", "text": "show", "source": "speech"},
        "transcript.user.final": {
            "utterance_id": "user-1",
            "text": "show wraps",
            "source": "speech",
        },
        "app.text_input": {"text": "show wraps"},
        "app.control": {"intent": "switch_mode", "mode": "manual"},
        "agent.control": {"intent": "switch_mode", "mode": "manual"},
        "agent.error": {
            "code": "not_available",
            "message": "Assistance is unavailable.",
            "fatal": False,
        },
        "agent.clarification_required": {
            "question": "Which wrap?",
            "choices": [
                {"id": "wrap-veg", "label": "Veggie Wrap"},
            ],
        },
        "app.context_updated": captured["contexts"][1]["payload"],
    }
    for kind, payload in event_payloads.items():
        revision = payload["revision"] if kind == "app.context_updated" else 1
        artifacts[f"examples/event_{kind.replace('.', '_')}.json"] = dump(
            {
                **metadata(kind, f"event-{kind}", revision),
                "payload": payload,
            }
        )
    for phase, spoken in {
        "started": "",
        "updated": "Here are",
        "completed": "Here are the wraps.",
        "interrupted": "Here are",
    }.items():
        artifacts[f"examples/transcript_assistant_{phase}.json"] = dump(
            {
                **metadata("transcript.assistant", f"assistant-{phase}"),
                "payload": {
                    "utterance_id": f"assistant-example-{phase}",
                    "text": spoken,
                    "phase": phase,
                },
            }
        )
    first_result = captured["exchanges"][0]["result"]
    for state in ("not_seen", "pending", "expired", "found"):
        artifacts[f"lookup_examples/{state}.json"] = dump(
            LookupResponse.model_validate(
                {
                    "schema_version": "2.0",
                    "session_id": SESSION,
                    "event_id": f"lookup-{state}",
                    "reply_to": "lookup-request",
                    "timestamp": TIMESTAMP,
                    "action_id": first_result["payload"]["action_id"],
                    "state": state,
                    "result": first_result if state == "found" else None,
                }
            ).model_dump(mode="json")
        )
    negatives = {}
    original = captured["exchanges"][5]["request"]
    for name, field, value in (
        ("unsupported_version", "schema_version", "1.0"),
        ("missing_version", "schema_version", None),
        ("missing_revision", "context_revision", None),
        ("forbidden_field", "execute", "arbitrary code"),
        ("wrong_quantity_type", "quantity", "2"),
        ("missing_action_id", "action_id", None),
    ):
        invalid = copy.deepcopy(original)
        target = invalid
        if field == "quantity":
            target = invalid["payload"]["arguments"]
        elif field == "action_id":
            target = invalid["payload"]
        if value is None:
            target.pop(field, None)
        else:
            target[field] = value
        negatives[name] = {"kind": "event", "event": invalid}
    invalid_context = copy.deepcopy(captured["contexts"][0])
    invalid_context["payload"]["session_id"] = "foreign-session"
    negatives["nested_session_mismatch"] = {"kind": "event", "event": invalid_context}
    for name, field in (("action_mismatch", "action_id"), ("operation_mismatch", "operation")):
        pair = copy.deepcopy(captured["exchanges"][0])
        if field == "action_id":
            pair["result"]["payload"][field] = "foreign-action"
        else:
            pair["result"]["payload"].update(
                operation="select_item",
                verified_state=copy.deepcopy(
                    captured["exchanges"][3]["result"]["payload"]["verified_state"]
                ),
            )
        negatives[name] = {"kind": "pair", **pair}
    for name, invalid in negatives.items():
        artifacts[f"negative/{name}.json"] = dump(invalid)
    artifacts["schemas/transport.json"] = dump(
        {
            "schema_version": "2.0",
            "max_wire_bytes": MAX_WIRE_BYTES,
            "action_rpc": "foodease.action.v2",
            "lookup_rpc": "foodease.action_status.v2",
            "context_topic": "foodease.context.v2",
            "control_topic": "foodease.control.v2",
            "text_topic": "foodease.text_input.v2",
            "agent_events_topic": "foodease.events.v2",
            "http_action_status": "GET /api/v2/app/actions/{action_id}",
            "rpc_timeout_seconds": 5,
            "session_idle_ttl_seconds": 1800,
            "session_absolute_ttl_seconds": 7200,
            "result_retention": "entire shopping session",
            "idempotency_key": ["session_id", "action_id"],
            "lookup_states": ["not_seen", "pending", "found", "expired"],
            "source": "Project defaults; endpoints and runtime enforcement are future phases",
        }
    )
    artifacts["MANIFEST.json"] = dump(
        {
            "schema_version": "2.0",
            "canonical_models": "foodease_agent.contract.v2.models",
            "actual_website_operations": sorted(ARG_MODELS),
            "synthetic_status_examples": ["status_failed", "status_timeout_unknown"],
            "actual_domain_status_examples": ["rejected", "stale_context", "requires_confirmation"],
            "non_action_event_examples": "Authored contract examples, not live session evidence",
            "runtime_activated": False,
        }
    )
    contract_readme = TREES[0] / "README.md"
    if contract_readme.exists():
        artifacts["README.md"] = contract_readme.read_text(encoding="utf-8")
    return artifacts


def check_artifacts(trees: tuple[Path, ...] = TREES) -> None:
    expected = build_artifacts()
    for tree in trees:
        generated = {
            path.relative_to(tree).as_posix(): path.read_text(encoding="utf-8")
            for path in tree.rglob("*")
            if path.is_file() and (path.suffix == ".json" or path.name == "README.md")
        }
        if generated != expected:
            raise ValueError(f"Contract drift: {tree}; regenerate with freeze_contract_v2.py")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        check_artifacts()
        print("PASS v2 models, pinned Phase 1 domain examples and both generated trees match")
    else:
        for tree in TREES:
            for relative, content in build_artifacts().items():
                path = tree / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
        print("Generated v2 artifacts in both trees; frozen v1 untouched")


if __name__ == "__main__":
    main()
