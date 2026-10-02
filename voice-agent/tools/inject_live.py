"""Mode 1 live latency campaign client (Phase 9).

Joins a LiveKit room, publishes scripted turns (WAV when provided, else lk chat text),
records remote agent audio onset, and appends TurnMetrics JSONL.

Requires: worker running in the same room, completed 9.1 setup, filled `.env`.
Does not print secrets (R6).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import uuid
from pathlib import Path

from livekit import api, rtc

from foodease_agent.config import ConfigError, load_config
from foodease_agent.metrics import MetricsLogger, TurnMetrics

ROOT = Path(__file__).resolve().parents[1]


def _access_token(settings, *, room: str, identity: str) -> str:
    grant = api.VideoGrants(room_join=True, room=room)
    token = (
        api.AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        .with_identity(identity)
        .with_name("latency-inject")
        .with_grants(grant)
    )
    return token.to_jwt()


async def _wait_for_agent_audio(room: rtc.Room, timeout_s: float = 45.0) -> float | None:
    """Return ms from now until first non-silent remote audio frame (approximate)."""
    start = time.perf_counter()
    event = asyncio.Event()
    holder: dict[str, float | None] = {"ms": None}

    def on_track_subscribed(track: rtc.Track, *_args) -> None:
        if track.kind != rtc.TrackKind.KIND_AUDIO:
            return

        async def reader() -> None:
            audio = rtc.AudioStream(track)
            async for frame in audio:
                data = frame.frame.data
                if not data:
                    continue
                # Simple energy gate — not a calibrated dB measurement.
                if max(abs(b) for b in data[: min(256, len(data))]) > 200:
                    holder["ms"] = (time.perf_counter() - start) * 1000.0
                    event.set()
                    return

        asyncio.create_task(reader())

    room.on("track_subscribed", on_track_subscribed)
    try:
        await asyncio.wait_for(event.wait(), timeout=timeout_s)
    except TimeoutError:
        return None
    return holder["ms"]


async def _send_turn(room: rtc.Room, utterance: str) -> None:
    if utterance.startswith("("):
        return
    payload = json.dumps({"message": utterance}).encode("utf-8")
    await room.local_participant.publish_data(payload, reliable=True)


async def run_campaign(
    *,
    room_name: str,
    manifest_path: Path,
    out_path: Path,
    session_id: str,
    max_turns: int | None,
) -> int:
    try:
        settings = load_config()
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    turns = manifest["mode_1"]["turns"]
    if max_turns is not None:
        turns = turns[:max_turns]

    logger = MetricsLogger(
        out_path,
        config={
            "tool": "inject_live.py",
            "room": room_name,
            "pipeline": settings.voice_pipeline_config,
            "stt": settings.stt_model,
            "tts": settings.tts_model,
            "llm": settings.llm_model,
            "preemptive": settings.preemptive_generation,
            "interruption_min_duration": settings.interruption_min_duration,
        },
    )

    room = rtc.Room()
    token = _access_token(settings, room=room_name, identity=f"inject-{uuid.uuid4().hex[:6]}")
    await room.connect(settings.livekit_url, token)
    written = 0
    try:
        for spec in turns:
            turn_id = spec.get("id", uuid.uuid4().hex[:8])
            kind = spec.get("turn_kind", "response")
            utterance = spec.get("utterance", "")
            t0 = time.perf_counter()
            await _send_turn(room, utterance)
            measured = await _wait_for_agent_audio(room)
            record: dict = {
                "mode": "mode_1",
                "turn_kind": kind,
                "completed_without_restart": measured is not None,
                "success": measured is not None,
            }
            if kind == "barge_in":
                record["barge_in_stop_ms"] = measured
            elif kind == "greeting_warm":
                record["greeting_warm_ttfa_ms"] = measured
            elif kind == "greeting_cold":
                record["greeting_cold_ttfa_ms"] = measured
            else:
                record["response_ttfa_ms"] = measured
                record["audible_ttfa_ms"] = measured

            metrics = TurnMetrics(
                turn_id=turn_id,
                session_id=session_id,
                config_hash=logger.hash,
                audible_ttfa_ms=measured,
                extra={
                    **record,
                    "utterance": utterance,
                    "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2),
                    "note": "live approximate audio onset; WAV path preferred for STT EOT",
                },
            )
            logger.write(metrics)
            written += 1
            await asyncio.sleep(1.0)
    finally:
        await room.disconnect()

    print(json.dumps({"wrote": written, "out": str(out_path), "config_hash": logger.hash}))
    return 0 if written else 1


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--room", required=True, help="LiveKit room name (worker must be present)")
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--session-id", default="latency-live")
    p.add_argument("--max-turns", type=int, default=None)
    args = p.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    code = asyncio.run(
        run_campaign(
            room_name=args.room,
            manifest_path=args.manifest,
            out_path=args.out,
            session_id=args.session_id,
            max_turns=args.max_turns,
        )
    )
    raise SystemExit(code)


if __name__ == "__main__":
    main()
