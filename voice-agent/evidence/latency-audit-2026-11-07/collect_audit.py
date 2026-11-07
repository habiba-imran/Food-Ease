"""Offline evidence audit. No credentials, provider clients, audio, or live timing claims."""

from __future__ import annotations

import asyncio
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))

from livekit.agents import llm  # noqa: E402

from foodease_agent.integrated.agent import (  # noqa: E402
    POLICY,
    URDU_POLICY,
    IntegratedFoodEaseAgent,
)
from foodease_agent.integrated.output import guarded_output  # noqa: E402
from foodease_agent.integrated.runtime import LiveConversationRuntime  # noqa: E402
from foodease_agent.latency_report import percentile  # noqa: E402
from test_integrated_runtime import Session, WebsiteAdapter, call  # noqa: E402


def finite(value: str | None) -> float | None:
    try:
        result = float(value)  # type: ignore[arg-type]
        return result if math.isfinite(result) and result >= 0 else None
    except (TypeError, ValueError):
        return None


def summary(values: list[float]) -> dict:
    ordered = sorted(values)
    return {"n": len(ordered), "p50_ms": percentile(ordered, 50), "p95_ms": percentile(ordered, 95)}


def old_components() -> dict:
    results = {}
    groups: dict[str, list[float]] = defaultdict(list)
    source = ROOT / "evidence/phase-1/llm.csv"
    for row in csv.DictReader(source.open(encoding="utf-8")):
        if row["kind"] != "latency":
            continue
        value = finite(row["total_ms"])
        if value is not None:
            groups[row["model"] + "/" + row["thinking_level"]].append(value)
    results["llm"] = {
        "source": "voice-agent/evidence/phase-1/llm.csv",
        "meaning": "historical non-streaming completion time; not TTFT or current Urdu E2E",
        "groups": {key: summary(values) for key, values in groups.items()},
    }
    groups.clear()
    source = ROOT / "evidence/phase-1/tts.csv"
    for row in csv.DictReader(source.open(encoding="utf-8")):
        if row["kind"] != "timing":
            continue
        value = finite(row["ttfb_ms"])
        if value is not None:
            groups[row["voice"]].append(value)
    results["tts"] = {
        "source": "voice-agent/evidence/phase-1/tts.csv",
        "meaning": "historical English HTTP completed-body timing; not streaming TTFB; "
        "timing rows omit status/ok",
        "groups": {key: summary(values) for key, values in groups.items()},
    }
    return results


class CountingAdapter(WebsiteAdapter):
    def __init__(self):
        super().__init__()
        self.snapshot_calls = self.action_calls = 0

    async def get_snapshot(self):
        self.snapshot_calls += 1
        return await super().get_snapshot()

    async def submit(self, request):
        self.action_calls += 1
        return await super().submit(request)


async def structural_probe() -> dict:
    adapter, agent = CountingAdapter(), IntegratedFoodEaseAgent(language="ur")
    runtime = LiveConversationRuntime(agent, Session(), adapter)
    await runtime.prepare()
    await runtime.select_mode("voice")
    try:
        adapter.snapshot_calls = adapter.action_calls = 0
        result = await call(runtime, "get_cart", text="میری ٹوکری میں کیا ہے؟")
        assert result["status"] == "success"
        requests = {
            "fresh_context_requests": adapter.snapshot_calls,
            "requested_action": adapter.action_calls,
            "production_rpc_calls_per_successful_get_cart": adapter.snapshot_calls
            + adapter.action_calls,
        }
        context = json.dumps(runtime.reasoning_data(), ensure_ascii=False, separators=(",", ":"))
        schemas = [llm.utils.build_legacy_openai_schema(tool) for tool in agent.tools]
        schema_text = json.dumps(schemas, ensure_ascii=False, separators=(",", ":"))
        runtime.mode = "choosing"
        choosing = json.dumps(runtime.reasoning_data(), ensure_ascii=False, separators=(",", ":"))
        runtime.mode = "voice"
        chunks = 0
        released = None

        async def source():
            nonlocal chunks
            for value in ("آپ کی ٹوکری ", "خالی ہے", "۔ "):
                chunks += 1
                yield value

        async for value in guarded_output(source(), runtime, runtime.active_turn):
            if isinstance(value, str) and value.strip() and released is None:
                released = chunks
        assert released == 3
        return {
            "provenance": "offline structural probe; no wall-clock/provider timing measured",
            "application_action": requests,
            "sentence_gate": {
                "input_chunks": chunks,
                "first_text_after_chunk": released,
                "release_required_sentence_punctuation": True,
            },
            "request_footprint": {
                "urdu_policy_characters": len(POLICY + URDU_POLICY),
                "active_context_characters": len(context),
                "active_context_utf8_bytes": len(context.encode()),
                "tool_count": len(schemas),
                "all_tool_schema_characters": len(schema_text),
                "onboarding_context_characters": len(choosing),
                "note": "Exact character/byte counts only; "
                "not token estimates or a full chat size.",
            },
            "integrated_metric_handlers_registered": sorted(
                key
                for key in runtime._handlers
                if key in {"metrics_collected", "conversation_item_added", "session_usage_updated"}
            ),
        }
    finally:
        await runtime.close()


async def main() -> None:
    raw = sorted((ROOT / "evidence/phase-9").rglob("*.jsonl"))
    output = {
        "audit_date": "2026-11-07",
        "provider_requests_made": 0,
        "current_urdu_audible_latency_samples": 0,
        "phase9_raw_jsonl_files": [str(path.relative_to(ROOT)) for path in raw],
        "historical_components": old_components(),
        "structural_probe": await structural_probe(),
    }
    path = Path(__file__).with_name("audit.json")
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
