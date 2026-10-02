"""One tiny call per provider. Prints pass/fail only — never prints secrets."""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "spikes"))

from _env import load_env, present, require  # noqa: E402
from credit_ledger import save_charge  # noqa: E402


async def check_livekit() -> tuple[str, str]:
    from livekit import api

    url = require("LIVEKIT_URL")
    key = require("LIVEKIT_API_KEY")
    secret = require("LIVEKIT_API_SECRET")
    lk = api.LiveKitAPI(url, key, secret)
    try:
        # Tiny authenticated RPC: list rooms (empty list is fine).
        await lk.room.list_rooms(api.ListRoomsRequest())
        return "LiveKit", "PASS"
    except Exception as exc:  # noqa: BLE001 — report class only
        return "LiveKit", f"FAIL ({type(exc).__name__})"
    finally:
        await lk.aclose()


def check_deepgram() -> tuple[str, str]:
    key = require("DEEPGRAM_API_KEY")
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                "https://api.deepgram.com/v1/projects",
                headers={"Authorization": f"Token {key}"},
            )
        if resp.status_code == 200:
            return "Deepgram", "PASS"
        return "Deepgram", f"FAIL (HTTP {resp.status_code})"
    except Exception as exc:  # noqa: BLE001
        return "Deepgram", f"FAIL ({type(exc).__name__})"


def check_cartesia() -> tuple[str, str]:
    key = require("CARTESIA_API_KEY")
    text = "ok"
    save_charge("healthcheck", text, voice_id="health")
    # Use a known default English voice from LiveKit/Cartesia docs.
    voice = "9626c31c-bec5-4cca-baa8-f8ba9e84c8bc"
    try:
        with httpx.Client(timeout=60.0) as client:
            t0 = time.perf_counter()
            resp = client.post(
                "https://api.cartesia.ai/tts/bytes",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Cartesia-Version": "2026-08-14",
                    "Content-Type": "application/json",
                },
                json={
                    "model_id": "sonic-3.6",
                    "transcript": text,
                    "voice": {"id": voice},
                    "language": "en",
                    "output_format": {
                        "container": "wav",
                        "encoding": "pcm_s16le",
                        "sample_rate": 24000,
                    },
                },
            )
            _ = time.perf_counter() - t0
        if resp.status_code == 200 and len(resp.content) > 100:
            return "Cartesia", "PASS (sonic-3.6 accepted)"
        return "Cartesia", f"FAIL (HTTP {resp.status_code}, body_len={len(resp.content)})"
    except Exception as exc:  # noqa: BLE001
        return "Cartesia", f"FAIL ({type(exc).__name__})"


def check_gemini() -> tuple[str, str]:
    from google import genai
    from google.genai import types

    key = require("GOOGLE_API_KEY")
    try:
        client = genai.Client(api_key=key)
        resp = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents="Reply with exactly: ok",
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_level="minimal"),
                max_output_tokens=8,
            ),
        )
        text = (resp.text or "").strip().lower()
        if "ok" in text or text:
            return "Gemini", "PASS (gemini-3.1-flash-lite + thinking_level=minimal)"
        return "Gemini", "FAIL (empty response)"
    except Exception as exc:  # noqa: BLE001
        return "Gemini", f"FAIL ({type(exc).__name__}: {exc})"


async def main() -> int:
    load_env()
    print("Provider health checks (secrets not printed)")
    for name in (
        "LIVEKIT_URL",
        "LIVEKIT_API_KEY",
        "LIVEKIT_API_SECRET",
        "DEEPGRAM_API_KEY",
        "CARTESIA_API_KEY",
        "GOOGLE_API_KEY",
    ):
        print(f"  env {name}: {'set' if present(name) else 'MISSING'}")

    results: list[tuple[str, str]] = []
    results.append(await check_livekit())
    results.append(check_deepgram())
    results.append(check_cartesia())
    results.append(check_gemini())

    print("---")
    failed = 0
    for provider, status in results:
        print(f"{provider}: {status}")
        if not status.startswith("PASS"):
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
