## Phase 6 — Conversation design and humanization (Size L)

**Goal:** make it feel like talking to a patient, warm shopping guide. Naturalness comes from three things working together: a good voice (Phase 1), good *conversation behavior* (6A–6B), and well-shaped speech text (6C). **6A–6C can run in parallel with Phase 5 once Phase 4 is done; 6D–6E need the Phase 5 gate.**

### 6A. Conversation design (docs the agent follows)

- **6A.1 [AGENT]** `docs/conversation/PERSONA.md`: a calm, helpful, concise guide; light warmth, no jokes unless the user jokes; respectful register suited to Pakistani English and local food names; never claims to be human, no backstory; may use a product-assistant name.
- **6A.2 [AGENT]** `docs/conversation/DIALOGUE_ACTS.md`: the repertoire the agent uses (greet, orient, offer, narrow, recommend, compare, confirm-result, clarify, repair, apologize, redirect, wrap-up) with 2–3 example phrasings each and rules for when **not** to use them. Include:
  - *Mixed initiative:* vague requests ("I'm hungry", "something light") get **one** narrowing question or a small, data-based suggestion set (2–3 items, with a reason drawn from tags/prices), never a menu dump.
  - *Answer first, details after;* front-load the key info so interruptions lose little.
  - *Relative references:* "the cheaper one", "the spicier one", "the other one", resolved from presented data.
  - *Repair:* when mishearing, offer candidates ("Was that the Zinger Burger or the Zinger Wrap?"); the second consecutive failure offers typed input instead of repeating the same question.
  - *Next-step offers:* at most one relevant offer after a success, not every turn, never after a decline, no upselling by default.
  - *Mirroring:* shorter replies for terse users, more detail for users who ask for it.
  - *Unknown data:* say you don't have that information; never guess ingredients or allergens.
  - *Off-topic / frustration / rudeness:* brief, calm, one line back to the task, offering text or manual browsing when the user is struggling.
- **6A.3 [AGENT]** `docs/conversation/DIALOGUE_SUITE.md`: 20 scenarios (DS-01…DS-20), each with the user turns, the mock state, and the expected behavior: (1) vague hunger; (2) "something light"; (3) "what do you recommend?"; (4) compare two items; (5) "the cheaper one"; (6) "no, I meant the wrap"; (7) change of mind in the cart; (8) small talk; (9) frustrated user; (10) "what did you say?"; (11) interrupt a list with "next"; (12) long silence mid-flow; (13) budget change ("actually under 600"); (14) ingredient question with and without data; (15) vague quantity ("a couple"); (16) "I'll browse myself" then "talk to me again"; (17) change at the checkout confirmation; (18) two intents in one sentence; (19) thanks and goodbye; (20) abusive language.

### 6B. Policy refinement and dialogue suite

- **6B.1 [AGENT]** Iterate the policy prompt (`agent_policy.v2…`) to implement 6A. Each version is logged in `prompts/CHANGELOG.md` with reason and results.
- **6B.2 [AGENT]** `tools/run_dialogue_suite.py`: runs DS-01…DS-20 in text mode (real LLM, mock app), saves transcripts, computes conversation metrics (words per reply, sentences per reply, clarification rate on unambiguous scenarios, unnecessary confirmations on Tier 0/1 actions, repeated-opener rate), and re-runs the V4.4/V4.5 safety suite (R14).

### 6C. Speech text shaping

- **6C.1 [AGENT] `speech_text/` module.**
  1. Sanitizer: strips markdown, bullets, URLs, IDs, emoji.
  2. **Verbalizer:** PKR amounts and quantities spoken unambiguously ("eight hundred fifty rupees", never "eight fifty" or "one fifty"), ranges, totals, positions ("the second of four").
  3. Pronunciation: dictionary for dish/brand names (Cartesia pronunciation dictionaries if supported on the chosen model; otherwise respelling).
  4. Sentence chunking so the first sentence is short and TTS starts early; list items one per sentence with natural pauses via punctuation.
  5. **Two forms:** `spoken_text` for TTS and `display_text` (readable written form of the same words) for captions, so text parity (VA-08) is exact.
- **6C.2 [AGENT] Delivery profile.** Start with Cartesia's default context-driven delivery and good punctuation for natural pauses. Add `generation_config.emotion` (valid values per docs; beta) only for specific moments (welcoming, apologetic after a failure) **if the listening test shows it helps**. Off by default.
- **6C.3 [AGENT] Truthful wait feedback.** If an action is pending longer than ~1.5 s, say one short honest status ("Still checking the cart."), once. Never fill silence for effect. (Optional P2 experiment for the listening panel: a one-phrase lead-in before slow actions. It must contain no success wording; a regex guard enforces this.)

### 6D. Human checks (need the voice pipeline)

- **6D.1 [HUMAN] Pronunciation sheet.** The agent speaks a 50-line sheet (prices, quantities, dish names, ranges, totals). You mark every misread; iterate the dictionary/verbalizer until clean.
- **6D.2 [HUMAN] Conversation dogfooding loop.** 10 free voice sessions (varied people if possible). Tag each breakdown: misheard, too long, robotic, over-asked, ignored context, awkward timing, wrong tone. Hand the tagged list to the agent, fix, and run a second round of ≥ 5 sessions. Repeat until the top breakdown types stop recurring.

### 6E. Listening and conversation panel

- **6E.1 [HUMAN]** Render 12 clips from real sessions. Panel of ≥ 5 listeners (classmates/friends; ideally ≥ 1 regular screen-reader user). Score 1–5: clarity, warmth, naturalness, pace, comfort over a long session, trust, and "sounds like a helpful guide, not a script". A/B contested choices (emotion on vs off; default pace vs slightly slower; with vs without the P2 lead-in). Record results; decide settings via ADR.

**Strict guidelines**

- Never claim to be human; no fillers or stutters inserted to "sound human".
- Spoken price/quantity errors are zero tolerance.
- Replies stay 1–3 short sentences unless asked for more.
- Text transforms never change meaning or numbers.
- Every prompt edit re-runs the safety suite (R14).

**Verification**

| ID | Check | Pass condition |
|---|---|---|
| V6.1 | Verbalizer unit tests (≥ 40 cases: 150 vs 1,500, ranges, totals, decimals, large numbers) | 100% |
| V6.2 [HUMAN] | 50-line pronunciation sheet | **0 misreads of any price/quantity**; ≤ 2 dish-name misreads, listed |
| V6.3 | Dialogue suite DS-01…DS-20 run and read through | Each scenario meets its expected behavior; no safety violation |
| V6.4 | Conversation metrics (project targets) | Clarification rate ≤ 15% on unambiguous scenarios; 0 unnecessary confirmations on Tier 0/1; same opener ≤ 20% of 30 replies; typical reply ≤ ~35 spoken words (except detail requests) |
| V6.5 | `display_text` vs `spoken_text` parity | Same words and numbers |
| V6.6 [HUMAN] | Dogfooding: two rounds completed; top breakdown categories reduced in round 2 | Documented |
| V6.7 [HUMAN] | Listening panel: mean ≥ 4.0/5 on clarity and comfort; no criterion mean < 3.5; "robotic"/"overdramatic" comments investigated | Meets, or ADR explaining |
| V6.8 | Safety suite (V4.4, V4.5) re-run on the final prompt | 0 violations |

**Gate:** V6.1–V6.8; final voice settings and final prompt version recorded.

---

