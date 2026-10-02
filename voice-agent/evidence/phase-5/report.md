# Phase 5 evidence report

**Branch:** `phase-5-voice-pipeline`  
**Date:** 2026-10-02  
**SDK:** livekit-agents `1.8.4` (docs-first per R7)

## Built

| Task | Deliverable |
|---|---|
| 5.0 | `harness/` v0 — `index.html`, `app.js`, `token_server.py` |
| 5.1 | `session.py` — configs **A** / **B**; Cartesia word timestamps; Gemini thinking_level |
| 5.2 | `worker.py` — prewarm; consent-gated join |
| 5.3 | Greeting pool, snapshot timeout, resume, cache |
| 5.4 | Idle tips (fake-clock tests) |
| 5.5 | `TurnHandlingOptions` starting values |
| 5.6 | Interruption reconciler |
| 5.7 | ADR-0008 — preemptive off + `TurnCommitGate` |
| 5.8 | NC env toggle (module not wired on this tier) |
| 5.9 | Control fast-path + TTS speed helper |
| 5.10 | **Waived** — ADR-0009 (no live conversation) |

## Verification (honest status)

Live-audio items are **pending**, not passed (ADR-0009 / R8 / R11).

| ID | Status | Notes |
|---|---|---|
| V5.1 | **pending** | Needs live T01 (silence → greeting) |
| V5.2 | **done** | Idle controller: tip1 → tip2 → quiet; no loop (fake clock) |
| V5.3 | **pending** | Needs live T03 (interrupt greeting) |
| V5.4 | **pending** | Needs live T04 hesitation trials + counts |
| V5.5 | **pending** | Needs live T10 by voice + logs (fast-path unit match exists; not sufficient alone) |
| V5.6 | **pending** | Needs live T20 (reconciler unit test ≠ live interrupt) |
| V5.7 | **done** | TurnCommitGate + `PREEMPTIVE_GENERATION=false` (ADR-0008); 0 mutations when uncommitted/discarded |
| V5.8 | **pending** | Needs live event-log overlap check (helper unit test ≠ live log) |
| V5.9 | **pending** | Needs live false-interruption (cough / mm-hmm); UNTESTED on real mic |
| V5.10 | **done** | Snapshot-timeout unit: greets without context; recovers when snapshot arrives |
| V5.11 | **pending** | Needs live 20-minute soak |

## Commands

```bash
uv sync
uv run pytest -q
```

**114 passed** (automated suite only). No live voice session run.

## Gate

**Not fully closed.** Done: V5.2, V5.7, V5.10. Waived: task **5.10** only (ADR-0009). Pending (before Phase 9): V5.1, V5.3–V5.6, V5.8, V5.9, V5.11 — echo/clipping/overlap/false-interruption UNTESTED with real voice/mic.
