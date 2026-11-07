"""Bounded live provider probe with synthetic Urdu and the real local cart authority.

This is not a Cloud room, physical-microphone or caller-heard latency test. No audio
is saved, and the script never submits an order. Run only with provider-cost approval.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "voice-agent/tests"))

from cloud import local_environment, redact  # noqa: E402
from foodease_agent.config import load_config  # noqa: E402
from foodease_agent.integrated.agent import IntegratedFoodEaseAgent  # noqa: E402
from foodease_agent.integrated.runtime import LiveConversationRuntime  # noqa: E402
from foodease_agent.production_metrics import metric_record  # noqa: E402
from foodease_agent.session import build_llm, build_stt, build_tts  # noqa: E402
from livekit.agents import AgentSession  # noqa: E402
from livekit.agents.types import APIConnectOptions  # noqa: E402
from livekit.agents.utils import http_context  # noqa: E402
from livekit.agents.voice.agent_session import SessionConnectOptions  # noqa: E402
from livekit.agents.voice.io import TextOutput  # noqa: E402
from test_integrated_runtime import WebsiteAdapter  # noqa: E402


class TextSink(TextOutput):
    def __init__(self):
        super().__init__(label="live-provider-probe", next_in_chain=None)

    async def capture_text(self, text):
        pass

    def flush(self):
        pass


async def synthesize(tts, text):
    started = time.perf_counter()
    first, frames = None, []
    async with tts.synthesize(
        text, conn_options=APIConnectOptions(max_retry=0, timeout=25)
    ) as stream:
        async for audio in stream:
            if first is None:
                first = time.perf_counter()
            frames.append(audio.frame)
    if not frames or first is None:
        raise RuntimeError("No synthesized audio")
    return frames, round((first - started) * 1000, 2)


async def probe():
    settings = load_config(environ=local_environment())
    tts, stt, model = build_tts(settings), build_stt(settings, "B"), build_llm(settings)
    adapter = WebsiteAdapter()  # actual website SessionStore; fake RTC is not involved
    session = AgentSession(
        llm=model,
        max_tool_steps=6,
        conn_options=SessionConnectOptions(llm_conn_options=APIConnectOptions(max_retry=1)),
    )
    session.output.transcription = TextSink()
    runtime = LiveConversationRuntime(IntegratedFoodEaseAgent(language="ur"), session, adapter)
    metrics, samples = [], []
    session.on("conversation_item_added", lambda event: metrics.append(metric_record(event)))
    try:
        await runtime.prepare()
        await runtime.select_mode("typed")
        await session.start(agent=runtime.agent)
        for text in (
            "ایک کولا کا کین کارٹ میں ایڈ کر دو۔",
            "میرے کارٹ کا ٹوٹل کتنا ہوا؟",
        ):
            input_frames, _ = await synthesize(tts, text)
            started = time.perf_counter()
            recognition = await stt.recognize(
                input_frames,
                language="ur",
                conn_options=APIConnectOptions(max_retry=0, timeout=25),
            )
            recognized = recognition.alternatives[0].text
            recognized_at = time.perf_counter()
            event_index, request_index = len(adapter.events), len(adapter.requests)
            handle = await runtime.input_text(
                recognized, uuid4().hex, runtime.snapshot.revision, source="text"
            )
            if handle is None:
                raise RuntimeError("Input was not admitted")
            await asyncio.wait_for(handle.wait_for_playout(), timeout=45)
            for _ in range(100):
                completed = [
                    payload["text"]
                    for event, payload, _ in adapter.events[event_index:]
                    if event == "transcript.assistant" and payload.get("phase") == "completed"
                ]
                if completed:
                    break
                await asyncio.sleep(0.05)
            if not completed:
                raise RuntimeError("No completed model/control reply")
            model_done = time.perf_counter()
            output_frames, ttfb = await synthesize(tts, completed[-1])
            samples.append(
                {
                    "recognized_synthetic_urdu": recognized,
                    "reply": completed[-1],
                    "stt_request_ms": round((recognized_at - started) * 1000, 2),
                    "model_and_tools_complete_ms": round((model_done - recognized_at) * 1000, 2),
                    "response_tts_first_frame_ms": ttfb,
                    "serialized_probe_to_first_output_audio_ms": round(
                        (model_done - started) * 1000 + ttfb, 2
                    ),
                    "output_audio_seconds": round(
                        sum(frame.duration for frame in output_frames), 3
                    ),
                    "operations": [
                        request.payload.operation for request in adapter.requests[request_index:]
                    ],
                }
            )
            print(json.dumps(samples[-1], ensure_ascii=False), flush=True)
        cart = runtime.snapshot.cart
        passed = (
            len(cart.lines) == 1
            and cart.lines[0].item_id == "drink-cola"
            and cart.lines[0].quantity == 1
            and "cart.add_item" in samples[0]["operations"]
            and "get_cart" in samples[1]["operations"]
        )
        result = {
            "kind": "live_providers_local_real_authority_synthetic_audio",
            "passed": passed,
            "samples": samples,
            "sdk_metrics": metrics,
            "actual_cart_total": cart.total,
            "cloud_room_tested": False,
            "caller_heard_latency_measured": False,
        }
        output = ROOT / "deployment/evidence/provider-probe.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0 if passed else 1
    finally:
        await runtime.close()
        await session.aclose()
        await tts.aclose()
        await stt.aclose()
        await model.aclose()


async def main_probe():
    async with http_context.open():
        return await asyncio.wait_for(probe(), timeout=180)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.WARNING)
    try:
        raise SystemExit(asyncio.run(main_probe()))
    except Exception as error:
        detail = {
            "passed": False,
            "error_type": type(error).__name__,
            "detail": redact(str(error), local_environment()),
            "cause_type": type(error.__cause__).__name__,
            "cause": redact(str(error.__cause__), local_environment()),
        }
        output = ROOT / "deployment/evidence/provider-probe-failure.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(detail, ensure_ascii=False))
        raise SystemExit(1) from None
