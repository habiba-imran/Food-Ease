# Ownership — final website orchestration

## Folders

| Folder | Owner | Owns | Must not own |
|---|---|---|---|
| `orchestration/` | Habiba | Tokens, consent/dispatch, demo bring-up, joint checklists / evidence | Cart, menu, voice brain, website UI |
| `voice-agent/` | Habiba | Integrated voice worker, dialogue, action admission and speech delivery | Shopping authority, product screens |
| `zainab-pack/` | Habiba → Zainab | Frozen contract + handover | Runtime services |
| `website/` | Zainab | UI, browser app/user seats, owner-scoped shopping state and demo receipts | JWT mint secrets, agent dispatch keys |

## Why `orchestration/` exists

Glue for **who joins which room, with which role, after consent**.  
Shopping stays in the real website authority. Voice stays in `voice-agent/`.
The [final runbook](FINAL_RUNBOOK.md) is the current launch/acceptance source.
Earlier MockApp/harness checklists are standalone historical evidence.

```text
Browser / website     →  website authority + bound v2 session API (no API secrets)
orchestration/        →  mints JWTs + optional CreateAgentDispatch
voice-agent worker    →  joins room as agent, talks to app seat via contract
browser app seat     →  forwards tools to the website's shared manual/voice authority
```

## Env

- **Canonical demo secrets for the session API:** `orchestration/.env` (from `.env.example`)
- Worker may share the same LiveKit project via `voice-agent/.env` (fallback documented in config)
- Never commit real `LIVEKIT_API_SECRET`

## Joint handoff

1. The owner cookie and per-tab shopping session bind `/v2/assist/start`, ready,
   status and end. `/v1` stays disabled on the final path.
2. The browser joins separate app/user seats; server dispatch assigns the agent
   identity. All three carry the same session/generation with distinct roles.
3. `contracts/` owns shared **v2** validation and frozen schemas. Do not edit the
   historical v1 handoff copies. The thirteen semantic operations are unchanged.
4. [Lifecycle](PHASE_03_ASSISTANCE_LIFECYCLE.md),
   [browser](PHASE_05_BROWSER_INTEGRATION.md),
   [recovery](PHASE_08_RECOVERY.md) and [final runbook](FINAL_RUNBOOK.md) describe
   the active boundary. The website owns every committed cart/order result.
5. Human live listening, devices, accessibility and audible measurements are joint
   Habiba/Zainab acceptance. Empty/local-fake evidence cannot retire these gates.
