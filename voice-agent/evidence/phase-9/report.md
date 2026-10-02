# Phase 9 evidence report

**Branch:** `phase-9-latency`  
**Date:** 2026-10-02  
**Gate:** **Waived for live campaign** (ADR-0011). Tooling retained; no fabricated §7 metrics (R8).

## Built (kept)

| Task | Deliverable |
|---|---|
| 9.2 scaffold | `tools/run_latency_campaign.py` — 30 + 10 turn manifest |
| 9.3 hooks | Env interruption/endpointing knobs; `configs/latency_frozen.json` |
| 9.4 fixtures | `tools/run_interruption_tuning.py` → `interruption_tuning.json` |
| Report | `tools/generate_latency_report.py` + `latency_report.py` |
| Live client | `tools/inject_live.py` (ready when a room exists later) |
| V9.5 | `tools/run_v95_regression.py` — automated suite still green |

## Verification

| ID | Status | Notes |
|---|---|---|
| V9.1 | **Tooling only** | Lever README + generator; no live lever tables |
| V9.2 | **Pass** (tooling) | One-command report from JSONL when data exists |
| V9.3 | **Waived** (ADR-0011) | Multi-device / Mode 1 sample size not run |
| V9.4 | **Waived** (live) | Fixture sweep only; no live met/not-met §7 table |
| V9.5 | **Pass** | Automatable regression still runs |

## [HUMAN] skipped

9.1 setup sheet and 9.6 Mode 2 sessions **not required** to close this phase under ADR-0011.
