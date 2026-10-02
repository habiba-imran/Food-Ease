# Phase 10.2 / 10.3 — [HUMAN] checklist

Agent stopped here per plan. Fill results into `evidence/phase-10/acceptance.md` (or append notes below). Do **not** invent scores.

## 10.2 Live audio-dependent tests (≥3 runs each)

| ID | Script reminder | Runs (pass/fail) | Notes |
|---|---|---|---|
| T01 | Opt in; say nothing — welcome once | | |
| T02 | Stay silent after welcome | | |
| T03 | Interrupt greeting: “Show burgers.” | | |
| T04 | Pause mid: “I want… maybe a spicy… burger.” | | |
| T09 | GUI navigate then “Where am I?” | | (text auto-pass exists; confirm live) |
| T10 | Stop / Repeat / Go back / Slower | | |
| T15 | Deny mic / mute | | |
| T17 | Kill STT/LLM/TTS (fault toggles OK) | | |
| T18 | Regional / noisy mic | | |
| T20 | Interrupt mid cart mutation | | |

## 10.3 Usability (optional P1) — 3–5 fresh users

Task: “find something vegetarian under 800, add two, change to one, place demo order.”

- Consent recorded (anonymized notes only; no raw audio by default)
- Task completion / errors / naturalness / trust / SR collision notes:

(After you paste top 3 breakdown types, agent does 10.4 fixes + re-run suites.)
