# Phase 2 evidence report

**Branch:** `phase-2-contract`  
**Date:** 2026-10-02  
**Scope:** Tasks 2.1–2.4 only. Stopped before 2.5. Skipped 2.6. No provider API calls.

## Deliverables

| Path | Purpose |
|---|---|
| `src/foodease_agent/contract/` | Pydantic models (source of truth) |
| `contract/v1/schemas/` | Exported JSON Schemas (30 files) |
| `contract/v1/examples/` | Golden envelopes |
| `contract/v1/STATE_MACHINES.md` | Conversation + action lifecycles |
| `contract/v1/DECISIONS.md` | Habiba wire defaults |
| `contract/v1/schemas/transport_defaults.json` | `x-habiba-default` transport mapping |

## Verification

| ID | Result |
|---|---|
| V2.1 | **Pass** — schema export + all golden examples validate (`Envelope`) |
| V2.2 | **Pass** — negatives: unknown op, missing `action_id`, qty 0/99999/-1, wrong types, bad `item_id` |
| V2.3 | **Pass** — drift check models ↔ `envelope.json` |
| V2.4 | **Pass** — checkout summary/submit examples **without** `confirmation_token` |
| 2.5 [HUMAN] | **Pending** — you read `contract/v1/` vs SPEC and tag `contract-v1.0-frozen` |
| 2.6 [LATER] | Skipped |

## Commands

```bash
uv run python -m foodease_agent.contract.export_schemas
uv run python -m foodease_agent.contract.write_examples
uv run pytest tests/test_contract_v1.py -q
```

Result: **28 passed**.

## Gate

Agent items V2.1–V2.4: **pass**.  
Full Phase 2 gate also needs your **2.5** tag `contract-v1.0-frozen`.

## Update

Human tagged **`contract-v1.0-frozen`** (2026-10-02). Phase 2 gate: **passed**.
