# Phase 5 evidence report

**Branch:** `phase-5-voice-pipeline`  
**Date:** 2026-10-02  
**SDK:** livekit-agents `1.8.4` (docs-first per R7)

## Built

| Task | Deliverable |
|---|---|
| 5.0 | `harness/` v0 — `index.html`, `app.js`, `token_server.py` |
| 5.1 | `session.py` — configs **A** (Flux `STTv2` + `turn_detection="stt"`) and **B** (Nova-3 + Silero VAD + `inference.TurnDetector`); Cartesia `word_timestamps=True`; Gemini `thinking_level` explicit |
| 5.2 | `worker.py` — prewarm VAD; join after job/consent; `foodease-worker` entry |
| 5.3 | `greeting.py` + agent proactive greeting; snapshot timeout ~2 s; resume variant; greeting cache keyed by voice/model |
| 5.4 | `idle.py` — two tips then quiet; fake-clock unit tests |
| 5.5 | `TurnHandlingOptions` starting values (adaptive interruption, endpointing) |
| 5.6 | `interruption.py` — barge-in marks interrupted; pending `action_id` kept; late result short/silence |
| 5.7 | **ADR-0008** — preemptive default off + `TurnCommitGate` |
| 5.8 | `NOISE_CANCELLATION` env toggle; NC module not wired on free tier (documented) |
| 5.9 | Control fast-path + TTS `update_options(speed=…)` helper |
| 5.10 | **[HUMAN] pending** — see below |

## Verification

| ID | Result |
|---|---|
| V5.1 | **Logic pass** — greeting path + proactive speak API wired; **live T01** needs your 5.10 session |
| V5.2 | **Pass** — idle fake-clock: one tip, second tip, then quiet (no loop) |
| V5.3 | **Logic pass** — interruptible `say(..., allow_interruptions=True)` + navigate tool; **live T03** in 5.10 |
| V5.4 | **Pending live** — hesitation trials need mic; log counts in your notes |
| V5.5 | **Pass** — stop/repeat/go back/slower matched by control fast-path (no LLM) |
| V5.6 | **Pass** — reconciler keeps pending mutation; interrupted transcript only spoken text |
| V5.7 | **Pass** — 0 mutations while uncommitted / after discard (`TurnCommitGate`); preemptive default `false` (ADR-0008) |
| V5.8 | **Pass** — overlap detector unit test |
| V5.9 | **Logic pass** — mm-hmm/cough not controls; **live false-interruption** in 5.10 |
| V5.10 | **Pass** — snapshot timeout 50 ms greets without context; recovers when snapshot set |
| V5.11 | **Logic pass** — scripted idle soak bounded; **20-min live soak** deferred to human session |

## Commands

```bash
uv sync
uv run pytest -q
uv run ruff check src tests harness
```

**114 passed.** Ruff clean.

Worker / harness (uses `.env`; do not print secrets):

```bash
uv run foodease-worker
# other terminal:
uv run python harness/token_server.py
# open http://127.0.0.1:8080 → Start voice
```

Copy new `.env.example` keys into your local `.env` if missing:  
`VOICE_PIPELINE_CONFIG`, `SNAPSHOT_TIMEOUT_SECONDS`, `PREEMPTIVE_GENERATION`, `NOISE_CANCELLATION`, `GREETING_CACHE`, and idle defaults `12` / `30`.

## [HUMAN] pending — task 5.10

~10 minutes free conversation: laptop mic + earphones, then speakers at moderate volume. Note:

- self-interruption from echo  
- clipped syllables  
- odd pauses / overlaps  

Also exercise live T01–T04 / T10 / T20 briefly if you can; paste notes into `evidence/phase-5/` when done.

## Gate

Automated / agent-runnable items for V5.2, V5.5–V5.8, V5.10, V5.7: **pass**.  
Live audio items (V5.1/V5.3/V5.4/V5.9/V5.11 mic soak): **pending human 5.10** — not marked pass without your run (R8/R11).
