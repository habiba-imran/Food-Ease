/**
 * Minimal LiveKit talk client (Phase 5.0).
 * Loads livekit-client from CDN — no build step.
 */
import {
  Room,
  RoomEvent,
  Track,
  createLocalTracks,
} from "https://cdn.jsdelivr.net/npm/livekit-client@2.15.4/+esm";

const stateEl = document.getElementById("state");
const captionsEl = document.getElementById("captions");
const startBtn = document.getElementById("start");
const muteBtn = document.getElementById("mute");
const leaveBtn = document.getElementById("leave");
const typedInput = document.getElementById("typed");
const sendBtn = document.getElementById("send");

let room = null;
let micPublication = null;
let muted = false;

function setState(s) {
  stateEl.textContent = s;
}

function appendCaption(line) {
  captionsEl.textContent += line + "\n";
  captionsEl.scrollTop = captionsEl.scrollHeight;
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
  room.on(RoomEvent.DataReceived, (payload, participant) => {
    try {
      const msg = new TextDecoder().decode(payload);
      const data = JSON.parse(msg);
      if (data.type === "agent.status" && data.payload?.state) {
        setState(data.payload.state);
      }
      if (data.type?.startsWith("transcript.")) {
        const who = data.type.includes("user") ? "You" : "Agent";
        const text = data.payload?.text || data.payload?.content || msg;
        appendCaption(`${who}: ${text}`);
      }
    } catch {
      /* ignore non-JSON */
    }
  });
  room.on(RoomEvent.TrackSubscribed, (track) => {
    if (track.kind === Track.Kind.Audio) {
      const el = track.attach();
      document.body.appendChild(el);
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
  appendCaption("[joined — wait for agent greeting]");
});

muteBtn.addEventListener("click", async () => {
  if (!micPublication) return;
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
    type: "app.text_input",
    schema_version: "1.0",
    payload: { text },
  };
  const bytes = new TextEncoder().encode(JSON.stringify(envelope));
  await room.localParticipant.publishData(bytes, { reliable: true });
  appendCaption(`You (typed): ${text}`);
  typedInput.value = "";
});
