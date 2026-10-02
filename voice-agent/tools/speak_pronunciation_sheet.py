"""Synthesize the V6.2 pronunciation sheet with Cartesia (optional; burns credits).

Usage:
  uv run python tools/speak_pronunciation_sheet.py          # all 50 lines
  uv run python tools/speak_pronunciation_sheet.py --limit 5

Does not print secrets. Writes WAVs under evidence/phase-6/human/audio/.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
SHEET = ROOT / "evidence" / "phase-6" / "human" / "pronunciation_sheet.md"
OUT = ROOT / "evidence" / "phase-6" / "human" / "audio"
CARTESIA_VERSION = "2026-08-14"


def _lines_from_sheet() -> list[str]:
    text = SHEET.read_text(encoding="utf-8")
    lines: list[str] = []
    for row in text.splitlines():
        if not row.startswith("|"):
            continue
        cells = [c.strip() for c in row.strip("|").split("|")]
        if len(cells) < 3:
            continue
        if cells[0] in {"#", "---"} or not cells[0].isdigit():
            continue
        lines.append(cells[2])
    if len(lines) != 50:
        raise SystemExit(f"expected 50 sheet lines, found {len(lines)}")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Synthesize only first N lines")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    import os

    api_key = os.environ.get("CARTESIA_API_KEY", "").strip()
    voice = os.environ.get("TTS_VOICE_ID", "").strip()
    model = os.environ.get("TTS_MODEL", "sonic-3.6").strip() or "sonic-3.6"
    # Jacqueline (ADR-0006) if .env still has a placeholder
    default_voice = "9626c31c-bec5-4cca-baa8-f8ba9e84c8bc"
    if len(voice) != 36 or voice.count("-") != 4:
        print("TTS_VOICE_ID missing/invalid in .env — using primary Jacqueline id")
        voice = default_voice
    if not api_key:
        raise SystemExit("CARTESIA_API_KEY required in .env")

    lines = _lines_from_sheet()
    if args.limit > 0:
        lines = lines[: args.limit]

    OUT.mkdir(parents=True, exist_ok=True)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Cartesia-Version": CARTESIA_VERSION,
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=90.0, headers=headers) as client:
        for i, spoken in enumerate(lines, start=1):
            payload = {
                "model_id": model,
                "transcript": spoken,
                "voice": {"id": voice},
                "language": "en",
                "output_format": {
                    "container": "wav",
                    "encoding": "pcm_s16le",
                    "sample_rate": 24000,
                },
            }
            r = client.post("https://api.cartesia.ai/tts/bytes", json=payload)
            if r.status_code != 200:
                raise SystemExit(f"Cartesia HTTP {r.status_code}: {r.text[:300]}")
            path = OUT / f"{i:02d}.wav"
            path.write_bytes(r.content)
            print(f"wrote {path.name} ({len(spoken)} chars)")

    print(f"done: {len(lines)} files in {OUT}")


if __name__ == "__main__":
    main()
