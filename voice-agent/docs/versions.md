# Pinned versions and model IDs

Update this file whenever a dependency or model choice changes. Exact pins come from the lockfile / installer output — never invent numbers (R8).

## Tooling

| Item | Version / value | Source |
|---|---|---|
| Python | 3.12 (requires `>=3.12,<3.15`) | `.python-version`, `pyproject.toml` |
| Package manager | uv `0.10.6` | `uv --version` |
| `python-dotenv` | `1.2.4` | `uv.lock` |
| pytest | `9.1.1` | `uv.lock` |
| ruff | `0.16.10` | `uv.lock` |
| pyright | `1.1.414` | `uv.lock` (ADR-0001) |
| pre-commit | `4.6.2` | `uv.lock` |
| gitleaks (pre-commit hook) | `v8.24.3` | `.pre-commit-config.yaml` |

## SDKs (Phase 1)

| Item | Version | Notes |
|---|---|---|
| `livekit-agents` | `1.8.4` | ADR-0002 follow-up; Phase 5 uses `TurnHandlingOptions` + `inference.TurnDetector` (docs; plugin turn_detector deprecated) |
| `livekit-api` | `1.2.1` | |
| `livekit-plugins-cartesia` | `1.8.4` | `word_timestamps=True` for aligned captions |
| `livekit-plugins-deepgram` | `1.8.4` | Config A: `STTv2` Flux; Config B: Nova-3 |
| `livekit-plugins-google` | `1.8.4` | |
| `livekit-plugins-silero` | `1.8.4` | VAD (both configs; interruptions) |
| `livekit-plugins-turn-detector` | `1.8.4` | Extra installed; prefer `inference.TurnDetector` per 1.8 docs |
| `deepgram-sdk` | `7.12.0` | |
| `cartesia` | `4.2.0` | |
| `google-genai` | `2.27.0` | |

## Models and voice (provisional — ADR-0005 / ADR-0006)

| Setting | Chosen ID |
|---|---|
| `STT_MODEL` | `flux-general-en` (provisional; final in Phase 5/9) |
| Turn mode | STT-based (config A); config B kept for Phase 5.1 |
| `LLM_MODEL` | `gemini-3.1-flash-lite` |
| `LLM_THINKING_LEVEL` | `minimal` |
| LLM fallback | `gemini-2.5-flash-lite` |
| `TTS_MODEL` | `sonic-3.6` |
| `TTS_VOICE_ID` (primary) | `9626c31c-bec5-4cca-baa8-f8ba9e84c8bc` (Jacqueline) |
| TTS backup | `f786b574-daa5-4673-aa0c-cbe3e8534c02` (Katie) |

## Other runtime defaults

| Setting | Value |
|---|---|
| `IDLE_PROMPT_1_SECONDS` | `12` |
| `IDLE_PROMPT_2_SECONDS` | `30` |
| `VOICE_PIPELINE_CONFIG` | `A` (Flux+STT) or `B` (Nova-3+VAD+TurnDetector) |
| `SNAPSHOT_TIMEOUT_SECONDS` | `2` |
| `PREEMPTIVE_GENERATION` | `false` (ADR-0008) |
| `NOISE_CANCELLATION` | `false` (toggle; NC module plan-gated) |
| `GREETING_CACHE` | `true` |
| `RECORD_AUDIO` | `false` |
| `DEV_MODE` | `false` |
| LiveKit region | auto-routed (ADR-0003) |
