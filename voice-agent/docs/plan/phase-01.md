## Phase 1 — Provider spikes (Size M)

**Goal:** choose models, turn-taking mode and voice **by evidence**. Throwaway scripts in `spikes/`.

### 1.1 STT: Deepgram Flux vs Nova-3

- **[HUMAN]** Record fixtures (git-ignored, never in handover): 12 utterances × 2 takes × 3 conditions (laptop mic quiet, earphones quiet, laptop mic with moderate background noise) ≈ 72 short clips. Include: "vegetarian under eight hundred", "show burgers", "add two", "actually make it one", "the second one", "one fifty rupees", "checkout", "stop", and several Pakistani dish names. Write `fixtures/ground_truth.json` with the exact intended text. If anyone else records, get consent.
- **[AGENT]** Script that streams each fixture to Flux (LiveKit Deepgram `STTv2`, `flux-general-en`) and to Nova-3. Log interim vs final events, end-of-turn timing, word error rate. Test keyterm boosting for dish names where supported. Report accuracy on **numbers, prices and quantities separately**.

### 1.2 TTS: Cartesia Sonic 3.6 and voice choice

- **[AGENT]** For each shortlisted voice: time-to-first-byte over 30 runs; `generation_config` speed / volume / emotion; `[laughter]`-style tags; and a number sheet ("Rs. 850", "PKR 1,500", "150", "800–1,000", "two items, total 1,700"). Confirm the installed LiveKit Cartesia plugin accepts `sonic-3.6`; if not, record the fallback.
- **[AGENT]** Explicitly test whether **speed and volume work on the chosen model**. Cartesia's docs note they were temporarily disabled on sonic-3.5 and remain on sonic-3.
- **[HUMAN] Voice audition (this decides how human it feels).** Shortlist 4 English voices (warm, clear, calm, mid-pace). Generate the same 8 lines per voice: greeting, listing results, apology after failure, checkout confirmation, a correction, a long item description, an error message, a goodbye. Listen on laptop speakers and earphones. Score 1–5: clarity, warmth, naturalness, pacing, "not overdramatic", consistency. Get at least one other listener's independent scores (any friend or classmate). Pick a primary and a backup voice; record IDs.

### 1.3 LLM: Gemini 3.1 Flash-Lite (or substitute)

- **[AGENT]** With the 13 function declarations: 30 requests at `thinking_level` minimal and low (TTFT and total time), 20 tool-calling utterances scored for tool/argument correctness, and **10 sample conversational replies per model** saved for a human read (tone, brevity, warmth). Report p95/max separately. Test one fallback model with the same script.
- **[HUMAN]** Read the sample replies aloud; mark any that sound stiff, wordy or salesy.

**Strict guidelines**

- Every Gemini call sets `thinking_level` explicitly (Gemini 3 defaults to high, which is wrong for voice).
- Free-tier latency can be spiky. Choose from the distribution, not a best-case run.
- If speed/volume are unsupported on the chosen Sonic model, log an ADR choosing one of: (a) pin an older Sonic model for speed control; (b) disable the speed preference and tell the user honestly; (c) emit an `agent.control` volume-preference event for a frontend to honor, **[LATER]**, default (b) until then. Never claim a capability the voice lacks.
- Fixtures are personal audio: local only, git-ignored, delete after Phase 10.

**Verification**

| ID | Check | Pass condition |
|---|---|---|
| V1.1 | Raw CSVs for STT, TTS, LLM in `evidence/phase-1/` | Present with n, percentiles, conditions |
| V1.2 | Number/price/quantity accuracy per STT model | Chosen model has no systematic number errors, or the weakness is documented |
| V1.3 | Number-sheet audio reviewed by ear | Every price/quantity unambiguous, or a Phase 6 verbalizer fix logged |
| V1.4 [HUMAN] | Audition scorecard + primary/backup voice IDs | Recorded in `docs/decisions.md` |
| V1.5 | LLM tool-call accuracy ≥ 90% on 20 utterances | Meets, or fallback chosen |

**Gate:** `docs/decisions.md` records STT model + provisional turn mode, TTS model + voice ID + backup, LLM + thinking level + fallback, and the speed/volume decision, each linked to raw data.

---

