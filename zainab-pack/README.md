# Zainab pack (Habiba → Zainab) — frozen

Self-contained integration kit so you can build the FoodEase website **without spelunking** Habiba’s agent tree.

**Pack status:** ready for joint phase — see [`handover/PACK_STATUS.md`](handover/PACK_STATUS.md).  
Habiba’s voice agent + **orchestration glue** (tokens, assist dispatch, topology, IR auto suite) are already built. Your job is the accessible website + the **app seat** on the same contract.

## What’s inside

| Path | Purpose |
|---|---|
| `README.md` | This file — start here |
| `catalog-seed.json` | **Authoritative demo menu** (28 items): stable `item_id`, PKR prices, tags |
| `handover/PACK_STATUS.md` | Freeze stamp: Habiba done vs your remaining work |
| `handover/OWNERSHIP.md` | Tokens/dispatch vs cart vs voice brain |
| `handover/INTEGRATION_NOTE.md` | Entry/exit, RPC/topics, revision rules |
| `handover/FRONTEND_QUICKSTART.md` | Join room, register RPCs, push context |
| `handover/SESSION_API.md` | LiveKit JWTs + Start/End assistance |
| `handover/JOINT_ACCEPTANCE.md` | IR-01…IR-05 Live column (your gate) |
| `handover/OPEN_DECISIONS.md` | Defaults we **keep unless you object** (L1–L20) |
| `handover/SAMPLE_DIALOGUE.md` | Spoken happy-path reference |
| `handover/DELIVERABLES.md` | SPEC §11 map → pack + siblings |
| `contract/v1/` | Frozen schemas, examples, state machines, transport defaults |
| `golden-traces/` | Add → set-qty → checkout (wire + spoken) |

## Read order (≈ 1 sitting)

1. `handover/PACK_STATUS.md` — what Habiba already shipped  
2. `handover/OWNERSHIP.md` — who owns what  
3. `handover/INTEGRATION_NOTE.md` — entry/exit, RPC/topics, revision rules  
4. `handover/FRONTEND_QUICKSTART.md` — join as **app**, push context  
5. `handover/SESSION_API.md` — mint + assist start/end (no secrets in browser)  
6. `handover/JOINT_ACCEPTANCE.md` — IR-01…IR-05 you must pass live  
7. `handover/OPEN_DECISIONS.md` — object here or defaults stand  
8. `catalog-seed.json` — lock these `item_id`s (or jointly replace before hard-coding)  
9. `contract/v1/STATE_MACHINES.md` + `schemas/` — envelopes and 13 ops  
10. `golden-traces/INDEX.md` — acceptance-shaped examples for your mock-agent harness  

Sibling deep-dives (optional): `../orchestration/docs/` (`API`, `TOPOLOGY`, `BRINGUP`, `demo_up.py`).

## Hard rules

1. **One catalog.** Reuse `catalog-seed.json` IDs/prices, or jointly freeze a replacement *before* either side hard-codes a second menu.  
2. **Same 13 operations** (exact spellings) — see `contract/v1`.  
3. **App owns truth.** Manual UI and agent requests call the **same** domain ops; agent never invents cart success.  
4. **Bump `revision`** and publish `foodease.context` on every meaningful GUI/cart change.  
5. **No secrets** in the frontend. Tokens from Habiba’s `orchestration/` only.  
6. **End assistance keeps cart.** Never clear cart on assist end.

## Two seats your site must understand

| Seat | Token | Job |
|---|---|---|
| **app** | `POST /v1/token` `role=app` (or `include_app_token`) | Shopping UI; register `foodease.action`; publish context |
| **user** | `POST /v1/assist/start` after consent | Mic / voice; Start assistance only |

Demo today: MockApp = app, harness = user. You replace **app** (and later own user mic UX).

## What you do *not* need from this pack

- Habiba’s STT/TTS/LLM/prompts  
- Reimplementing JWT mint or CreateAgentDispatch  
- Copying `voice-agent/harness/` as product UI (debug inspector only)  
- Day-one LiveKit — prove ops with a **mock agent injector** first (your W09–W22)

## When you’re ready to plug in

1. Join with `foodease.role=app` and register the RPCs MockApp registers.  
2. Call `/v1/assist/start` / `end` for mic + agent (WEB-01).  
3. Habiba runs adapter conformance (task 11.8 / L15).  
4. Tick Live column on `JOINT_ACCEPTANCE.md` / `INTEGRATION_CHECKLIST.md`.  
5. Drop MockApp; leave her conversation brain unchanged.

Questions / objections → `handover/OPEN_DECISIONS.md` (L1–L20).
