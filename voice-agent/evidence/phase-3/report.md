# Phase 3 evidence report

**Branch:** `phase-3-adapters-mock`  
**Date:** 2026-10-02  
**Scope:** Tasks 3.1–3.4. No provider API calls.

## Deliverables

| Path | Purpose |
|---|---|
| `src/foodease_agent/adapters/base.py` | Async `AppAdapter` protocol |
| `src/foodease_agent/adapters/mock.py` | In-process `MockAdapter` + scenario controller |
| `src/foodease_agent/adapters/mock_catalog.py` | 28 fictional PKR items + traps |
| `tests/adapter_conformance/` | Idempotency, revision, stale, correlation, timeout |
| `tests/test_mock_cart.py` | Totals / qty / fees (V3.1) |
| `tests/test_mock_scenarios.py` | Scenario modes + GUI sims (V3.2/V3.3) |
| `tests/test_no_mock_leak.py` | V3.5 import boundary |

## Traps included

Two Zinger names · two wraps · prices 150 vs 1500 · out-of-stock burger · dessert with no ingredients · fries description with injection string.

## Verification

| ID | Result |
|---|---|
| V3.1 | Pass |
| V3.2 | Pass |
| V3.3 | Pass |
| V3.4 | Pass (conformance on MockAdapter) |
| V3.5 | Pass (no `mock` imports outside `adapters/`) |

## Commands

```bash
uv run pytest -q
uv run ruff check src/foodease_agent/adapters tests/test_mock_cart.py tests/test_mock_scenarios.py tests/adapter_conformance tests/test_no_mock_leak.py
```

**67 passed** (full suite including prior phases).

## Gate

V3.1–V3.5: **pass**. Phase 3 complete. No [HUMAN] items.
