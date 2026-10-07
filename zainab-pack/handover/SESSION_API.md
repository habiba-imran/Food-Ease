# Session / assist API (Habiba orchestration)

Habiba owns session glue: short-lived LiveKit JWTs **and** consent-gated agent dispatch.  
Never embed LiveKit API keys in the frontend.

Local default: `http://127.0.0.1:8090` · OpenAPI `/docs`

## Where it lives

| Path | Purpose |
|---|---|
| `../orchestration/` | Sibling glue package — not your website tree |
| `OWNERSHIP.md` | Who owns tokens vs cart vs voice |
| `../orchestration/docs/API.md` | Full request/response shapes |
| `../orchestration/docs/ASSIST_LIFECYCLE.md` | Start / End assistance rules |
| `../orchestration/tools/demo_up.py` | Print demo stack commands |

## Which token for which seat

| Seat | Call | Use |
|---|---|---|
| **app** (your UI) | `POST /v1/token` `{ "role": "app", "room": "…" }` | Connect; register `foodease.action`; publish context |
| **user** (mic) | `POST /v1/assist/start` `{ "consent": true, … }` | Mic JWT + agent dispatch after opt-in |
| both at once (optional) | `assist/start` with `include_app_token: true` | Returns `user` + `app` JWTs |

`POST /v1/session` mints tokens **without** dispatch — useful for app-only wiring before Start assistance.

## Start assistance (opt-in)

```javascript
const s = await fetch("http://127.0.0.1:8090/v1/assist/start", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    consent: true, // only after explicit assistance opt-in (WEB-01)
    room: "foodease-demo",
    include_app_token: true,
  }),
}).then((r) => r.json());

// user = mic; app = foodease.role=app (if include_app_token)
await userRoom.connect(s.livekit_url, s.user.token);
// Keep s.session_id + s.dispatch_id for End
```

## End assistance (keep cart)

```javascript
await fetch("http://127.0.0.1:8090/v1/assist/end", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    room: s.room,
    dispatch_id: s.dispatch_id,
    session_id: s.session_id,
  }),
});
// Response always cart_preserved: true — do not clear the shopping cart
```

## Room topology

Three seats in one LiveKit room: **user** + **app** + **agent**.  
You take the **app** seat (same RPCs/topics as MockApp). See `../orchestration/docs/TOPOLOGY.md`.

```bash
cd orchestration
uv run python tools/demo_up.py
uv run python tools/topology_up.py
```

## Joint scenarios

MockApp auto today; your Live column later — `JOINT_ACCEPTANCE.md`.

```bash
cd voice-agent
uv run python tools/run_integration.py
```

## Open decisions

L18 (session mint), L19 (topology), L20 (IR suite) in `OPEN_DECISIONS.md`.
