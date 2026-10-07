# Handover deliverables map (SPEC §11)

Paths below are relative to the **HCI-PROJECT** repo root unless marked *pack*.

## Habiba shipped (do not rebuild)

| # | Deliverable | Path(s) |
|---|---|---|
| 1 | Working standalone voice-agent | `voice-agent/` → `uv run foodease-worker`, `harness/` |
| 2 | Full source + provider/adapter split | `voice-agent/src/foodease_agent/` |
| 3 | `.env.example` + model/voice IDs | `voice-agent/.env.example`, `orchestration/.env.example` |
| 4 | Frozen integration contract + samples | **pack** `contract/v1/`, `handover/INTEGRATION_NOTE.md` |
| 5 | Mock adapter + MockApp + scenarios | `voice-agent` mock adapter + `mock_app/` |
| 6 | Behavior/prompt + sample dialogue | **pack** `handover/SAMPLE_DIALOGUE.md` (+ Habiba prompts in voice-agent) |
| 7 | Session / assist / transcript interfaces | `orchestration/` API; harness inspector; **pack** `SESSION_API.md` |
| 8 | Interruption / latency evidence | `voice-agent/evidence/phase-9/` (live campaign waived ADR-0011) |
| 9 | Acceptance T01–T20 | `voice-agent/evidence/phase-10/acceptance.md` (live waived ADR-0012) |
| 10 | Integration handover note | **pack** `handover/*` (this kit) |

## Orchestration glue (Habiba — joint phase)

| Piece | Path |
|---|---|
| Session / token + assist gate | `orchestration/src/foodease_session/` |
| Demo bring-up | `orchestration/tools/demo_up.py` |
| Topology helper | `orchestration/tools/topology_up.py` |
| IR-01…IR-05 auto suite | `voice-agent` `tools/run_integration.py` |
| Ownership | **pack** `handover/OWNERSHIP.md` |

## Your remaining deliverables (website)

| Piece | Pack guide |
|---|---|
| Accessible FoodEase UI | Your W-tasks / requirements spec |
| App-seat LiveKit client | `FRONTEND_QUICKSTART.md` |
| Same 13 ops + catalog IDs | `contract/v1/`, `catalog-seed.json` |
| Live IR-01…IR-05 | `JOINT_ACCEPTANCE.md` |
| Object or accept defaults | `OPEN_DECISIONS.md` |
