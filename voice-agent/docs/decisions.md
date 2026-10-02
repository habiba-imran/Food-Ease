# Architecture Decision Records

Format per entry: **context → decision → evidence → date**.

Newest entries at the top.

---

## ADR-0012 — Phase 10 live audio / usability waived

- **Context:** Phase 10.2 requires live audio runs (≥3 each) for T01–T04, T09, T10, T15, T17, T18, T20. Phase 10.3 is optional usability with fresh participants. Habiba asks to skip and start Phase 11.
- **Decision:**
  1. **10.2 and 10.3 waived** (not failed). No fabricated live or usability scores (R8).
  2. Keep **10.1** automated acceptance record (`evidence/phase-10/acceptance.md`): 18 automated pass; T04/T18 remain `pending_human` / known-limitation under this ADR.
  3. **10.4** deferred (no session breakdowns to fix). Dialogue/safety suites stay as last automated green run.
  4. Close Phase 10 automated gate; proceed to Phase 11 handover. Live must-pass items in V10.2 that need audio stay **documented limitations**, not claimed passes.
- **Evidence:** Habiba instruction 2026-10-02 (“SKIP AND START 11”); checklist empty of live runs.
- **Date:** 2026-10-02

---

## ADR-0011 — Phase 9 live Mode 1 / Mode 2 campaign waived

- **Context:** Phase 9 requires Mode 1 injection (≥30 turns + ≥10 interruptions) and Mode 2 live sessions across multiple devices/conditions (built-in mic, earphones, household noise, venue network). Habiba cannot run that multi-device campaign now and asks to skip and proceed.
- **Decision:**
  1. **Live Mode 1 / Mode 2 measurement and V9.3–V9.4 live sample sizes are waived** (not failed). No fabricated §7 p50/p95 numbers (R8).
  2. Keep Phase 9 **tooling** (campaign manifest, `inject_live`, report generator, interruption fixture sweep, tuning env knobs, V9.5 regression hook). Empty/placeholder latency tables stay labelled incomplete.
  3. Close Phase 9 gate as **waived for live campaign**; proceed to Phase 10. Optional: run Mode 1/2 later before final handover demos if time allows.
- **Evidence:** Habiba instruction 2026-10-02 (“skip… multiple devices… proceed to next”); no Mode 1/2 JSONL with measured timings.
- **Date:** 2026-10-02

---

## ADR-0010 — Phase 6 V6.2 attested; V6.6 / V6.7 waived

- **Context:** Habiba listened to the pronunciation sheet audio and reported all lines OK, but did not fill the markdown herself; asked the agent to record it. Formal dogfooding (10+5 sessions) and listening panel (≥5 listeners, 12 clips, means) were not run — no time / not written.
- **Decision:**
  1. **V6.2 Pass** by human attestation (0 price/qty misreads, 0 dish misreads); sheet filled under `evidence/phase-6/human/pronunciation_sheet.md`.
  2. **V6.6 and V6.7 waived** (not failed, not fabricated). No invented panel means or dogfood tag counts (R8). Delivery stays emotion-off / default pace (6C.2) until a real panel exists.
  3. Close Phase 6 automated+attested gate; proceed when human starts Phase 7.
- **Evidence:** Habiba chat 2026-10-02 (“all are okay… write yourself”); no panel/dogfood raw logs.
- **Date:** 2026-10-02

---

## ADR-0009 — Phase 5 task 5.10 waived (no live conversation)

- **Context:** Task 5.10 asks for ~10 minutes of free conversation (earphones, then speakers) to note echo self-interruption, clipped syllables, odd pauses, and overlaps. The human has no time and accepts the deviation.
- **Decision:** **5.10 is waived** (not failed). No live-session observations exist yet. Echo, clipping, overlap, and false-interruption behavior are **UNTESTED with a real voice and mic**. They **must be tested before Phase 9**. Do not mark any V5 verification that requires live audio as passed. Those items stay **pending**, not waived.
- **Evidence:** Human instruction 2026-10-02; no `evidence/phase-5` live notes or session logs.
- **Date:** 2026-10-02

---

## ADR-0008 — Speculative / preemptive generation safety (Phase 5.7)

