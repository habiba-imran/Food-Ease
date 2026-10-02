"""Cartesia TTS spike (Phase 1). Credit-capped. Audition clips generated once."""

from __future__ import annotations

import csv
import json
import statistics
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "spikes"))

from _env import load_env, require  # noqa: E402
from credit_ledger import load_state, plan_cost, save_charge  # noqa: E402

MODEL = "sonic-3.6"
CARTESIA_VERSION = "2026-08-14"
AUDIO_DIR = ROOT / "evidence" / "phase-1" / "audio"
MANIFEST = AUDIO_DIR / "manifest.json"
TTS_CSV = ROOT / "evidence" / "phase-1" / "tts.csv"
META_JSON = ROOT / "evidence" / "phase-1" / "tts_meta.json"

# Four English voices: warm / clear / calm / mid-pace (IDs from LiveKit Cartesia docs + default).
VOICES: list[dict[str, str]] = [
    {
        "label": "jacqueline",
        "id": "9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        "note": "confident young American adult female",
    },
    {
        "label": "blake",
        "id": "a167e0f3-df7e-4d52-a9c3-f949145efdab",
        "note": "energetic American adult male",
    },
    {
        "label": "robyn",
        "id": "f31cc6a7-c1e8-4764-980c-60a361443dd1",
        "note": "neutral mature Australian female",
    },
    {
        "label": "katie",
        "id": "f786b574-daa5-4673-aa0c-cbe3e8534c02",
        "note": "Cartesia plugin default English female",
    },
]

AUDITION_LINES: list[tuple[str, str]] = [
    ("greeting", "Welcome. I can help you explore the menu and place a demo order."),
    ("listing", "I found three spicy options under one thousand rupees."),
    ("apology", "Sorry, that item is out of stock right now."),
    (
        "checkout",
        "Your demo total is one thousand seven hundred rupees. Shall I place it?",
    ),
    ("correction", "Okay, making that one instead of two."),
    (
        "long_desc",
        "Chicken biryani with basmati rice, raita, and a mild spice level.",
    ),
    ("error", "I could not update the cart. Want to try again?"),
    ("goodbye", "Thanks for trying the demo. Goodbye."),
]

NUMBER_SHEET: list[tuple[str, str]] = [
    ("rs_850", "Rs. 850"),
    ("pkr_1500", "PKR 1,500"),
    ("plain_150", "150"),
    ("range_800_1000", "800 to 1,000"),
    ("two_items_1700", "two items, total 1,700"),
]

TIMING_PHRASE = "Timing."


def _client(api_key: str) -> httpx.Client:
    return httpx.Client(
        timeout=90.0,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Cartesia-Version": CARTESIA_VERSION,
            "Content-Type": "application/json",
        },
    )


def synthesize(
    client: httpx.Client,
    *,
    voice_id: str,
    text: str,
    purpose: str,
    generation_config: dict | None = None,
    out_path: Path | None = None,
) -> dict:
    save_charge(purpose, text, voice_id=voice_id)
    body: dict = {
        "model_id": MODEL,
        "transcript": text,
        "voice": {"id": voice_id},
        "language": "en",
        "output_format": {
            "container": "wav",
            "encoding": "pcm_s16le",
            "sample_rate": 24000,
        },
    }
    if generation_config:
        body["generation_config"] = generation_config
    t0 = time.perf_counter()
    resp = client.post("https://api.cartesia.ai/tts/bytes", json=body)
    ttfb_ms = (time.perf_counter() - t0) * 1000.0
    # For bytes endpoint the first byte arrives with the completed body; still useful latency.
    if resp.status_code != 200:
        raise RuntimeError(f"Cartesia HTTP {resp.status_code}: {resp.text[:200]}")
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(resp.content)
    return {
        "status": resp.status_code,
        "ttfb_ms": round(ttfb_ms, 2),
        "bytes": len(resp.content),
        "chars": len(text),
    }


def load_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {"audition": {}, "number_sheet": {}, "speed_volume": {}, "emotion": {}}


def save_manifest(manifest: dict) -> None:
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def ensure_audition(client: httpx.Client) -> None:
    manifest = load_manifest()
    audition = manifest.setdefault("audition", {})
    pending_texts: list[str] = []
    jobs: list[tuple[str, str, str, Path]] = []
    for voice in VOICES:
        for line_id, text in AUDITION_LINES:
            key = f"{voice['label']}__{line_id}"
            path = AUDIO_DIR / "audition" / voice["label"] / f"{line_id}.wav"
            if key in audition and path.exists():
                continue
            pending_texts.append(text)
            jobs.append((key, voice["id"], text, path))
    if jobs:
        print(f"Audition: generating {len(jobs)} new clips (chars={plan_cost(pending_texts)})")
        print(f"Credits before: {load_state().used}/{load_state().cap}")
        for key, voice_id, text, path in jobs:
            meta = synthesize(
                client,
                voice_id=voice_id,
                text=text,
                purpose=f"audition:{key}",
                out_path=path,
            )
            audition[key] = {"path": str(path.relative_to(ROOT)), **meta, "text": text}
            save_manifest(manifest)
    else:
        print("Audition: all clips already on disk — not regenerating")


