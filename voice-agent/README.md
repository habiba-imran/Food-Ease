# FoodEase Voice Agent

LiveKit voice agent for the accessible FoodEase ordering demo. The final website
uses the integrated v2 runtime and the website's authoritative cart. Start with
the [final delivery runbook](../orchestration/docs/FINAL_RUNBOOK.md). Standalone
MockApp/handover notes below are retained for development and historical evidence.

The integrated session explicitly disables SDK recording and remote session hosting;
all thirteen website operations remain behind the bound action/confirmation gates.

The integrated website assistant now defaults to **Urdu** (`ASSISTANT_LANGUAGE=ur`).
It uses Groq Whisper with `language=ur` for recognition, Silero VAD for turn endings,
and Cartesia Sonic 3.6 with `language=ur` for speech. Greetings, captions, prices,
cart summaries, confirmations and recovery messages use Urdu script. Existing
English Flux/Nova settings are ignored in Urdu mode; select `ASSISTANT_LANGUAGE=en`
to use the retained English pipeline. The legacy standalone MockApp/CLI sections
below describe the original English development harness.

Menu meaning is interpreted by the LLM against actual catalog/category data.
There is no shopping-synonym whitelist. Urdu catalog display names live in
`src/foodease_agent/locales/ur.json`; these translate verified product labels and
do not choose search/filter operations. Spoken/typed endings, mode choices, pause,
repeat and page-reading requests also use model interpretation through one local
`conversation_control` tool. Users can express these in their own words. The code
validates the selected effect, session, turn and permissions; direct UI controls
and explicit checkout consent remain deterministic. See the
[semantic-controls follow-up](evidence/semantic-controls-2026-11-07/report.md).

**Owner (agent):** Habiba · **Website:** Zainab
**Handover docs:** [`docs/handover/`](docs/handover/) — start with [`INTEGRATION_NOTE.md`](docs/handover/INTEGRATION_NOTE.md) and [`FRONTEND_QUICKSTART.md`](docs/handover/FRONTEND_QUICKSTART.md).

## Quick start (clean checkout)

```bash
# Python 3.12+
cd voice-agent
uv sync
cp .env.example .env
# Fill LIVEKIT_* / CARTESIA_API_KEY / GROQ_API_KEY in .env.
# DEEPGRAM_API_KEY is used only for the retained English recognition pipeline.

# Smoke (no paid provider calls):
uv run python tools/smoke.py

# Full automated suite:
uv run pytest -q
```

Groq defaults to `openai/gpt-oss-20b`. Set `GROQ_MODEL` to select another Groq
model. To run Gemini, set `LLM_PROVIDER=gemini` and configure `GOOGLE_API_KEY`,
`LLM_MODEL` and `LLM_THINKING_LEVEL`. Urdu recognition still needs `GROQ_API_KEY`.
`TTS_VOICE_ID` takes a Cartesia voice UUID.
The worker uses the FoodEase default voice if that setting is blank or malformed.

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
