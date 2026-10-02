# STATUS

The coding agent reads this at the start of every session and updates it at the end.
The human updates the [HUMAN] checkboxes. Keep it short and current.

**Last updated:** 2026-10-02 by agent  
**Current phase:** 3 (gate passed) → ready for Phase 4  
**Current branch:** `phase-3-adapters-mock`  
**Next action:** Start Phase 4 (`phase-4-conversation-engine`) with the Phase 4 prompt from `docs/PROMPTS.md`.

---

## Phase tracker

| Phase | Name | Status | Gate items | Tag |
|---|---|---|---|---|
| 0 | Foundations | gate passed | V0.1–V0.5 | `phase-0-done` |
| 1 | Provider spikes | gate passed | waived/partial ADR-0005/0006 | `phase-1-done` |
| 2 | Contract v1.0 | gate passed | V2.1–V2.4 + `contract-v1.0-frozen` | `phase-2-done` |
| 3 | Adapter + mock app | gate passed | V3.1–V3.5 | `phase-3-done` |
| 4 | Conversation engine (text) | not started | V4.1–V4.8 | |
| 5–11 | (see plan) | not started | | |

---

## [HUMAN] checklist

### Phase 2
- [x] **2.5** `contract-v1.0-frozen`

### Phase 3
(none)

---

## Last session summary

Phase 3 done: `AppAdapter` + `MockAdapter` (28 items, traps, scenarios, GUI sims), conformance suite, V3.1–V3.5 pass. Ready for Phase 4.
