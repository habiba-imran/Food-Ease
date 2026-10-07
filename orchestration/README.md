# FoodEase orchestration (sibling glue package)

**Habiba-owned.** Session/token minting, consent/dispatch gate, demo bring-up.  
Not the voice brain (`voice-agent/`). Not the shopping UI (future `website/`).

See [`docs/OWNERSHIP.md`](docs/OWNERSHIP.md).

## What’s in this package

| Piece | Path |
|---|---|
| Session / token API | `src/foodease_session/` → `foodease-session` |
| Env example | `.env.example` |
| Bring up demo stack | `tools/demo_up.py` |
| 3-seat topology helper | `tools/topology_up.py` |
| Joint checklist pointer | `docs/INTEGRATION_CHECKLIST.md` |

## Quick start

```bash
cd orchestration
uv sync
cp .env.example .env
# Fill LIVEKIT_URL / LIVEKIT_API_KEY / LIVEKIT_API_SECRET
# (or rely on ../voice-agent/.env as fallback)

uv run python tools/demo_up.py          # print full stack commands
uv run foodease-session                 # http://127.0.0.1:8090  ·  /docs
uv run python tools/demo_up.py --check  # healthz + mint probe
```

```bash
uv run pytest -q
uv run python tools/smoke_session.py
uv run python tools/smoke_assist.py     # needs LiveKit if dispatch=true
uv run python tools/topology_up.py
uv run python tools/secret_scan.py

# Integration scenarios (MockApp; joint when Zainab plugs in):
#   cd ../voice-agent && uv run python tools/run_integration.py
```

## API summary

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/healthz` | Liveness |
| `POST` | `/v1/session` | Token mint only (no agent dispatch) |
| `POST` | `/v1/token` | Mint one role |
| `POST` | `/v1/assist/start` | Consent + mic JWT + **CreateAgentDispatch** |
| `POST` | `/v1/assist/end` | Delete dispatch; **cart preserved** |

Docs: [`docs/API.md`](docs/API.md) · [`docs/ASSIST_LIFECYCLE.md`](docs/ASSIST_LIFECYCLE.md) · [`docs/BRINGUP.md`](docs/BRINGUP.md) · [`docs/TOPOLOGY.md`](docs/TOPOLOGY.md)

### Start assistance (Zainab / harness)

```javascript
const s = await fetch("http://127.0.0.1:8090/v1/assist/start", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ consent: true, include_app_token: true }),
}).then((r) => r.json());
await room.connect(s.livekit_url, s.user.token);
// later: POST /v1/assist/end { room, dispatch_id, session_id }
```

## Hardening checklist

- [x] Sibling package (glue out of agent + website)
- [x] `/healthz` without secrets
- [x] Consent matrix for tokens + assist start
- [x] App JWT `foodease.role=app`
- [x] Short TTL + CORS + rate limit
- [x] Assist start/end with cart_preserved
- [x] `demo_up.py` + `.env.example` + OWNERSHIP
- [x] Topology + integration checklist links

## Known limits

- Localhost demo auth (no end-user login)
- `FOODEASE_AGENT_NAME` must match LiveKit Agents worker (`foodease`)
- Set `LIVEKIT_AGENT_DISPATCH=false` to mint-only (no Cloud dispatch)
- Agent dispatch requires worker running; MockApp cart is independent
- Full 3-seat check needs Cloud + `FOODEASE_APP_TRANSPORT=livekit` + MockApp `--livekit`
