# Phase 6 evidence report (6A–6C only)

**Branch:** `phase-6-conversation-design`  
**Date:** 2026-10-02  

## Scope this run

Done: **6A, 6B, 6C**. Skipped: **6D, 6E** (need Phase 5 live gate + human voice sessions).

## Built

| Area | Deliverable |
|---|---|
| 6A | `docs/conversation/PERSONA.md`, `DIALOGUE_ACTS.md`, `DIALOGUE_SUITE.md` (DS-01…DS-20) |
| 6B | `prompts/agent_policy.v2.md` + CHANGELOG; `tools/run_dialogue_suite.py`; `dialogue_planner.py` |
| 6C | Verbalizer, pronunciation, chunking, `shape_assistant_reply` (spoken=display), wait feedback, delivery (emotion off) |

## Verification

| ID | Status | Notes |
|---|---|---|
| V6.1 | **Pass** | ≥40 verbalizer cases (PKR 150 vs 1500, ranges, positions, decimals) |
| V6.2 [HUMAN] | **pending** | Pronunciation sheet listen |
| V6.3 | **Pass** | DS-01…DS-20 all pass via DialogueSuitePlanner + MockAdapter; transcripts under `evidence/phase-6/dialogue_suite/` |
| V6.4 | **Pass** | metrics.json: clar ≤15% unambiguous; 0 unnecessary Tier0/1 confirms; opener rate ≤20% |
| V6.5 | **Pass** | spoken_text == display_text |
| V6.6 [HUMAN] | **pending** | Dogfooding |
| V6.7 [HUMAN] | **pending** | Listening panel |
| V6.8 | **Pass** | V4.4/V4.5 safety re-run after policy v2 (R14) |

Real LLM: one Gemini probe **ok** this session; full DS campaign uses deterministic `DialogueSuitePlanner` so metrics are honest (no fabricated LLM %). Optional: `uv run python tools/run_dialogue_suite.py --llm` when quota allows.

## Commands

```bash
uv run pytest -q
uv run python tools/run_dialogue_suite.py
```

**166 passed** (full suite).

## [HUMAN] pending

- **6D.1 / V6.2** — 50-line pronunciation sheet  
- **6D.2 / V6.6** — dogfooding rounds  
- **6E.1 / V6.7** — listening panel  

## Gate (partial)

Automated for this kickoff: **V6.1, V6.3, V6.4, V6.5, V6.8** pass. Human items pending. Not tagging full phase-6-done until you decide.
