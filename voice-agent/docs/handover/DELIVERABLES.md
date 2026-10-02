# Handover deliverables map (SPEC §11)

| # | Deliverable | Path(s) |
|---|---|---|
| 1 | Working standalone voice-agent service | `src/foodease_agent/worker.py`, `uv run foodease-worker`, `harness/` |
| 2 | Full source + provider/adapter split | This repo; `pyproject.toml` / `uv.lock`; adapters under `src/foodease_agent/adapters/` |
| 3 | `.env.example` + model/voice IDs | `.env.example`, `docs/versions.md`, `docs/provider-limits.md` |
| 4 | Frozen integration contract + samples | `contract/v1/`, `docs/handover/INTEGRATION_NOTE.md` |
| 5 | Mock adapter + MockApp + scenarios | `src/foodease_agent/adapters/mock.py`, `mock_app/` |
| 6 | Behavior/prompt + sample dialogue | `prompts/agent_policy.v2.md`, `docs/conversation/`, `docs/handover/SAMPLE_DIALOGUE.md` |
| 7 | Session/transcript interfaces | Phase 7 EventBus / product state; harness inspector; `INTEGRATION_NOTE.md` |
| 8 | Interruption / latency evidence | `evidence/phase-9/` (tooling; live campaign **waived** ADR-0011 — no fabricated §7 numbers) |
| 9 | Acceptance T01–T20 | `evidence/phase-10/acceptance.md` (live rows **waived** ADR-0012) |
| 10 | Integration handover note | `docs/handover/INTEGRATION_NOTE.md`, `FRONTEND_QUICKSTART.md`, `OPEN_DECISIONS.md` |
