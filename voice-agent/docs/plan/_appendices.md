## Appendix A — Requirement coverage

| Spec item | Where implemented / verified |
|---|---|
| VA-01 activation & greeting | 5.2, 5.3 · T01, T03 |
| VA-02 silent-user help | 5.4 · T02 |
| VA-03 barge-in & turns | 5.5–5.7, 9.4 · T03, T04, T20 |
| VA-04 humanized speech | Phase 6 (6A–6E) |
| VA-05 context & orientation | 4.3, 4.4, 7.3 · T06, T09 |
| VA-06 domain behavior & safe actions | Phase 4 (4.6, 4.7) · T05–T08, T11–T14 |
| VA-07 exposed states | 7.2 |
| VA-08 text parity | 6C.1, 7.1, 4.9 · T16 |
| VA-09 context subscription | 2.1, 7.3 |
| VA-10–VA-14 contract | Phases 2, 3.4, 4.1, 4.7, 7.4 |
| VA-15 agency & inclusivity | 4.8, 7.1–7.3, 10.3 · T15, T19 |
| VA-16 trust & security | R6, R13, 7.6, 11.5 |
| VA-17 failure & recovery | Phase 8 · T14, T17, T20 |
| §7 latency | Phase 9 |

## Appendix B — Risk register

| Risk | Likelihood / impact | Mitigation |
|---|---|---|
| Free-tier LLM latency spikes or quota exhaustion | High / High | Explicit `thinking_level`; fallback model (8.2); tail-latency measurement (1.3); request-budget estimate (0.1) |
| Eager/preemptive generation triggers a discarded mutation | Medium / Critical | 5.7 gate, V5.7 test, disable preemption if unprovable |
| Speed/volume unavailable on the chosen Sonic model | Medium / Medium | Test in 1.2; ADR; honest user message |
| Echo or noise causes self-interruptions | Medium / Medium | Earphones in demos, noise-cancellation toggle, adaptive interruption, 5.8 |
| Zainab's implementation differs from the contract | Medium / Medium | Contract owned by you; translation inside `LiveKitRpcAdapter`; conformance suite; optional fields |
| Agent sounds like a form (over-confirming, over-asking) | Medium / High | Risk tiers (4.6), "ask only when necessary", V6.4 metrics, dogfooding loop |
| Voice sounds robotic despite a good model | Medium / High | Voice audition, verbalizer, listening panel; no gimmicks |
| Prompt tweaks quietly break safety behavior | Medium / High | R14 regression on every prompt change |
| Demo venue network worse than desk | Medium / Medium | Venue test (9.6); report honestly |
| Scope creep (UI, DB, Urdu) | High / Medium | R10; Urdu only after Phase 11 as a stretch |
| Plan too large for the time available | Medium / High | Appendix D cut line |

## Appendix C — Evidence folder

```
evidence/
  phase-N/report.md                   # commands run, results, redacted logs
  phase-1/   stt.csv  tts.csv  llm.csv  audition-scorecard.md
  phase-6/   dialogue-suite/  pronunciation-sheet.md  dogfooding-rounds.md  listening-panel.md
  phase-9/   raw/*.jsonl  report.md  config-hash.txt
  phase-10/  acceptance.md  traces/
```

## Appendix D — Cut line if time runs short

**Keep (P0):** Phases 0–5; the tiers, confirmation and truthfulness core of Phase 4; 6A–6C essentials (persona, dialogue acts, verbalizer, voice choice), one dogfooding round, and the pronunciation sheet; Phase 7.1–7.4 and 7.7–7.8; Phase 8 rows for action failure, timeout and interruption; a smaller Phase 9 (≥ 20 turns + 5 interruptions, stated); Phase 10.1–10.2; Phase 11 deliverables.
**Defer:** MockApp participant (7.5), cached greeting, provider fallback chain, LiveKit Inference A/B, usability sessions, emotion tuning, P2 lead-in experiment, Urdu.

## Appendix E — Changes from v1.0 (audit)

- Removed every dependency on Zainab: contract is frozen by you; her review is optional; `confirmation_token` is optional; the handover gate no longer needs her confirmation; the audition and listening panels no longer require her.
- Added §0.5 independence principle, a self-serve frontend quick-start, and an open-decisions list with defaults.
- Added a real transport rehearsal: `LiveKitRpcAdapter` (P0) and a MockApp participant (P1).
- Added a minimal talk client in Phase 5 (v1.0 had no way to speak to the agent until Phase 7).
- Rebuilt Phase 6 around conversation design: persona, dialogue acts, a 20-scenario dialogue suite, conversation metrics, a dogfooding loop, and a panel.
- Added interaction-risk tiers so safety does not make the agent robotic, plus prompt-change regression (R14).
- Clarified latency measurement into two labelled modes and added the injection test client.
- Added snapshot-timeout greeting, retention/`RECORD_AUDIO` control, dev-only control surfaces, `navigate` targets (including "back"), an "end session" control, and a request-budget estimate.
- Trimmed the STT fixture set and fixed cross-references and file names.
