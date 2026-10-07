# Frontend quickstart (1–2 pages)

Goal: join the LiveKit room, register the same RPCs MockApp registers, push context, consume agent state/transcripts. Full schemas live in `contract/v1/`.

## 1. Join the room (Start assistance)

Mint tokens **and** dispatch the agent via Habiba’s session API. See `zainab-pack/handover/SESSION_API.md`.

```javascript
const s = await fetch("http://127.0.0.1:8090/v1/assist/start", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ consent: true, include_app_token: true }),
}).then((r) => r.json());

const room = new Room();
await room.connect(s.livekit_url, s.user.token);

await fetch("http://127.0.0.1:8090/v1/assist/end", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    room: s.room,
    dispatch_id: s.dispatch_id,
    session_id: s.session_id,
  }),
});
```

## 2. Register RPC: `foodease.action`

Handle agent cart/menu ops; return `ActionResultPayload` JSON.

```javascript
// Pseudocode — LiveKit JS registerRpcMethod (confirm API for your livekit-client version)
room.localParticipant.registerRpcMethod("foodease.action", async (data) => {
  const request = JSON.parse(data.payload); // ActionRequestPayload
  const result = await yourBackend.execute(request); // must bump revision + cart truth
  // Optionally publish updated ContextSnapshot on foodease.context
  await room.localParticipant.publishData(
    new TextEncoder().encode(JSON.stringify(snapshot)),
    { reliable: true, topic: "foodease.context" },
  );
  return JSON.stringify(result);
});
```

Python MockApp equivalent: `mock_app/participant.py` → `_handle_action`.

## 3. Push context on every GUI change

Whenever the user taps a category or edits the cart **without** voice:

```javascript
await room.localParticipant.publishData(
  new TextEncoder().encode(JSON.stringify(contextSnapshot)),
  { reliable: true, topic: "foodease.context" },
);
```

`revision` must increase. Include `route`, `visible_items` (bounded), `cart`, `checkout_available`.

## 4. Consume agent status / transcripts

Harness listens on data messages (envelope `type`):

```javascript
room.on(RoomEvent.DataReceived, (payload) => {
  const data = JSON.parse(new TextDecoder().decode(payload));
  if (data.type === "agent.status") {
    // data.payload.state → ready/listening | thinking | speaking | error | ...
  }
  if (data.type === "transcript.assistant") {
    // show caption; phase === "interrupted" for barge-in
  }
});
```

Prefer LiveKit native transcription/agent-state streams when available; mirror into these envelope types for UI parity (`transport_defaults.json`).

## 5. Typed input (optional)

```javascript
await room.localParticipant.publishData(
  new TextEncoder().encode(
    JSON.stringify({
      schema_version: "1.0",
      type: "app.text_input",
      payload: { text: "show burgers" },
    }),
  ),
  { reliable: true },
);
```

Or implement RPC `foodease.text_input` the way MockApp does.

## 6. Mute

Client mic mute (harness):

```javascript
await room.localParticipant.setMicrophoneEnabled(false);
```

Also publish `foodease.control` if the app owns session mute — see `OPEN_DECISIONS.md`.

## 7. Local demo stack

1. Fill `.env` from `.env.example`
2. `uv run foodease-worker`
3. `DEV_MODE=true` → `uv run python -m mock_app` (control UI on `127.0.0.1:8765`)
4. `uv run python harness/token_server.py` → open printed URL

Replace MockApp with your site by registering the same RPC/topics; leave the worker unchanged.
