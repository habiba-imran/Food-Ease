# Integration checklist (Habiba ↔ Zainab)

Run: `cd voice-agent && uv run python tools/run_integration.py`  
Latest auto report: `orchestration/evidence/integration/report.md` (generated).

| ID | Scenario | Auto | Live/Zainab later |
|---|---|---|---|
| IR-01 | Stale revision on mutating action | [x] | [ ] |
| IR-02 | Duplicate `action_id` idempotent | [x] | [ ] |
| IR-03 | Checkout requires explicit confirm | [x] | [ ] |
| IR-04 | Mic denied → typed/manual continue | [x] | [ ] |
| IR-05 | Cart edit invalidates checkout confirm | [x] | [ ] |

Topology prerequisite (3 seats): see `TOPOLOGY.md`.  
Zainab-facing copy: `zainab-pack/handover/JOINT_ACCEPTANCE.md`.  
When Zainab’s adapter exists: re-run with her AppAdapter (task 11.8 / L15 / L20).
