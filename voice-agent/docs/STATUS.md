# STATUS

The coding agent reads this at the start of every session and updates it at the end.
The human updates the [HUMAN] checkboxes. Keep it short and current.

**Last updated:** 2026-10-02 by agent  
**Current phase:** 2 (gate passed) → ready for Phase 3  
**Current branch:** `phase-2-contract`  
**Next action:** Start Phase 3 (`phase-3-adapters-mock`) with the Phase 3 prompt from `docs/PROMPTS.md`.

---

## Phase tracker

Status values: `not started` · `in progress` · `blocked on human` · `gate passed`
Gate rule: do not start the next phase until every Gate item passes and evidence is in `evidence/phase-N/`.
Tag the commit `phase-N-done`. Phases 6A to 6C may run alongside Phase 5 once Phase 4 is done.

| Phase | Name | Status | Gate items | Tag |
|---|---|---|---|---|
| 0 | Foundations | gate passed | V0.1–V0.5 | `phase-0-done` |
| 1 | Provider spikes | gate passed | waived/partial per ADR-0005/0006 | `phase-1-done` |
| 2 | Contract v1.0 | gate passed | V2.1–V2.4 + `contract-v1.0-frozen` | `phase-2-done` |
| 3 | Adapter + mock app | not started | V3.1–V3.5 | |
| 4 | Conversation engine (text) | not started | V4.1–V4.8 (V4.4 and V4.5 are zero-tolerance) | |
| 5 | Real-time voice pipeline | not started | V5.1–V5.11 | |
| 6 | Conversation design + humanization | not started | V6.1–V6.8 | |
| 7 | Interfaces, metrics, transport, harness | not started | V7.1–V7.9 | |
| 8 | Failure and recovery hardening | not started | V8.1–V8.5 | |
| 9 | Latency tuning + measurement | not started | V9.1–V9.5 | |
| 10 | Acceptance + usability | not started | V10.1–V10.3, V10.5 | |
| 11 | Handover package | not started | V11.1–V11.5 | |

---

## [HUMAN] checklist

### Phase 0
- [x] **0.1** / **0.2** / **V0.5**

### Phase 1
- [x] Waived per ADR-0005 / ADR-0006

### Phase 2
- [x] **2.5** Read contract against SPEC; tagged `contract-v1.0-frozen`.

### Phase 5+
(unchanged — see plan)

---

## Last session summary

Phase 2 gate closed: V2.1–V2.4 + human tag `contract-v1.0-frozen`. Ready for Phase 3 (adapters + mock app).
