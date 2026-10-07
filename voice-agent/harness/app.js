/**
 * FoodEase inspector harness — consent-gated Start / End assistance.
 * Tokens + dispatch via orchestration (:8090). Cart lives in MockApp (:8765).
 */
import {
  Room,
  RoomEvent,
  Track,
  createLocalTracks,
} from "https://cdn.jsdelivr.net/npm/livekit-client@2.15.4/+esm";

const SESSION_API = "http://127.0.0.1:8090";
const ROOM_NAME = "foodease-demo";

const stateEl = document.getElementById("state");
const captionsEl = document.getElementById("captions");
const eventsEl = document.getElementById("events");
const startBtn = document.getElementById("start");
const endBtn = document.getElementById("endAssist");
const muteBtn = document.getElementById("mute");
const leaveBtn = document.getElementById("leave");
const typedInput = document.getElementById("typed");
const sendBtn = document.getElementById("send");
const navBtn = document.getElementById("navBtn");
const navPage = document.getElementById("navPage");
const faultDrop = document.getElementById("faultDrop");

let room = null;
let micPublication = null;
let muted = false;
let dropOn = false;
let assistSession = null; // { session_id, dispatch_id, room, ... }

function setState(s) {
  stateEl.textContent = s;
}

function appendCaption(line, { interrupted = false } = {}) {
  const span = document.createElement("div");
  if (interrupted) span.className = "interrupted";
  span.textContent = line;
  captionsEl.appendChild(span);
  captionsEl.scrollTop = captionsEl.scrollHeight;
}

function logEvent(obj) {
  eventsEl.textContent += JSON.stringify(obj) + "\n";
  eventsEl.scrollTop = eventsEl.scrollHeight;
}

function setAssistUi(active) {
  startBtn.disabled = active;
  if (endBtn) endBtn.disabled = !active;
  muteBtn.disabled = !active;
  leaveBtn.disabled = !active;
  typedInput.disabled = !active;
  sendBtn.disabled = !active;
}

async function endAssistance({ disconnectRoom = true } = {}) {
  if (assistSession) {
    try {
      const res = await fetch(`${SESSION_API}/v1/assist/end`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          room: assistSession.room || ROOM_NAME,
          dispatch_id: assistSession.dispatch_id || null,
          session_id: assistSession.session_id || null,
        }),
      });
      const body = await res.json().catch(() => ({}));
      logEvent({
        assist_end: true,
        ok: res.ok,
        cart_preserved: body.cart_preserved,
        dispatch_deleted: body.dispatch_deleted,
      });
    } catch (e) {
      logEvent({ assist_end_error: String(e) });
    }
    assistSession = null;
  }
  if (disconnectRoom && room) {
    await room.disconnect();
    room = null;
  }
  muted = false;
  muteBtn.textContent = "Mute mic";
  setAssistUi(false);
  setState("off/awaiting_consent");
  appendCaption("[assistance ended — cart preserved in app]");
}

startBtn.addEventListener("click", async () => {
  setState("connecting");
  startBtn.disabled = true;
  let session;
  try {
    const res = await fetch(`${SESSION_API}/v1/assist/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        consent: true,
        room: ROOM_NAME,
        user_identity: "harness-user",
        include_app_token: false,
      }),
    });
    if (!res.ok) {
      throw new Error(`assist/start HTTP ${res.status}`);
    }
    session = await res.json();
  } catch (e) {
    setState("error");
    appendCaption(`[assist start error] Is foodease-session on :8090? ${e}`);
    startBtn.disabled = false;
    return;
  }
  if (!session.user?.token || !session.livekit_url) {
    setState("error");
    appendCaption("[assist start error] voice token missing");
    startBtn.disabled = false;
    return;
  }
  assistSession = {
    session_id: session.session_id,
    dispatch_id: session.dispatch_id,
    room: session.room,
  };
  logEvent({
    assist_start: true,
    session_id: session.session_id,
    room: session.room,
    dispatch_id: session.dispatch_id,
    dispatch_enabled: session.dispatch_enabled,
  });

  room = new Room();
  room.on(RoomEvent.DataReceived, (payload) => {
    try {
      const msg = new TextDecoder().decode(payload);
      const data = JSON.parse(msg);
      logEvent({ type: data.type || "data", keys: Object.keys(data) });
      if (data.type === "agent.status" && data.payload?.state) {
        setState(data.payload.state);
      }
      if (data.type === "transcript.user.partial") {
        appendCaption(`You (…): ${data.payload?.text || ""}`);
      }
      if (data.type === "transcript.user.final") {
        appendCaption(`You: ${data.payload?.text || ""}`);
      }
      if (data.type === "transcript.assistant") {
        const phase = data.payload?.phase || "";
        const interrupted = phase === "interrupted";
        appendCaption(`Agent: ${data.payload?.text || ""}`, { interrupted });
      }
    } catch {
      logEvent({ raw: "non-json data" });
    }
  });
  room.on(RoomEvent.TrackSubscribed, (track) => {
    if (track.kind === Track.Kind.Audio) {
      document.body.appendChild(track.attach());
    }
  });
  await room.connect(session.livekit_url, session.user.token);
  const tracks = await createLocalTracks({ audio: true, video: false });
  for (const t of tracks) {
    micPublication = await room.localParticipant.publishTrack(t);
  }
  setState("ready/listening");
  setAssistUi(true);
  appendCaption("[assistance started]");
});

if (endBtn) {
  endBtn.addEventListener("click", async () => {
    await endAssistance({ disconnectRoom: true });
  });
}

muteBtn.addEventListener("click", async () => {
  if (!room) return;
  muted = !muted;
  await room.localParticipant.setMicrophoneEnabled(!muted);
  muteBtn.textContent = muted ? "Unmute mic" : "Mute mic";
  setState(muted ? "muted/paused" : "ready/listening");
});

leaveBtn.addEventListener("click", async () => {
  await endAssistance({ disconnectRoom: true });
});

sendBtn.addEventListener("click", async () => {
  const text = typedInput.value.trim();
  if (!text || !room) return;
  const envelope = {
    schema_version: "1.0",
    type: "app.text_input",
    payload: { text },
  };
  await room.localParticipant.publishData(
    new TextEncoder().encode(JSON.stringify(envelope)),
    { reliable: true },
  );
  appendCaption(`You (typed): ${text}`);
  typedInput.value = "";
});

navBtn.addEventListener("click", async () => {
  try {
    const r = await fetch("http://127.0.0.1:8765/navigate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ page: navPage.value }),
    });
    logEvent({ mock_navigate: navPage.value, ok: r.ok });
  } catch (e) {
    logEvent({ mock_navigate_error: String(e) });
  }
});

faultDrop.addEventListener("click", async () => {
  dropOn = !dropOn;
  try {
    const r = await fetch("http://127.0.0.1:8765/faults", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ drop_connection: dropOn }),
    });
    logEvent({ drop_connection: dropOn, ok: r.ok });
  } catch (e) {
    logEvent({ fault_error: String(e) });
  }
});

setState("off/awaiting_consent");
setAssistUi(false);
