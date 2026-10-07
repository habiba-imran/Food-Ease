# Joint acceptance (IR-01…IR-05)

Habiba’s auto column already passes against **MockApp**.  
Your Live column is the joint gate when your AppAdapter is ready.

Canonical checklist: `../orchestration/docs/INTEGRATION_CHECKLIST.md`  
Runner (today): `cd voice-agent && uv run python tools/run_integration.py`

| ID | Scenario | Pass criteria (app side) |
|---|---|---|
| IR-01 | Stale revision | Mutating op with old `context_revision` → `stale_context`; cart unchanged |
| IR-02 | Duplicate `action_id` | Second identical `action_id` returns same result; no double mutation |
| IR-03 | Checkout confirm | No demo order until explicit yes; one submit on confirm |
| IR-04 | Mic denied → manual | Voice blocked; typed / GUI path still works |
| IR-05 | Cart invalidates confirm | Cart edit while awaiting confirm clears confirm; old yes must not submit |

## Topology prerequisite

Three seats in one room before Live ticks:

| Seat | Who (demo → you) |
|---|---|
| user | Harness → your mic client after Start assistance |
| app | MockApp `--livekit` → **your website** (`foodease.role=app`) |
| agent | `foodease-worker` (unchanged) |

```bash
cd orchestration
uv run python tools/demo_up.py
uv run python tools/topology_up.py
```

## When to tick Live

1. Your site registers `foodease.action` / publishes `foodease.context`.  
2. Habiba points the worker at your app seat (drop MockApp).  
3. Re-run IR scenarios (or Habiba’s 11.8 conformance) against **your** ops.  
4. Mark Live column in `INTEGRATION_CHECKLIST.md`.
