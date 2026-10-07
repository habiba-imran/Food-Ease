# Ownership — joint phase

## Folders

| Folder | Owner | Owns | Must not own |
|---|---|---|---|
| `orchestration/` | Habiba | Tokens, consent/dispatch, demo bring-up, joint checklists / evidence | Cart, menu, voice brain, website UI |
| `voice-agent/` | Habiba | Voice worker, contract, MockApp stand-in, dialogue | Browser LiveKit secrets, product screens |
| `zainab-pack/` | Habiba → Zainab | Frozen contract + handover | Runtime services |
| `website/` *(later)* | Zainab | UI, app-seat LiveKit client, shopping state | JWT mint secrets, agent dispatch keys |

## Why `orchestration/` exists

Glue for **who joins which room, with which role, after consent**.  
Shopping stays on the app seat (MockApp today → Zainab’s site later). Voice stays in `voice-agent/`.

```text
Browser / website     →  calls orchestration API only (no API secrets)
orchestration/        →  mints JWTs + optional CreateAgentDispatch
voice-agent worker    →  joins room as agent, talks to app seat via contract
app seat (MockApp/UI) →  owns cart / menu / checkout
```

## Env

- **Canonical demo secrets for the session API:** `orchestration/.env` (from `.env.example`)
- Worker may share the same LiveKit project via `voice-agent/.env` (fallback documented in config)
- Never commit real `LIVEKIT_API_SECRET`

## Joint handoff

When Zainab’s site is ready:

1. She keeps calling `POST /v1/assist/start` / `end` (or `/v1/session`)
2. She takes the **app** seat (`foodease.role=app`) — same RPCs as MockApp
3. Integration checklist Live column: `docs/INTEGRATION_CHECKLIST.md`
