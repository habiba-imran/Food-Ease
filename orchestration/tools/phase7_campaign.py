"""Prepare offline, or explicitly opt into a bounded real Google-model campaign.

No dotenv, Cloud/RTC, microphone or TTS. Uses actual website HTTP authority and
integrated SDK agent/tools. A headless text receipt is not browser/audio evidence.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
import os
from pathlib import Path
from uuid import uuid4

from phase7_cases import campaign_cases

ROOT = Path(__file__).resolve().parents[2]


def prepare(output: Path) -> list[dict]:
    output.mkdir(parents=True, exist_ok=True)
    cases = campaign_cases()
    (output / "cases.json").write_text(json.dumps(cases, indent=2), encoding="utf-8")
    manifest = {
        "status": "prepared_not_run",
        "cases": len(cases),
        "planned_user_turns": sum(len(case["utterances"]) for case in cases),
        "real_model_turns": 0,
        "human_listeners": 0,
        "minimum_real_model_turns": 40,
        "minimum_listeners": 3,
        "required_median_rating": 4,
        "model_quality_gate": "not_evaluated",
        "physical_audio_gate": "not_evaluated",
        "metrics": {
            "tool_accuracy": None,
            "unnecessary_clarifications": None,
            "false_success": None,
            "duplicates": None,
            "human_rating_medians": None,
        },
    }
    if not (output / "manifest.json").exists():
        (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    ratings = output / "listening-ratings.csv"
    if not ratings.exists():
        with ratings.open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    "case_id",
                    "turn",
                    "listener_id",
                    "live_audio_reference",
                    "naturalness",
                    "relevance",
                    "brevity",
                    "comfort",
                    "notes",
                ]
            )
            for case in cases:
                for index, _ in enumerate(case["utterances"], 1):
                    writer.writerow([case["id"], index, "", "", "", "", "", "", ""])
    return cases


async def run(output: Path, cases: list[dict], *, model: str, thinking: str, request_limit: int):
    import httpx
    from foodease_agent.adapters.integrated import action_request
    from foodease_agent.integrated.agent import IntegratedFoodEaseAgent
    from foodease_agent.integrated.runtime import LiveConversationRuntime
    from foodease_contract.models import ActionResultEvent, ContextSnapshot
    from foodease_website.app import create_app
    from google.genai.types import HttpOptions, HttpRetryOptions, ThinkingConfig, ThinkingLevel
    from livekit.agents import AgentSession, llm
    from livekit.agents.voice.io import TextOutput
    from livekit.plugins import google

    # SDK/provider exception messages can include transport data. Save only types.
    logging.disable(logging.CRITICAL)
    requests = 0

    class CountedGoogle(google.LLM):
        def chat(self, **kwargs):
            nonlocal requests
            from livekit.agents import APIConnectOptions

            kwargs["conn_options"] = APIConnectOptions(max_retry=0, timeout=20)
            if requests >= request_limit:
                raise RuntimeError("campaign request budget exhausted")
            requests += 1
            return super().chat(**kwargs)

    provider = CountedGoogle(
        model=model,
        thinking_config=ThinkingConfig(thinking_level=ThinkingLevel(thinking.upper())),
        max_output_tokens=768,
        http_options=HttpOptions(retry_options=HttpRetryOptions(attempts=1)),
    )

    class Sink(TextOutput):
        def __init__(self):
            super().__init__(label="headless-campaign", next_in_chain=None)

        async def capture_text(self, text):
            pass

        def flush(self):
            pass

    class Adapter:
        def __init__(self, client, sid):
            self.client, self.sid = client, sid
            self.actions: list[dict] = []
            self.summaries: list[str] = []

        async def get_snapshot(self):
            response = await self.client.get("/api/v2/app/context")
            response.raise_for_status()
            return ContextSnapshot.model_validate(response.json())

        async def submit(self, request):
            response = await self.client.post(
                "/api/v2/app/action", json=request.model_dump(mode="json")
            )
            response.raise_for_status()
            result = ActionResultEvent.model_validate(response.json())
            self.actions.append(
                {
                    "operation": request.payload.operation,
                    "arguments": {
                        key: value
                        for key, value in request.payload.arguments.items()
                        if key != "confirmation_token"
                    },
                    "status": result.payload.status,
                    "revision": result.context_revision,
                }
            )
            return result

        async def lookup(self, action_id):
            response = await self.client.get(
                f"/api/v2/app/actions/{action_id}", headers={"X-FoodEase-Event-Id": uuid4().hex}
            )
            response.raise_for_status()
            from foodease_contract.models import LookupResponse

            return LookupResponse.model_validate(response.json())

        async def present_summary(self, **kwargs):
            self.summaries.append(kwargs["text"])
            return True  # Explicit headless text receipt; never a browser/audio receipt.

        async def publish_control(self, intent: str, mode: str | None = None):
            pass

        async def publish_event(self, *args, **kwargs):
            pass

    results = []
    try:
        for case in cases:
            if requests >= request_limit:
                break
            client = httpx.AsyncClient(
                transport=httpx.ASGITransport(app=create_app()), base_url="http://campaign.test"
            )
            async with client:
                response = await client.post("/api/v2/app/sessions", json={})
                response.raise_for_status()
                sid = response.json()["session_id"]
                client.headers["X-FoodEase-Session"] = sid
                adapter = Adapter(client, sid)
                for step in case["setup"]:
                    snapshot = await adapter.get_snapshot()
                    await adapter.submit(
                        action_request(
                            sid, "setup", snapshot.revision, step["operation"], step["arguments"]
                        )
                    )
                adapter.actions.clear()
                session = AgentSession(llm=provider, max_tool_steps=8)
                session.output.transcription = Sink()
                runtime = LiveConversationRuntime(IntegratedFoodEaseAgent(), session, adapter)
                trace: dict = {"id": case["id"], "source": case["source"], "turns": []}
                try:
                    await runtime.prepare()
                    await runtime.select_mode("typed")
                    await session.start(agent=runtime.agent)
                    for index, text in enumerate(case["utterances"], 1):
                        before, start = requests, len(adapter.actions)
                        handle = await runtime.input_text(
                            text, f"{case['id']}-{index}", runtime.snapshot.revision
                        )
                        if handle is not None:
                            await asyncio.wait_for(handle.wait_for_playout(), timeout=45)
                        for speech in tuple(runtime.speeches.values()):
                            await asyncio.wait_for(speech.wait_for_playout(), timeout=45)
                        assistant = " ".join(
                            item.text_content or ""
                            for item in (handle.chat_items if handle else [])
                            if isinstance(item, llm.ChatMessage) and item.role == "assistant"
                        ).strip()
                        trace["turns"].append(
                            {
                                "user": text,
                                "assistant": assistant,
                                "real_model_turn": requests > before,
                                "provider_requests": requests - before,
                                "actions": adapter.actions[start:],
                            }
                        )
                    operations = {action["operation"] for action in adapter.actions}
                    trace["required_operations_observed"] = (
                        set(case["expected_operations"]) <= operations
                    )
                    trace["forbidden_operations_observed"] = sorted(
                        operations.intersection(case["forbidden_operations"])
                    )
                    trace["headless_summary_receipts"] = len(adapter.summaries)
                    trace["final_cart"] = runtime.snapshot.cart.model_dump(mode="json")
                except Exception as error:
                    trace["error_type"] = type(error).__name__
                finally:
                    await runtime.close()
                    await session.aclose()
                results.append(trace)
                (output / "results.json").write_text(
                    json.dumps(results, indent=2), encoding="utf-8"
                )
    finally:
        await provider.aclose()
    actual = sum(turn["real_model_turn"] for case in results for turn in case["turns"])
    manifest = {
        "status": "real_model_text_run",
        "model": model,
        "thinking_level": thinking,
        "provider_requests": requests,
        "provider_request_limit": request_limit,
        "real_model_turns": actual,
        "cases_completed": len(results),
        "required_operations_matched_cases": sum(
            case.get("required_operations_observed", False) for case in results
        ),
        "forbidden_operation_cases": sum(
            bool(case.get("forbidden_operations_observed")) for case in results
        ),
        "error_cases": sum("error_type" in case for case in results),
        "minimum_real_model_turns_met": actual >= 40,
        "human_listeners": 0,
        "human_quality_gate": "not_evaluated",
        "audio_gate": "not_evaluated",
        "rtc": "none",
        "delivery": "headless text, not browser or audible evidence",
        "manual_review_required": [
            "false factual/success claims",
            "unnecessary clarification",
            "duplicates",
            "naturalness",
            "relevance",
            "brevity",
            "comfort",
        ],
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--allow-provider-cost", action="store_true")
    parser.add_argument("--model", default=os.environ.get("LLM_MODEL"))
    parser.add_argument("--thinking-level", default=os.environ.get("LLM_THINKING_LEVEL"))
    parser.add_argument("--max-provider-requests", type=int, default=160)
    args = parser.parse_args()
    os.environ["PYTHON_DOTENV_DISABLED"] = "1"
    os.environ["RECORD_AUDIO"] = "false"
    if args.live and (not args.allow_provider_cost or not args.model or not args.thinking_level):
        parser.error("Live mode requires explicit cost approval, model and thinking level.")
    if args.live and not os.environ.get("GOOGLE_API_KEY"):
        parser.error("GOOGLE_API_KEY must already be in the environment; dotenv is never loaded.")
    if not 1 <= args.max_provider_requests <= 160:
        parser.error("Provider request limit must be between 1 and 160.")
    output = args.output.resolve()
    allowed = ROOT / "orchestration/evidence/final/phase-07"
    if not output.is_relative_to(allowed) or output == allowed:
        parser.error("Output must be a new run directory inside Phase 7 evidence.")
    if args.live and (output / "results.json").exists():
        parser.error("Use a fresh output directory to preserve prior campaign evidence.")
    cases = prepare(output)
    if args.live:
        asyncio.run(
            run(
                output,
                cases,
                model=args.model,
                thinking=args.thinking_level,
                request_limit=args.max_provider_requests,
            )
        )
    print(
        f"Phase 7 campaign: {'real model text run' if args.live else 'prepared, no provider calls'}"
    )


if __name__ == "__main__":
    main()
