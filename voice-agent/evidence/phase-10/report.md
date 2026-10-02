# Phase 10 evidence report

**Branch:** `phase-10-acceptance`  
**Date:** 2026-10-02  

## Built

| Task | Deliverable |
|---|---|
| 10.1 | `tools/run_acceptance.py` → `evidence/phase-10/acceptance.md` + traces |
| T09 fix | Mock `route` exposes category name for orientation |
| 10.2/10.3 | Stopped — `evidence/phase-10/human/checklist.md` |

## Verification

| ID | Status | Notes |
|---|---|---|
| V10.1 | **Pass** (structure) | 20/20 rows recorded (18 automated pass; T04/T18 `pending_human`) |
| V10.2 | **Partial** | Must-pass automated set green in text/logic; live audio musts still need 10.2 |
| V10.3 | **Pass** | `uv run python tools/run_acceptance.py` reproduces |
| V10.4 | **Pending [HUMAN]** | Usability sessions |
| V10.5 | **Pass** (pre-10.4) | Full pytest 212 green; dialogue suite unchanged until 10.4 fixes |

## Commands

```bash
uv run python tools/run_acceptance.py
uv run pytest -q
uv run python tools/run_dialogue_suite.py
```

## [HUMAN]

1. **10.2** — Live audio tests in the checklist (T01–T04, T09/T10/T15/T17/T18/T20 as marked).
2. **10.3** — Optional usability (3–5 users).
3. Paste top 3 session breakdowns → agent runs **10.4**.

## Gate

Not closed until 10.2 fills live must-pass items (or you waive them with an ADR). Automated half is done.
