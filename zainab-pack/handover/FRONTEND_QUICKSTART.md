# Frontend quickstart (1–2 pages)

Goal: join the LiveKit room as the **app** seat, register the same RPCs MockApp registers, push context, consume agent state/transcripts. Full schemas live in `contract/v1/`.

Seats: see `OWNERSHIP.md` + `SESSION_API.md`. Shopping UI = **app**; mic after consent = **user**.

## 1. Mint tokens (no secrets in the browser)

### App seat (your website — always)

```javascript
const app = await fetch("http://127.0.0.1:8090/v1/token", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    role: "app",
    room: "foodease-demo",
    identity: "zainab-app",
  }),
}).then((r) => r.json());

const appRoom = new Room();
await appRoom.connect(app.livekit_url, app.participant.token);
// JWT already has foodease.role=app
```

### Start assistance (user / mic + agent dispatch)

Only after explicit opt-in (WEB-01). See `SESSION_API.md`.

```javascript
const s = await fetch("http://127.0.0.1:8090/v1/assist/start", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    consent: true,
    room: "foodease-demo",
    include_app_token: false, // app already joined above
  }),
}).then((r) => r.json());

const userRoom = new Room(); // or second connection pattern your stack prefers
await userRoom.connect(s.livekit_url, s.user.token);
await userRoom.localParticipant.setMicrophoneEnabled(true);

// End assistance (keeps cart):
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

Demo topology today: MockApp = app, harness = user. You replace MockApp.  
Details: `../orchestration/docs/TOPOLOGY.md`.

## 2. Register RPC: `foodease.action`

Handle agent cart/menu ops; return `ActionResultPayload` JSON.

```javascript
// Pseudocode — LiveKit JS registerRpcMethod (confirm API for your livekit-client version)
appRoom.localParticipant.registerRpcMethod("foodease.action", async (data) => {
  const request = JSON.parse(data.payload); // ActionRequestPayload
  const result = await yourBackend.execute(request); // must bump revision + cart truth
  await appRoom.localParticipant.publishData(
    new TextEncoder().encode(JSON.stringify(snapshot)),
    { reliable: true, topic: "foodease.context" },
  );
  return JSON.stringify(result);
});
```

Python MockApp equivalent: `voice-agent/mock_app/participant.py` → `_handle_action`.

## 3. Push context on every GUI change

Whenever the user taps a category or edits the cart **without** voice:

```javascript
await appRoom.localParticipant.publishData(
  new TextEncoder().encode(JSON.stringify(contextSnapshot)),
  { reliable: true, topic: "foodease.context" },
);
```

`revision` must increase. Include `route`, `visible_items` (bounded), `cart`, `checkout_available`.

## 4. Consume agent status / transcripts

```javascript
userRoom.on(RoomEvent.DataReceived, (payload) => {
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
await appRoom.localParticipant.publishData(
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

```javascript
await userRoom.localParticipant.setMicrophoneEnabled(false);
```

Also publish `foodease.control` if the app owns session mute — see `OPEN_DECISIONS.md` L9.

## 7. Local demo stack (Habiba siblings)

```bash
cd orchestration
uv run python tools/demo_up.py
# Then terminals printed: foodease-session → foodease-worker → MockApp → harness
```

Replace MockApp with your site (app seat); leave worker + session API unchanged.  
Joint IR gate: `JOINT_ACCEPTANCE.md`.
