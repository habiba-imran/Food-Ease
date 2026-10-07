# Integration runner / checklist — plan

## Goal

Automated (MockApp-driven) scenarios that prove joint contract behavior before Zainab’s UI:

| ID | Scenario | Pass condition |
|---|---|---|
| IR-01 | Stale `context_revision` | `stale_context`; no cart mutation |
| IR-02 | Duplicate `action_id` | Same result; no second mutation |
| IR-03 | Checkout confirm | No submit without yes; one demo order on yes |
| IR-04 | Mic denied → manual continue | Voice blocked state; typed/manual path still works |
| IR-05 | Cart change invalidates confirm | Prior yes does not submit after cart edit |

**Default driver:** in-process `MockAdapter` (always CI-safe).  
**Later:** same IDs against Zainab’s adapter / live MockApp (`--livekit`).

## Phases (this delivery)

| Phase | Deliverable |
|---|---|
| 0 | This plan + `INTEGRATION_CHECKLIST.md` |
| 1 | Scenario module + `tools/run_integration.py` |
| 2 | Evidence JSON/MD + pytest hook |
| 3 | Docs in zainab-pack / topology cross-link |

## Commands

```bash
cd voice-agent
uv run python tools/run_integration.py
uv run pytest tests/test_integration_runner.py -q
```
