# FoodEase Voice Agent

LiveKit voice agent for the accessible FoodEase ordering demo. The final website
uses the integrated v2 runtime and the website's authoritative cart. Start with
the [final delivery runbook](../orchestration/docs/FINAL_RUNBOOK.md). Standalone
MockApp/handover notes below are retained for development and historical evidence.

The integrated session explicitly disables SDK recording and remote session hosting;
all thirteen website operations remain behind the bound action/confirmation gates.

**Owner (agent):** Habiba · **Website:** Zainab
**Handover docs:** [`docs/handover/`](docs/handover/) — start with [`INTEGRATION_NOTE.md`](docs/handover/INTEGRATION_NOTE.md) and [`FRONTEND_QUICKSTART.md`](docs/handover/FRONTEND_QUICKSTART.md).

## Quick start (clean checkout)

```bash
# Python 3.12+
cd voice-agent
uv sync
cp .env.example .env
# Fill LIVEKIT_* / DEEPGRAM_* / CARTESIA_* / GOOGLE_* in .env (never commit .env)

# Smoke (no paid provider calls):
uv run python tools/smoke.py

# Full automated suite:
uv run pytest -q
```

### Live demo (needs filled `.env` + LiveKit Cloud)

```bash
# Terminal A — agent worker
uv run foodease-worker

# Terminal B (optional) — MockApp + DEV control :8765
# DEV_MODE=true in .env
uv run python -m mock_app

# Terminal C — harness token server + static UI
uv run python harness/token_server.py
# Open the URL printed (usually http://127.0.0.1:8080)
```

Text-only conversation (no audio providers required for the engine path):

```bash
uv run foodease-cli
```

## Layout

| Path | Purpose |
|---|---|
| `src/foodease_agent/` | Agent brain, adapters, contract models |
| `contract/v1/` | Frozen schemas + transport defaults |
| `mock_app/` | Website stand-in over RPC |
| `harness/` | Inspector UI for demos |
| `docs/` | SPEC, PLAN, STATUS, handover |
| `evidence/` | Phase reports (no secrets, no raw audio by default) |
| `prompts/` | Agent policy prompts |

## Rules of note for integrators

- Voice logic imports only `AppAdapter`. Wire format lives in `LiveKitRpcAdapter`.
- Never report cart/checkout success without a matching `action_id` result.
- `RECORD_AUDIO=false` by default; do not commit recordings or `.env`.
