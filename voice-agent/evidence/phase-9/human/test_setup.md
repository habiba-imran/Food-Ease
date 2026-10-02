# Phase 9.1 — Test setup record [HUMAN]

Fill this before the Mode 1 baseline campaign (task 9.2). The agent does not invent these values.

| Field | Your value |
|---|---|
| Date | |
| Browser + version | |
| OS / device model | |
| Microphone | built-in / earphones / other |
| Network | home broadband / venue Wi‑Fi / other |
| LiveKit region (or auto-routed) | |
| Account tiers (LiveKit, Deepgram, Cartesia, Google) | |
| Quota headroom notes | |
| `VOICE_PIPELINE_CONFIG` (A or B) | |
| Noise test planned? (9.6) | yes / no |

Save a screenshot or short note of LiveKit dashboard room settings if useful. Do **not** paste API keys here.

After filling, run:

```bash
uv run python tools/run_latency_campaign.py --manifest-only
# Start worker + harness room, then:
uv run python tools/run_latency_campaign.py --live --room YOUR_ROOM --out evidence/phase-9/campaign/baseline/metrics.jsonl
uv run python tools/generate_latency_report.py
```
