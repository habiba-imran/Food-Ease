# Phase 8 evidence report

**Branch:** `phase-8-failure-hardening`  
**Date:** 2026-10-02  

## Built

| Task | Deliverable |
|---|---|
| 8.1 | `recovery.py` — all 13 VA-17 situations; fault toggles in engine; stop-during-checkout |
| 8.2 | `fallback.py` — LLM/TTS/STT primary→backup selection + log (`FallbackChain`) |
| 8.3 | `confidence.py` — consequential low-confidence clarification gate |
| 8.4 | `reconnect.py` — fresh snapshot, invalidate confirmation, `guard_resubmit` (R4) |
| 8.5 | DS-21…DS-25 in `docs/conversation/DIALOGUE_SUITE.md` + `tests/test_phase8.py` |
| Chaos | `tools/run_chaos.py` — compressed invariant harness (not wall-clock 30 min) |

## VA-17 coverage (V8.2)

| Situation | Test / path |
|---|---|
| Mic denied | `test_mic_denied_and_tts_down` + `FAULTS.mic_denied` |
| No speech | `recover(NO_SPEECH)` + idle (prior phases); silence ≠ submit (`test_t11`) |
| Low confidence | `test_confidence_gate_consequential` + `FAULTS.low_confidence` |
| Two matching | `test_two_matching_items_clarify` |
| False interruption | `recover(FALSE_INTERRUPTION)` + `test_t20_interrupt_mutation_reconcile` |
| STT down | `test_t17` / DS-21; state=`error` (never listening) |
| TTS down | `test_mic_denied_and_tts_down`; text retained + note |
| LLM down/quota | `test_t17` / DS-22; cart unchanged phrasing |
| Action rejected | DS-23 / `test_ds21_25` |
| Action timeout | T14 / DS-24; no resend |
| Connection loss | DS-25 + reconnect manager |
| GUI switch mid-turn | `test_gui_switch_mid_turn_message` |
| Stop during checkout | `test_stop_during_checkout` |

## Verification

| ID | Status | Notes |
|---|---|---|
| V8.1 | **Pass** | T08, T11, T12, T13, T14, T17, T20 automated in `tests/test_phase8.py` |
| V8.2 | **Pass** | 13/13 rows covered (table above) |
| V8.3 | **Pass** | Compressed chaos: 200 trials, 0 false success, 0 stuck listening (`tools/run_chaos.py`). Same invariants as a long soak; not a wall-clock 30-minute live session. |
| V8.4 | **Pass** | `test_v84_reconnect_mid_checkout` — confirmation cleared; unknown action blocked |
| V8.5 | **Pass** | `FallbackChain.choose_llm(primary_failed=True)` → backup; `FAULTS.fail_llm` honest fail |

## Commands

```bash
uv run pytest -q
uv run pytest tests/test_phase8.py -q
uv run python tools/run_chaos.py --trials 200 --seed 42
```

**Full suite:** 207 passed (2026-10-02).

## [HUMAN] / pending

- None required to close Phase 8 gate.
- Optional later: live browser mic-deny (T15) and a real multi-provider LiveKit fallback soak if you want Mode-1 proof beyond the unit `FallbackChain`.

## Gate

**Passed** (automated). Zero false success / zero illegal mutation resend in suite + chaos.
