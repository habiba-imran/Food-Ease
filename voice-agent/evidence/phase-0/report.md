# Phase 0 evidence report

**Branch:** `phase-0-foundations`  
**Date:** 2026-10-02  
**Scope:** Agent tasks 0.3, 0.4, 0.5 only. No provider API calls. `.env` was not opened or printed. `docs/provider-limits.md` was not modified (content).  
**Layout note:** At gate close, the Habiba package was moved to `HCI-PROJECT/voice-agent/` (ADR-0004). V0.5 ticked per human instruction.

## What was done

- Scaffolded `uv` package `foodease-agent` (`src/foodease_agent/`), Python `>=3.12,<3.15`, lockfile `uv.lock`.
- Tooling: `ruff`, `pyright`, `pytest`, `pre-commit` + `gitleaks`.
- `config.py` fail-fast loader + `.env.example` (placeholders only).
- `docs/decisions.md` (ADR-0001…0003) and `docs/versions.md`.
- Filled `AGENTS.md` Commands section.
- Restored missing `docs/PLAN.md` from the identical `docs/FoodEase_Voice_Agent_Implementation_Plan.md` so AGENTS paths resolve (content unchanged).

## Verification

| ID | Command / check | Result |
|---|---|---|
| V0.1 | `git grep -nEi '(api[_-]?key|secret|token)\s*[=:]\s*[''\''\"]?[A-Za-z0-9_\-]{16,}'` | No matches |
| V0.1 | Working-tree `rg` with same pattern (excl. `.env`, `.venv`, `.git`) | No matches |
| V0.1 | `uv run pre-commit run gitleaks --all-files` | Passed |
| V0.2 | `uv sync` | OK |
| V0.2 | `uv run pytest` | **21 passed** |
| V0.2 | `uv run ruff check .` | All checks passed |
| V0.2 | `uv run pyright` | 0 errors |
| V0.3 | `uv run python tools/phase0_verify.py` (missing `CARTESIA_API_KEY`) | `Missing required environment variable(s): CARTESIA_API_KEY` |
| V0.4 | `tests/test_env_example_drift.py` (part of pytest) | Pass — config vars ↔ `.env.example` |
| V0.5 [HUMAN] | `docs/provider-limits.md` complete incl. request-budget estimate | **Pass** (human instructed tick 2026-10-02; budget table present; file content not rewritten by agent) |

## Exact commands used

```bash
uv sync
uv run pytest -q
uv run ruff check .
uv run pyright
uv run pre-commit run gitleaks --all-files
uv run python tools/phase0_verify.py
```

## Locked tool versions (from environment after `uv sync`)

| Package | Version |
|---|---|
| python-dotenv | 1.2.4 |
| pytest | 9.1.1 |
| ruff | 0.16.10 |
| pyright | 1.1.414 |
| pre-commit | 4.6.2 |
| uv | 0.10.6 |
| gitleaks hook rev | v8.24.3 |

## Human status (reported; agent did not tick STATUS checkboxes)

- **0.1:** keys in local `.env` (agent did not open the file).
- **0.2:** LiveKit region auto-routed on free plan → ADR-0003.
- **V0.5:** still yours — finish/confirm `docs/provider-limits.md` including request-budget estimate.

## Notes / ADRs

- ADR-0001: type checker = pyright.
- ADR-0002: `livekit-agents` deferred to Phase 1 (Phase 0 is non-voice; PyPI current inspected as 1.8.4 vs plan ~1.5).
- ADR-0003: LiveKit region auto-route.

## Gate

V0.1–V0.5: **pass**. Phase 0 closed.
