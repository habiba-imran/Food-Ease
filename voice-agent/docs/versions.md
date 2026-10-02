# Pinned versions and model IDs

Update this file whenever a dependency or model choice changes. Exact pins come from the lockfile / installer output — never invent numbers (R8).

## Tooling (Phase 0)

| Item | Version / value | Source |
|---|---|---|
| Python | 3.12 (requires `>=3.12,<3.15`) | `.python-version`, `pyproject.toml` |
| Package manager | uv `0.10.6` | `uv --version` |
| `python-dotenv` | `1.2.4` | `uv.lock` / `importlib.metadata` |
| pytest | `9.1.1` | `uv.lock` |
| ruff | `0.16.10` | `uv.lock` |
| pyright | `1.1.414` | `uv.lock` (ADR-0001) |
| pre-commit | `4.6.2` | `uv.lock` |
| gitleaks (pre-commit hook) | `v8.24.3` | `.pre-commit-config.yaml` |

## SDKs (not installed in Phase 0)

| Item | Status | Notes |
|---|---|---|
| `livekit-agents` | deferred (ADR-0002) | Plan cites ~1.5; PyPI current inspected as 1.8.4 — pin in Phase 1 after docs read (R7) |
| Deepgram / Cartesia / Gemini plugins | deferred | Phase 1 spikes |

## Models and voice (placeholders until Phase 1 decisions)

| Setting | Placeholder in `.env.example` | Chosen ID |
|---|---|---|
| `STT_MODEL` | `flux-general-en` | TBD (Phase 1) |
| `LLM_MODEL` | `gemini-3.1-flash-lite` | TBD (Phase 1) |
| `LLM_THINKING_LEVEL` | `minimal` | TBD (Phase 1) |
| `TTS_MODEL` | `sonic-3.6` | TBD (Phase 1) |
| `TTS_VOICE_ID` | `replace-after-phase-1-audition` | TBD (Phase 1 audition) |

## Other runtime defaults

| Setting | Value |
|---|---|
| `IDLE_PROMPT_1_SECONDS` | `8` |
| `IDLE_PROMPT_2_SECONDS` | `20` |
| `RECORD_AUDIO` | `false` |
| `DEV_MODE` | `false` |
| LiveKit region | auto-routed (ADR-0003) |
