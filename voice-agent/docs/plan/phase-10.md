## Phase 10 — Acceptance testing, usability and final conversation pass (Size M)

**Goal:** formal pass/fail for T01–T20, a small human-centred evaluation (HCI course), and a last conversation-quality pass with fresh users.

**Tasks**

- **10.1 [AGENT]** Runner/checklist generating `evidence/phase-10/acceptance.md`: per T-ID, the exact spoken/typed script, mock scenario, expected observable, result, action-trace excerpt, notes. Automate what can be automated (T05–T08, T11–T14, T16, T19 via text and injection).
- **10.2 [HUMAN]** Run audio-dependent tests live: T01–T04, T09, T10, T15, T17 (fault toggles), T18 (regional pronunciation and noisy mic; log recognition limits), T20. At least 3 runs each; record failures honestly.
- **10.3 [HUMAN] (P1) Usability sessions:** 3–5 participants who haven't heard the agent, a short task script ("find something vegetarian under 800, add two, change to one, check out the demo order"). Include someone who normally uses a screen reader or keyboard if possible. Collect task completion, errors, perceived naturalness, trust, and whether voice and screen-reader audio collided. Consent, anonymized notes only, no raw audio retained by default.
- **10.4 [AGENT + HUMAN] Final conversation pass:** take the top 3 breakdown types from the sessions, fix them, re-run the dialogue suite, the safety suite and T01–T20 automation.

**Strict guidelines**

- A test is "pass" only if the spec's observable condition is met, not "mostly".
- Keep failing results in the record with a cause and status (fixed / known limitation).

**Verification**

| ID | Check | Pass condition |
|---|---|---|
| V10.1 | All 20 tests have a recorded result with trace | 20/20 |
| V10.2 | **Must pass:** T01, T03, T05–T08, T10–T14, T16, T20; others pass or have documented limitations | Met |
| V10.3 | Clean-checkout run reproduces the automated results | Matches |
| V10.4 [HUMAN] | Usability summary (if run) with consent records | Written |
| V10.5 | Dialogue suite + safety suite after final fixes | No regressions |

**Gate:** V10.1–V10.3 and V10.5; defects triaged.

---

