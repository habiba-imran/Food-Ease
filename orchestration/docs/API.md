# Session API (v1.1)

Base URL (local): `http://127.0.0.1:8090`  
OpenAPI: `/docs`  
Lifecycle: [`ASSIST_LIFECYCLE.md`](ASSIST_LIFECYCLE.md)

Secrets (`LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET`) never appear in responses.

---

## `GET /healthz`

```json
{ "status": "ok", "service": "foodease-session" }
```

---

## `POST /v1/session`

Creates a correlated session for one LiveKit room.

### Request

```json
{
  "consent": true,
  "room": null,
  "user_identity": null,
  "app_identity": null,
  "include_app_token": true
}
```

| Field | Meaning |
|---|---|
| `consent` | If `true`, include a mic-capable **user** token (`voice_allowed: true`). If `false`, omit `user` |
| `room` | `null` → server generates `foodease-<id>`; else must match `foodease-*` |
| `include_app_token` | If `true`, include **app** token with attribute `foodease.role=app` |

### Response (200)

```json
{
  "schema_version": "1.0",
  "session_id": "sess_ab12...",
  "room": "foodease-...",
  "livekit_url": "wss://...",
  "expires_at": "2026-10-07T14:30:00+00:00",
  "ttl_seconds": 900,
  "voice_allowed": true,
  "user": { "identity": "user-...", "token": "<jwt>", "role": "user" },
  "app": { "identity": "app-...", "token": "<jwt>", "role": "app" }
}
```

### Consent matrix

| consent | include_app_token | user token | app token | voice_allowed |
|---|---|---|---|---|
| true | true | yes | yes | true |
| true | false | yes | no | true |
| false | true | **no** | yes | false |
| false | false | **no** | no | false |

---

## `POST /v1/token`

Mint a single participant token (MockApp / refresh).

### Request

```json
{
  "role": "app",
  "room": "foodease-demo",
  "identity": "mock-app",
  "consent": false
}
```

- `role=app` — allowed without consent (website stand-in)
- `role=user` — requires `consent: true` (403 otherwise)

### Response (200)

```json
{
  "schema_version": "1.0",
  "room": "foodease-demo",
  "livekit_url": "wss://...",
  "expires_at": "...",
  "ttl_seconds": 900,
  "participant": { "identity": "mock-app", "token": "<jwt>", "role": "app" }
}
```

---

## `POST /v1/assist/start`

Consent-gated **Start assistance**: mint mic user JWT + optional LiveKit AgentDispatch.

### Request

```json
{
  "consent": true,
  "room": "foodease-demo",
  "user_identity": "harness-user",
  "include_app_token": false
}
```

`consent` must be `true` (403 otherwise).

### Response (200)

```json
{
  "schema_version": "1.0",
  "session_id": "sess_...",
  "room": "foodease-demo",
  "livekit_url": "wss://...",
  "expires_at": "...",
  "ttl_seconds": 900,
  "voice_allowed": true,
  "dispatch_id": "AD_...",
  "dispatch_enabled": true,
  "user": { "identity": "harness-user", "token": "<jwt>", "role": "user" },
  "app": null
}
```

When `LIVEKIT_AGENT_DISPATCH=false`, `dispatch_id` is `null` and tokens are still minted.

---

## `POST /v1/assist/end`

Stops the agent job. **Always** returns `cart_preserved: true` (cart lives in the app).

### Request

```json
{
  "room": "foodease-demo",
  "dispatch_id": "AD_...",
  "session_id": "sess_..."
}
```

### Response (200)

```json
{
  "schema_version": "1.0",
  "room": "foodease-demo",
  "ended": true,
  "cart_preserved": true,
  "dispatch_id": "AD_...",
  "dispatch_deleted": true
}
```

---

## Errors

| HTTP | When |
|---|---|
| 400 | Bad room/identity/role (`PolicyError` / `MintError`) |
| 403 | User mint / assist start without consent |
| 429 | Rate limited |
| 500 | Missing LiveKit env on server |
| 502 | LiveKit Create/DeleteAgentDispatch failed |
