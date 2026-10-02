## Phase 8 — Failure, cancellation and recovery hardening (Size M)

**Goal:** the agent stays honest and usable when things break (VA-17).

**Tasks**

- **8.1 [AGENT]** Implement and test every VA-17 row using the fault toggles: mic denied; no speech; low-confidence phrase (ask to repeat or offer a constrained choice for anything consequential); two matching items; noise/false interruption; STT down; TTS down (keep text and status, offer retry/manual); LLM down/quota (say so plainly, preserve app state); action rejected (state the app's reason + a valid next option); action timeout (→ unknown → reconcile → ask); connection loss (rejoin from latest snapshot, no replay of uncertain actions); GUI switch mid-turn (cancel obsolete guidance); "stop" during checkout.
- **8.2 [AGENT]** Provider fallback chain using LiveKit's fallback adapters where available (verify): backup LLM, backup voice. Log which provider served each turn. (P1)
- **8.3 [AGENT]** Confidence handling: consequential intents (quantity, remove, checkout) with low STT confidence or ambiguous referents get a one-line clarification.
- **8.4 [AGENT]** Reconnect: request a fresh snapshot, reset pending confirmation, never resend a mutating action whose outcome is unknown.
- **8.5 [AGENT]** Failure phrasing stays conversational: plain words, once, then the next valid step. Add these to the dialogue suite as DS-21…DS-25 (STT down, LLM quota, rejected action, timeout, reconnect).

**Strict guidelines**

- Never display "listening" when STT is dead.
- No automatic retry for mutations (R4); read-only actions may retry once.

**Verification**

| ID | Check | Pass condition |
|---|---|---|
| V8.1 | T08, T11, T12, T13, T14, T17, T20 | All pass |
| V8.2 | Each of the 13 VA-17 rows has an automated or documented manual test | 13/13 |
| V8.3 | 30-minute chaos run with random fault injection | No duplicate mutation, no false success, no stuck state |
| V8.4 | Reconnect mid-checkout | Confirmation expired; no duplicate order |
| V8.5 | Kill the primary LLM mid-session | Continues on backup or fails honestly |

**Gate:** V8.1–V8.5. Zero tolerance on duplicate mutations and false success.

---

