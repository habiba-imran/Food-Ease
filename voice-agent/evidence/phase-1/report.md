# Phase 1 evidence report

**Branch:** `phase-1-provider-spikes`  
**Date:** 2026-10-02  
**Scope:** Provider spikes with human-accepted skips. No `.env` opened or printed.

## Provider health (tiny calls)

| Provider | Result |
|---|---|
| LiveKit | PASS |
| Deepgram | PASS |
| Cartesia | PASS (`sonic-3.6` accepted) |
| Gemini | PASS (`gemini-3.1-flash-lite` + `thinking_level=minimal`) |

## What ran

- **TTS:** Audition clips (4 voices × 8 lines, once), number sheet, speed/volume/emotion probes, 10× timing per voice. Credits **2524 / 8000**. Outputs: `evidence/phase-1/tts.csv`, `tts_meta.json`, `audio/` (git-ignored), `cartesia_credits.json`.
- **LLM (partial):** Latency only for primary — 30× `minimal`, 30× `low` on `gemini-3.1-flash-lite`. 3 tool-call rows then stopped. Free-tier **429 RESOURCE_EXHAUSTED** observed under rapid fire (~27 calls); paced resume later. CSV: `evidence/phase-1/llm.csv`.

## What was skipped (waived, not failed)

| Item | Why |
|---|---|
| STT spike + V1.1/V1.2 STT metrics | No fixtures; ADR-0005. No invented WER/accuracy. |
| Full LLM tool suite / samples / fallback campaign / V1.5 | Human: skip extra spike; quota 429. ADR-0006. |
| Full 30× timing on top-2 voices | Human skip; 10× all four already recorded. |
| Human audition scores V1.4 / number-sheet ear check V1.3 / read-aloud 1.3 | Human waived for Phase 1 gate; provisional voice IDs in ADR-0006. |

## Gate decisions (provisional — see `docs/decisions.md`)

- STT: Flux English + STT turn detection (config A); config B later in Phase 5/9.
- TTS: `sonic-3.6`; primary voice Jacqueline; backup Katie.
- LLM: `gemini-3.1-flash-lite`, `thinking_level=minimal`; fallback `gemini-2.5-flash-lite`.
- Speed/volume: treat as supported on sonic-3.6 (API accepted `generation_config`); refine in live Phase 5 if needed.

## Gate

Phase 1 **closed with documented waivers** (ADR-0005, ADR-0006). Not a clean lab pass — sufficient to unblock Phase 2 per human instruction.
