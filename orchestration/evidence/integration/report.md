# Integration suite report

Generated: 2026-10-07T15:57:55.133532+00:00

Driver: in-process MockAdapter (Zainab live adapter = later).

| ID | Scenario | Result | Detail |
|---|---|---|---|
| IR-01 | Stale context_revision rejects mutation | **PASS** | `status=stale_context lines=0` |
| IR-02 | Duplicate action_id is idempotent | **PASS** | `qty=1 same_payload=True` |
| IR-03 | Checkout requires explicit confirmation | **PASS** | `route_after_hmm=checkout assistant='Demo order placed. No real payment was taken.'` |
| IR-04 | Mic denied then manual/typed continue | **PASS** | `blocked_state=muted/paused continue_ok=True` |
| IR-05 | Cart change invalidates checkout confirmation | **PASS** | `awaiting=True invalidated=True state=none route=checkout not_auto_submit=True` |

**All scenarios passed.**

Checklist template: `orchestration/docs/INTEGRATION_CHECKLIST.md`
