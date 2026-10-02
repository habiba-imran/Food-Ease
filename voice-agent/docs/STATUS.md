# STATUS

The coding agent reads this at the start of every session and updates it at the end.
The human updates the [HUMAN] checkboxes. Keep it short and current.

**Last updated:** 2026-10-02 by agent  
**Current phase:** 1 (gate passed with waivers) → ready for Phase 2  
**Current branch:** `phase-1-provider-spikes`  
**Next action:** Start Phase 2 (`phase-2-contract`) with the Phase 2 prompt from `docs/PROMPTS.md`.

---

## Phase tracker

Status values: `not started` · `in progress` · `blocked on human` · `gate passed`
Gate rule: do not start the next phase until every Gate item passes and evidence is in `evidence/phase-N/`.
Tag the commit `phase-N-done`. Phases 6A to 6C may run alongside Phase 5 once Phase 4 is done.

| Phase | Name | Status | Gate items | Tag |
|---|---|---|---|---|
| 0 | Foundations | gate passed | V0.1–V0.5 | `phase-0-done` |
| 1 | Provider spikes | gate passed | waived/partial per ADR-0005/0006; see `evidence/phase-1/report.md` | `phase-1-done` |
| 2 | Contract v1.0 | not started | V2.1–V2.4 + tag `contract-v1.0-frozen` | |
| 3 | Adapter + mock app | not started | V3.1–V3.5 | |
| 4 | Conversation engine (text) | not started | V4.1–V4.8 (V4.4 and V4.5 are zero-tolerance) | |
| 5 | Real-time voice pipeline | not started | V5.1–V5.11 | |
| 6 | Conversation design + humanization | not started | V6.1–V6.8 | |
| 7 | Interfaces, metrics, transport, harness | not started | V7.1–V7.9 | |
| 8 | Failure and recovery hardening | not started | V8.1–V8.5 (zero tolerance: duplicate mutations, false success) | |
| 9 | Latency tuning + measurement | not started | V9.1–V9.5 | |
| 10 | Acceptance + usability | not started | V10.1–V10.3, V10.5 | |
| 11 | Handover package | not started | V11.1–V11.5 | |

---

## [HUMAN] checklist (only you can do these; the agent stops and waits)

Source: `docs/PLAN.md`. "Needed before" says which agent work is blocked until it is done.

### Phase 0
- [x] **0.1** Accounts/keys + provider-limits sheet.
- [x] **0.2** LiveKit region (auto-route → ADR-0003).
- [x] **V0.5** provider-limits filled.

### Phase 1
- [x] **1.1** STT fixtures — **waived** (ADR-0005).
- [x] **1.2 / V1.4** Voice audition — **waived for gate**; provisional voices in ADR-0006 (optional listen later: `evidence/phase-1/audio/audition/`).
- [x] **1.3** LLM read-aloud — **waived for gate** (ADR-0006).

### Phase 2
- [ ] **2.5** Read the contract once against the spec; tag `contract-v1.0-frozen`.

### Phase 5
- [ ] **5.10** 10 minutes of free conversation (laptop mic + earphones, then speakers). Note echo, clipped syllables, odd pauses, overlaps.

### Phase 6
- [ ] **6D.1** Pronunciation sheet (50 lines). Mark every misread. *V6.2: 0 price/quantity misreads.*
- [ ] **6D.2** Dogfooding: 10 free voice sessions, tag breakdowns, then a second round of at least 5.
- [ ] **6E.1** Listening panel: 12 clips, at least 5 listeners, scores 1 to 5, A/B contested choices.

### Phase 9
- [ ] **9.1** Fix and record the test setup (browser, device, network, region, account tiers, quota headroom).
- [ ] **9.6** Run Mode 2 live sessions (including noise) and one session on the demo venue's network.

### Phase 10
- [ ] **10.2** Run audio-dependent tests live: T01–T04, T09, T10, T15, T17, T18, T20 (at least 3 runs each).
- [ ] **10.3** (P1) Usability sessions with 3 to 5 participants. Consent, anonymized notes only.
- [ ] **10.4** Final conversation pass with the agent: fix the top 3 breakdown types.

### Phase 11
- [ ] **11.6** Cold-read test: a classmate runs the agent and harness using only the docs.
- [ ] **11.7** Tag `voice-agent-v1.0-handover`.

---

## Open [LATER] decisions (a default applies; none of these block a phase)

- [ ] **2.6** Send `contract/v1/` to Zainab for optional review, whenever convenient.
- [ ] **11.8** After handover: run the conformance suite against Zainab's adapter; adapt `LiveKitRpcAdapter` if needed.
- Listed in Phase 11 `OPEN_DECISIONS.md`: transport details, confirmation-token use, mute ownership,
  speed/volume forwarding, results-list identification, topic names.

---

## Known issues, deviations from the plan, ADRs

- ADR-0005: STT fixtures skipped; provisional Flux + STT turn detection.
- ADR-0006: Phase 1 closed early; provisional TTS/LLM; spike extras waived.
- Gemini free-tier 429 observed during Phase 1 latency runs.

---

## Last session summary

Phase 1 closed with waivers (ADR-0005/0006). TTS spike done (2524 Cartesia credits). LLM latency partial; tool/sample spikes skipped per human. Ready for Phase 2 contract.
