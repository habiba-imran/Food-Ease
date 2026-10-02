## Phase 11 — Handover package (Size S–M)

**Goal:** produce the 10 deliverables so the website can be connected later without rewriting voice logic, **self-serve and independent of Zainab's schedule**.

| # | Deliverable | Source |
|---|---|---|
| 1 | Working standalone voice-agent service | Phases 5–8 |
| 2 | Full source project, provider/adapter split, dependency manifest, **no keys, no raw recordings** | All |
| 3 | `.env.example` + chosen model IDs, voice ID, quota/trial assumptions | Phases 0–1 |
| 4 | Frozen integration contract + sample exchanges | Phase 2 |
| 5 | Mock adapter, MockApp, deterministic data, scenario controls | Phases 3, 7 |
| 6 | Behavior/prompt specification (final prompt, persona, dialogue acts, dialogue suite results) + one full sample dialogue incl. a correction | Phases 4, 6 |
| 7 | Session/transcript interfaces, documented and inspectable | Phase 7 |
| 8 | Interruption and latency evidence | Phase 9 |
| 9 | Acceptance-test record T01–T20 | Phase 10 |
| 10 | Integration handover note | below |

**Tasks**

- **11.1 [AGENT]** `docs/handover/INTEGRATION_NOTE.md`: entry/exit points, events, the RPC methods a frontend must register, state-sync requirements (revision rules, GUI-change reporting), the optional confirmation-token flow, mute ownership, supported languages (English demo; Urdu is a stretch, not promised), hard constraints, known limitations.
- **11.2 [AGENT]** `docs/handover/FRONTEND_QUICKSTART.md` (1–2 pages): how a website joins the room, registers the RPC methods, consumes transcripts/state, sends context snapshots/updates, with short JavaScript snippets taken from the working MockApp/harness. Written so Zainab can self-serve next month.
- **11.3 [AGENT]** `docs/handover/OPEN_DECISIONS.md`: every **[LATER]** item with your default (transport details, token use, mute ownership, speed/volume forwarding, results-list identification, topic names). Each states "default applies unless changed at integration".
- **11.4 [AGENT]** Clean-checkout test: fresh clone + `.env` from `.env.example` + one documented command starts the agent and passes the smoke suite.
- **11.5 [AGENT]** Final secret/recording scan of the repository and release artifact.
- **11.6 [HUMAN]** Cold-read test: someone other than you (any classmate) follows only the docs to run the agent and the harness. Fix what confuses them.
- **11.7 [HUMAN]** Tag `voice-agent-v1.0-handover`.
- **11.8 [LATER]** After handover, when Zainab is ready: run the conformance suite against her adapter; adapt `LiveKitRpcAdapter` for any differences; joint integration testing then belongs to the orchestration phase, which is outside this plan.

**Verification**

| ID | Check | Pass condition |
|---|---|---|
| V11.1 | Clean clone → agent starts → smoke tests pass using only the docs | Pass |
| V11.2 | Secret and recording scan of the final artifact | Clean |
| V11.3 | Conformance suite passes with `LiveKitRpcAdapter` ↔ MockApp | 100% |
| V11.4 | Each of the 10 deliverables exists at a documented path | 10/10 |
| V11.5 [HUMAN] | Cold-read test completed; issues fixed | Documented |

**Gate:** V11.1–V11.5. Voice-agent scope done.

---

