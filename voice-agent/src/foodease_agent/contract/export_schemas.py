"""Export Pydantic models to contract/v1/schemas/*.json."""

from __future__ import annotations

import json
from pathlib import Path

from foodease_agent.contract.models import (
    ARGS_BY_OPERATION,
    PAYLOAD_BY_TYPE,
    ActionResultPayload,
    ContextSnapshot,
    Envelope,
    json_schema_for,
)

ROOT = Path(__file__).resolve().parents[3]
SCHEMA_DIR = ROOT / "contract" / "v1" / "schemas"


def export_all() -> list[Path]:
    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    mapping: dict[str, dict] = {
        "envelope.json": json_schema_for(Envelope),
        "context_snapshot.json": json_schema_for(ContextSnapshot),
        "action_result_payload.json": json_schema_for(ActionResultPayload),
    }
    for event_type, model in PAYLOAD_BY_TYPE.items():
        name = f"payload_{event_type.value.replace('.', '_')}.json"
        mapping[name] = json_schema_for(model)
    for op, model in ARGS_BY_OPERATION.items():
        name = f"args_{op.value.replace('.', '_')}.json"
        mapping[name] = json_schema_for(model)

    # Annotate Habiba transport defaults on envelope meta schema companion.
    transport = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "HabibaTransportDefaults",
        "description": "Wire defaults where SPEC is silent. Marked x-habiba-default.",
        "x-habiba-default": {
            "action_transport": "livekit_rpc",
            "action_rpc_method": "foodease.action",
            "action_result": "rpc_response",
            "context_topic": "foodease.context",
            "control_topic": "foodease.control",
            "text_input_rpc_method": "foodease.text_input",
            "transcripts": "livekit_native_transcription_streams_mirrored_as_envelope_events",
            "agent_state": "livekit_native_agent_state_mirrored_as_agent.status",
            "max_payload_bytes": 15360,
            "max_payload_bytes_note": (
                "Conservative default under common LiveKit data/RPC practical limits; "
                "raise only after measuring the installed LiveKit version."
            ),
            "confirmation_token": "optional",
        },
        "type": "object",
    }
    mapping["transport_defaults.json"] = transport

    for filename, schema in mapping.items():
        path = SCHEMA_DIR / filename
        path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
        written.append(path)
    return written


def main() -> None:
    paths = export_all()
    print(f"Wrote {len(paths)} schemas to {SCHEMA_DIR}")


if __name__ == "__main__":
    main()
