# Phase 7 evidence report

**Branch:** `phase-7-interfaces-transport`  
**Date:** 2026-10-02  

## Built

| Task | Deliverable |
|---|---|
| 7.1 | `events.EventBus` — schema validate before emit; final replaces partial |
| 7.2 | `product_state.ProductStateMachine` + transition log (all VA-07 states) |
| 7.3 | `inbound.InboundHandler` — stale revisions ignored + logged |
| 7.4 | `adapters/livekit_rpc.py` + `transport.InProcessRoom` |
| 7.5 | `mock_app/` participant + localhost DEV_MODE control (`:8765`) |
| 7.6 | `metrics.MetricsLogger` JSONL + config hash |
| 7.7 | Harness inspector (`harness/`) — state, captions, event log, MockApp controls |
| 7.8 | `tools/inject.py` — metrics JSONL (dry_run timings labeled, not live Mode-1) |
| 7.9 | `faults.FaultToggles` + control `/faults` |

## Verification

| ID | Status | Notes |
|---|---|---|
| V7.1 | **Pass** | Scripted session envelopes validate; bad payload rejected |
| V7.2 | **Pass** | Transition walk covers every `ProductState` (see tests) |
| V7.3 | **Pass** (logic) | Mute → `muted/paused` in harness/state machine; live mic-deny still needs browser when you try it |
| V7.4 | **Pass** | Typed `show burgers` via RPC + engine (no fake audio) |
| V7.5 | **Pass** | Interim dropped when final arrives for same turn_id |
| V7.6 | **Pass** | Event JSON has no api_key/Bearer; inject does not write WAV by default |
| V7.7 | **Pass** | Idempotency + revision + timeout via LiveKitRpcAdapter ↔ MockApp |
| V7.8 | **Pass** | DS-06 / DS-17 style turns over transport |
| V7.9 | **Pass** | `inject.py` writes JSONL with required fields (dry_run note in record) |

## Commands

```bash
uv run pytest -q
uv run python tools/inject.py
# DEV_MODE=true: uv run python -m mock_app
```

## Gate

**Passed** (automated). Live browser mic-deny is optional manual follow-up, not blocking.
