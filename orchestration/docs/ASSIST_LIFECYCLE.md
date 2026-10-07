# Assistance lifecycle (consent / dispatch gate)

Matches WEB-01 / VA-01: no mic, no greeting, no idle tips until **Start assistance**.

## Product states (UI-facing)

| State | Meaning |
|---|---|
| `off/awaiting_consent` | Manual browse only; no agent job |
| `connecting` | Start assist in flight (token + dispatch) |
| `ready/listening` … | Normal assist (Habiba agent owns these) |
| `ended` / back to `off/awaiting_consent` | Assist ended; **cart unchanged** |

## API (frozen)

### `POST /v1/assist/start`

Requires `consent: true`. Mints mic **user** JWT (and optional **app**), creates LiveKit **AgentDispatch**.

```json
{
  "consent": true,
  "room": "foodease-demo",
  "user_identity": "harness-user",
  "include_app_token": false
}
```

Response includes `session_id`, tokens, `dispatch_id` (null if dispatch disabled), `voice_allowed: true`.

### `POST /v1/assist/end`

Stops the agent job. **Never clears cart.**

```json
{
  "room": "foodease-demo",
  "dispatch_id": "AD_...",
  "session_id": "sess_..."
}
```

Response: `{ "cart_preserved": true, "ended": true, ... }`.

### `POST /v1/session` (unchanged)

Token mint only — **no** agent dispatch. Use for app-only / manual paths.

## Cart invariant

Cart/order state lives in the **app** (MockApp / Zainab). End assistance must not call cart-clear or submit-order APIs.

## Env

| Var | Default | Meaning |
|---|---|---|
| `LIVEKIT_AGENT_DISPATCH` | `true` | When false, start mints tokens only (no CreateAgentDispatch) |
| `FOODEASE_AGENT_NAME` | `foodease` | Must match LiveKit Agents worker name |

## Harness mapping

| Button | Call |
|---|---|
| Start assistance | `POST /v1/assist/start` then connect + mic |
| End assistance | `POST /v1/assist/end` then disconnect agent/room; GUI nav still works |
| Leave | Disconnect room (same as end for demo) |