- **Context:** Flux eager EOT and LiveKit `preemptive_generation` can start the LLM before the user turn is committed. Task 5.7 requires determining whether a tool can *execute* in a generation later discarded; V5.7 requires **0 cart mutations** from discarded generations.
- **Investigation (livekit-agents 1.8.4):** In `AgentActivity` pipeline reply, LLM may run early, but `perform_tool_executions` is started only **after** `speech_handle._wait_for_authorization()` / play authorization (`agent_activity.py` ~3642–3728: “start to execute tools (only after play())”). Maintainers also state tools run after generation is authorized (livekit/agents#3414). Function *call objects* can be created before authorization; execution is gated by the framework — but races and future SDK changes make this **not a hard product guarantee** for cart mutations.
- **Decision:**
  1. Default **`PREEMPTIVE_GENERATION=false`** (disable speculative LLM) for FoodEase until Phase 9 explicitly re-enables it after live V5.7 proof.
  2. **Belt-and-suspenders:** `TurnCommitGate` refuses mutating / navigation ops until `on_user_turn_completed` marks the turn committed; discarded generations clear the gate.
  3. Pure read tools (`get_cart`, `get_item_details`, `get_current_context`, `checkout.get_summary`) remain allowed without commit.
- **Evidence:** Installed SDK source 1.8.4; unit tests `test_v57_zero_mutations_on_discarded_generation`, `test_agent_tool_blocked_until_committed`.
- **Date:** 2026-10-02

---

## ADR-0007 — Phase 4 V4.2 real-LLM campaign deferred

- **Context:** V4.2 asks for ≥40 real-LLM utterances. Gemini free tier already returned 429 in Phase 1; Phase 4 logic is covered by a scripted fake LLM (V4.1) and RulePlanner acceptance traces.
- **Decision:** Gate Phase 4 on V4.1 + V4.3–V4.8 with the fake/scripted planners. Treat V4.2 as **deferred** to Phase 5/6 when voice+LLM are exercised live (or when quota allows). No fabricated tool-accuracy %.
- **Evidence:** Phase 1 429 logs; Phase 4 test suite 93 passed without live Gemini calls.
- **Date:** 2026-10-02

---

## ADR-0006 — Phase 1 closed early; provisional TTS/LLM choices

- **Context:** Human asked to complete Phase 1 quickly and skip remaining spike work (not mandatory). Full audition scoring, LLM tool/sample campaign, and extra TTS timing were cut. Gemini free tier returned **429 RESOURCE_EXHAUSTED** during latency runs.
- **Decision (provisional, refine in Phase 5/9 from live data):**
  1. **TTS:** Cartesia **`sonic-3.6`**. Primary voice **Jacqueline** (`9626c31c-bec5-4cca-baa8-f8ba9e84c8bc`). Backup **Katie** (`f786b574-daa5-4673-aa0c-cbe3e8534c02`).
  2. **LLM:** **`gemini-3.1-flash-lite`** with **`thinking_level=minimal`**. Fallback **`gemini-2.5-flash-lite`**.
  3. **Speed/volume:** Treated as **available** on sonic-3.6 for now (API accepted `generation_config` in the TTS spike). If live demos disagree, prefer honest “not available” messaging (plan option b).
  4. **Waived (not failed):** V1.3 ear review, V1.4 audition scorecard, V1.5 tool-accuracy ≥90%, remaining LLM/TTS spike volume. Partial evidence kept under `evidence/phase-1/` (TTS CSV + partial LLM CSV). No fabricated metrics.
- **Evidence:** Health checks PASS; `tts.csv` / `tts_meta.json`; `llm.csv` (30+30 latency, 3 tools); human skip instruction 2026-10-02; Cartesia credits used 2524/8000.
- **Date:** 2026-10-02

---

## ADR-0005 — STT fixtures skipped; provisional Flux + STT turn detection

- **Context:** Phase 1 task 1.1 requires ~72 recorded STT fixtures + `fixtures/ground_truth.json`. The human has no time to record and accepts the deviation.
- **Decision:**
  1. **Do not run** the STT spike. A script may exist under `spikes/` but must not be executed without fixtures.
  2. **Provisional STT choice:** Deepgram **Flux English** with **STT-based turn detection** (config A).
  3. **Config B** (Nova-3 + Silero VAD + LiveKit turn detector) remains runnable per plan task 5.1; the **final** STT/turn choice is made from **live-session data in Phase 5/9**, not from fabricated WER numbers.
  4. Verification **V1.1 / V1.2 are waived for the STT portion** (not failed). No invented STT accuracy, WER, or number/price accuracy metrics.
- **Evidence:** Human instruction, Phase 1 session, 2026-10-02.
- **Date:** 2026-10-02

---

## ADR-0004 — Repo layout: Habiba voice agent in `voice-agent/`

- **Context:** Habiba owns the voice agent; Zainab owns frontend/backend. They must not share one mixed tree.
- **Decision:** All Habiba Phase work lives under `HCI-PROJECT/voice-agent/` (this package). Zainab adds a **sibling** folder later (e.g. `website/`). Root `HCI-PROJECT/README.md` only describes the boundary. Open `voice-agent/` as the Cursor workspace for agent phases.
- **Evidence:** Human instruction at Phase 0 close, 2026-10-02.
- **Date:** 2026-10-02

---

## ADR-0003 — LiveKit Cloud region (Phase 0 human decision)

- **Context:** Plan task 0.2 asks for the LiveKit Cloud region closest to test/demo.
- **Decision:** Region remains **auto-routed** on the free plan; region pinning is Scale-only and unavailable for this project tier.
- **Evidence:** Human report, 02 Oct 2026 (Phase 0 kickoff update).
- **Date:** 2026-10-02

---

## ADR-0002 — livekit-agents install deferred to Phase 1

- **Context:** Plan architecture cites `livekit-agents ~1.5`. Phase 0 is foundations only ("nothing voice-related yet"). PyPI current line as of this scaffold is `1.8.x` (requires Python `>=3.10,<3.15`).
- **Decision:** Do **not** install `livekit-agents` in Phase 0. Record candidates in `docs/versions.md`. Phase 1 will pin the exact SDK after reading docs for the installed version (R7); if the pin is not `~1.5`, add a follow-up ADR.
- **Evidence:** Phase 0 scope; PyPI `livekit-agents` info version `1.8.4` checked 2026-10-02.
- **Date:** 2026-10-02

---

## ADR-0001 — Type checker is pyright

- **Context:** Phase 0 allows `pyright` or `mypy`.
- **Decision:** Use **pyright** (`uv run pyright`) for the scaffold.
- **Evidence:** Chosen at Phase 0 scaffold; recorded in `AGENTS.md` Commands.
- **Date:** 2026-10-02
