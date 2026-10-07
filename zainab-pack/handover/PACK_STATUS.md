# Pack status — frozen for joint phase

**Status:** Habiba-side pack + orchestration glue **ready**.  
**Date stamp:** 2026-10-07  
**Contract:** `contract/v1` (v1.0)

## Habiba has already shipped (siblings)

| Piece | Where | Pack pointer |
|---|---|---|
| Voice agent + MockApp | `voice-agent/` | This pack’s contract + golden traces |
| Session / token + assist gate | `orchestration/` | `SESSION_API.md` |
| Ownership boundaries | `orchestration/docs/OWNERSHIP.md` | `OWNERSHIP.md` (pack copy) |
| Demo stack bring-up | `orchestration/tools/demo_up.py` | `FRONTEND_QUICKSTART.md` §7 |
| 3-seat topology | `orchestration/docs/TOPOLOGY.md` | `SESSION_API.md` |
| IR-01…IR-05 (MockApp auto) | `voice-agent` integration runner | `JOINT_ACCEPTANCE.md` |

## What this pack is for

You build the **website + app seat** against frozen ops/schemas here.  
You do **not** rebuild JWT mint, agent dispatch, or the conversation brain.

## What you still own

1. Accessible UI (browse, cart, checkout, assistance panel)  
2. Domain ops implementing the **same 13 operations** + `catalog-seed.json` IDs  
3. LiveKit **app** participant (`foodease.role=app`) registering RPCs/topics  
4. Mic **user** seat after Start assistance (call Habiba’s `/v1/assist/*`)  
5. Live column on IR-01…IR-05 once your adapter is wired (`JOINT_ACCEPTANCE.md`)

## Ready-to-plug sequence

1. Implement ops + context revision rules (mock-agent injector OK first).  
2. Join room as **app**; Habiba worker + session API unchanged.  
3. Habiba runs adapter conformance (task 11.8 / L15).  
4. Drop MockApp; tick Live column on joint checklist.

## Objections

Reply on `OPEN_DECISIONS.md` (L1–L20). Default applies until then.
