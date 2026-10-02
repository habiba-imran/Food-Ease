## Phase 0 — Foundations (Size S–M)

**Goal:** accounts, keys, repo, tooling, decision log. Nothing voice-related yet.

**Tasks**

- **0.1 [HUMAN]** Create/verify accounts and keys: LiveKit Cloud project, Deepgram, Cartesia (confirm Sonic 3.6 access on your plan), Google AI Studio. Record, without keys, in `docs/provider-limits.md`: quotas, credits, trial end dates, concurrency limits, each provider's data-use terms for free tiers. **Estimate your total LLM request budget** for Phases 1–10 (the Phase 9 campaign alone is ~120+ turns) and check it fits the free-tier limits.
- **0.2 [HUMAN]** Choose the LiveKit Cloud region closest to where you'll test and demo. Plan one session on the demo venue's network.
- **0.3 [AGENT]** Scaffold with `uv`, Python per `livekit-agents` requirements, `ruff`, `pyright` or `mypy`, `pytest`, pre-commit with a secret scanner (e.g. gitleaks). Copy the spec to `docs/SPEC.md` and this plan to `docs/PLAN.md`.
- **0.4 [AGENT]** `config.py` loads from env and **fails fast** with a clear message if anything is missing. `.env.example` has placeholders only: `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `DEEPGRAM_API_KEY`, `CARTESIA_API_KEY`, `GOOGLE_API_KEY`; non-secret: `STT_MODEL`, `LLM_MODEL`, `LLM_THINKING_LEVEL`, `TTS_MODEL`, `TTS_VOICE_ID`, `IDLE_PROMPT_1_SECONDS`, `IDLE_PROMPT_2_SECONDS`, `RECORD_AUDIO=false`, `DEV_MODE=false`.
- **0.5 [AGENT]** `docs/decisions.md` (ADR log: context → decision → evidence → date) and `docs/versions.md` (exact SDK versions, model IDs, voice ID).

**Strict guidelines**

- `.env` is in `.gitignore` before the first commit.
- Pin dependencies with a lockfile; no unpinned `latest`.
- No provider call at import time.

**Verification**

| ID | Check | Pass condition |
|---|---|---|
| V0.1 | `git grep -nEi "(api[_-]?key|secret|token)\s*[=:]\s*['\"]?[A-Za-z0-9_\-]{16,}"` plus the secret scanner | No hits |
| V0.2 | `uv sync && pytest && ruff check` on the scaffold | Green |
| V0.3 | Remove one env var, run config load | Clear error naming it |
| V0.4 | Every var read by `config.py` is in `.env.example` (scripted) | No drift |
| V0.5 [HUMAN] | `docs/provider-limits.md` filled, including the request-budget estimate | Done |

**Gate:** V0.1–V0.5.

---

