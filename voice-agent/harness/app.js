/**
 * FoodEase inspector harness (Phase 7.7) — extends Phase 5 talk client.
 */
import {
  Room,
  RoomEvent,
  Track,
  createLocalTracks,
} from "https://cdn.jsdelivr.net/npm/livekit-client@2.15.4/+esm";

const stateEl = document.getElementById("state");
const captionsEl = document.getElementById("captions");
const eventsEl = document.getElementById("events");
const startBtn = document.getElementById("start");
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
const finals = new Map(); // turn_id -> line index for replace semantics

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

startBtn.addEventListener("click", async () => {
  setState("connecting");
  startBtn.disabled = true;
  const res = await fetch("/token?identity=harness-user&room=foodease-demo");
  if (!res.ok) {
    setState("error");
    appendCaption("[token error]");
    startBtn.disabled = false;
    return;
  }
  const { url, token } = await res.json();
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
        // Replace: clear last partial-looking line is soft; append final once
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
  await room.connect(url, token);
  const tracks = await createLocalTracks({ audio: true, video: false });
  for (const t of tracks) {
    micPublication = await room.localParticipant.publishTrack(t);
  }
  setState("ready/listening");
  muteBtn.disabled = false;
  leaveBtn.disabled = false;
  typedInput.disabled = false;
  sendBtn.disabled = false;
  appendCaption("[joined]");
});

muteBtn.addEventListener("click", async () => {
  if (!room) return;
  muted = !muted;
  await room.localParticipant.setMicrophoneEnabled(!muted);
  muteBtn.textContent = muted ? "Unmute mic" : "Mute mic";
  setState(muted ? "muted/paused" : "ready/listening");
});

leaveBtn.addEventListener("click", async () => {
  if (room) {
    await room.disconnect();
    room = null;
  }
  setState("ended");
  startBtn.disabled = false;
  muteBtn.disabled = true;
  leaveBtn.disabled = true;
  typedInput.disabled = true;
  sendBtn.disabled = true;
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