def ensure_number_sheet(client: httpx.Client) -> None:
    manifest = load_manifest()
    sheet = manifest.setdefault("number_sheet", {})
    for voice in VOICES:
        for nid, text in NUMBER_SHEET:
            key = f"{voice['label']}__{nid}"
            path = AUDIO_DIR / "numbers" / voice["label"] / f"{nid}.wav"
            if key in sheet and path.exists():
                continue
            meta = synthesize(
                client,
                voice_id=voice["id"],
                text=text,
                purpose=f"numbers:{key}",
                out_path=path,
            )
            sheet[key] = {"path": str(path.relative_to(ROOT)), **meta, "text": text}
            save_manifest(manifest)
    print("Number sheet: complete (once per voice)")


def speed_volume_emotion(client: httpx.Client, rows: list[dict]) -> None:
    """One short probe per voice for speed/volume/emotion — do not regenerate if logged."""
    manifest = load_manifest()
    probes = manifest.setdefault("speed_volume", {})
    text = "Speed and volume check."
    configs = [
        ("speed_slow", {"speed": 0.7, "volume": 1.0}),
        ("speed_fast", {"speed": 1.3, "volume": 1.0}),
        ("volume_high", {"speed": 1.0, "volume": 1.5}),
    ]
    for voice in VOICES:
        for name, gen in configs:
            key = f"{voice['label']}__{name}"
            if key in probes:
                rows.append({**probes[key], "voice": voice["label"], "kind": name})
                continue
            try:
                meta = synthesize(
                    client,
                    voice_id=voice["id"],
                    text=text,
                    purpose=f"speedvol:{key}",
                    generation_config=gen,
                )
                probes[key] = {**meta, "ok": True, "config": gen}
            except Exception as exc:  # noqa: BLE001
                probes[key] = {"ok": False, "error": f"{type(exc).__name__}: {exc}", "config": gen}
            save_manifest(manifest)
            rows.append({**probes[key], "voice": voice["label"], "kind": name})

    emotion = manifest.setdefault("emotion", {})
    emo_text = "That went well."
    for voice in VOICES:
        key = f"{voice['label']}__calm"
        if key in emotion:
            continue
        try:
            meta = synthesize(
                client,
                voice_id=voice["id"],
                text=emo_text,
                purpose=f"emotion:{key}",
                generation_config={"emotion": "calm"},
            )
            emotion[key] = {**meta, "ok": True}
        except Exception as exc:  # noqa: BLE001
            emotion[key] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        save_manifest(manifest)

    # [laughter]-style tags: one probe on first voice only (credit-aware).
    laugh_key = "tag_laughter_probe"
    if laugh_key not in emotion:
        try:
            meta = synthesize(
                client,
                voice_id=VOICES[0]["id"],
                text="[laughter] That was funny.",
                purpose="emotion:laughter_tag",
            )
            emotion[laugh_key] = {**meta, "ok": True, "note": "literal [laughter] tag in transcript"}
        except Exception as exc:  # noqa: BLE001
            emotion[laugh_key] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        save_manifest(manifest)


def timing_runs(client: httpx.Client, rows: list[dict], *, n_per_voice: int = 10) -> None:
    """10x on all shortlisted voices now. Extra runs to reach 30x on top-2 after human pick."""
    for voice in VOICES:
        samples: list[float] = []
        for i in range(n_per_voice):
            meta = synthesize(
                client,
                voice_id=voice["id"],
                text=TIMING_PHRASE,
                purpose=f"timing:{voice['label']}:{i}",
            )
            samples.append(float(meta["ttfb_ms"]))
            rows.append(
                {
                    "kind": "timing",
                    "voice": voice["label"],
                    "voice_id": voice["id"],
                    "run": i,
                    "ttfb_ms": meta["ttfb_ms"],
                    "chars": meta["chars"],
                }
            )
        samples_sorted = sorted(samples)
        p95 = samples_sorted[max(0, int(0.95 * (len(samples_sorted) - 1)))]
        print(
            f"Timing {voice['label']}: n={len(samples)} median={statistics.median(samples):.1f}ms "
            f"p95={p95:.1f}ms max={max(samples):.1f}ms"
        )


def write_csv(rows: list[dict]) -> None:
    TTS_CSV.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    keys: list[str] = []
    for row in rows:
        for k in row:
            if k not in keys:
                keys.append(k)
    with TTS_CSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    load_env()
    api_key = require("CARTESIA_API_KEY")
    state = load_state()
    print(f"Cartesia credits at start: {state.used}/{state.cap} (remaining {state.remaining})")

    rows: list[dict] = []
    with _client(api_key) as client:
        # Confirm model id accepted (already health-checked; reaffirm in meta).
        ensure_audition(client)
        ensure_number_sheet(client)
        speed_volume_emotion(client, rows)
        timing_runs(client, rows, n_per_voice=10)

    write_csv(rows)
    meta = {
        "model": MODEL,
        "voices": VOICES,
        "audition_dir": str((AUDIO_DIR / "audition").relative_to(ROOT)),
        "number_sheet": [t for _, t in NUMBER_SHEET],
        "timing_phrase": TIMING_PHRASE,
        "timing_note": (
            "Ran 10x per voice. After human picks primary+backup, run +20 on those two "
            "to reach 30x (ask before exceeding credit cap)."
        ),
        "credits": load_state().__dict__,
        "plugin_note": (
            "Direct Cartesia /tts/bytes with model_id=sonic-3.6. "
            "LiveKit plugin docs list cartesia/sonic-3.6 via Inference; plugin default model "
            "string remains sonic-3 family — sonic-3.6 accepted by Cartesia API in this spike."
        ),
    }
    META_JSON.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Wrote {TTS_CSV}")
    print(f"Credits at end: {load_state().used}/{load_state().cap}")
    print("STOP for human voice audition (1.2): listen to evidence/phase-1/audio/audition/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
