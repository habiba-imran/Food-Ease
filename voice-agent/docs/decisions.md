# Architecture Decision Records

Format per entry: **context → decision → evidence → date**.

Newest entries at the top.

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
