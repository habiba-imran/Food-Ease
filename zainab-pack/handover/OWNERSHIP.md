# Ownership (pack copy)

Canonical: `../orchestration/docs/OWNERSHIP.md`.

| Folder | Owner | Owns | Must not own |
|---|---|---|---|
| `orchestration/` | Habiba | JWT mint, assist dispatch, demo bring-up | Cart, menu, website UI |
| `voice-agent/` | Habiba | Voice worker, contract, MockApp stand-in | Browser LiveKit secrets, product screens |
| `zainab-pack/` | Habiba → you | Frozen contract + handover | Runtime services |
| your `website/` | You | UI, app-seat client, shopping state | `LIVEKIT_API_KEY` / secret, agent dispatch keys |

```text
Your browser     →  POST orchestration /v1/assist/* or /v1/session (no API secrets)
orchestration/   →  mints JWTs + optional CreateAgentDispatch
voice-agent      →  agent seat; talks to you via foodease.* contract
your website     →  app seat; owns cart / menu / checkout truth
```

**Cart invariant:** End assistance never clears the cart.
