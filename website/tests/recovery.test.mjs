import { test } from "node:test";
import assert from "node:assert/strict";
import { AssistanceController } from "../static/js/assistance-controller.mjs";
import { Application, actionRequest } from "../static/js/application.mjs";
import { LiveKitSeats } from "../static/js/livekit-bridge.mjs";
import { acquireTabLease } from "../static/js/tab-lease.mjs";

const storage = () => {
  const values = new Map();
  return { getItem: k => values.get(k), setItem: (k, v) => values.set(k, v), removeItem: k => values.delete(k) };
};
test("reload cleans up the saved generation before creating another; no token is stored", async () => {
  const saved = storage(), calls = [];
  const options = { storage: saved, sessionId: "shop", acquireMedia: async () => ({ getTracks: () => [] }),
    api: async (name, body) => { calls.push([name, body]); return { state: name === "start" ? "preparing" : name === "end" ? "ended" : "active", generation: "generation", tokens: { app: { token: "private" } } }; },
    connectSeats: async () => ({ registerApp() {}, publishFreshContext: async () => ({ revision: 1 }), playbackReady() {}, disconnect() {} }) };
  const first = new AssistanceController(options);
  await first.start({ mode: "typed" });
  assert.ok(saved.getItem("foodease.assistance-owner.v2:shop"));
  assert.equal(saved.getItem("foodease.assistance-owner.v2:shop").includes("private"), false);
  const second = new AssistanceController(options);
  await second.recover();
  assert.equal(calls.at(-1)[0], "end");
  assert.equal(saved.getItem("foodease.assistance-owner.v2:shop"), undefined);
  assert.equal(second.current, null);
  await second.start({ mode: "typed" });
  assert.equal(calls.filter(([n]) => n === "start").length, 2);
  await second.end();
});
test("unconfirmed cleanup on reload blocks replacement", async () => {
  const saved = storage();
  saved.setItem("foodease.assistance-owner.v2:shop", JSON.stringify({ request_id: "old", generation: "g" }));
  const c = new AssistanceController({ storage: saved, sessionId: "shop", api: async () => { throw new Error("offline"); } });
  await c.recover();
  await assert.rejects(c.start({ mode: "typed" }), /Cleanup/);
  assert.ok(saved.getItem("foodease.assistance-owner.v2:shop"));
});
for (const state of ["not_seen", "pending", "expired"]) test(`lookup ${state} retains original identity and explains uncertainty`, async () => {
  const errors = [], request = actionRequest("shop", "turn", 1, "cart.add_item", { item_id: "wrap-veg", quantity: 1 });
  const app = new Application({ sessionId: "shop", render() {}, onError: s => errors.push(s), transport: {
    lookup: async () => ({ state }), action: async () => { throw new Error("lost"); },
  } });
  const result = await app.execute(request);
  assert.equal(result.payload.status, "timeout_unknown");
  await app.reconcile(request.payload.action_id);
  assert.equal(app.pending.get(request.payload.action_id), request);
  assert.equal(app.outcomes.get(request.payload.action_id), state);
  assert.match(errors.at(-1), state === "expired" ? /expired|no longer retained/i : state === "not_seen" ? /not registered|not seen/i : /pending|processing/i);
});

function bridgeFixture(mode = "voice") {
  const events = Object.fromEntries(["DataReceived", "TrackSubscribed", "TrackUnsubscribed", "Disconnected", "Reconnecting", "Reconnected", "ParticipantDisconnected"].map(x => [x, x]));
  const statuses = [], sent = [], track = { enabled: true, stopped: false, stop() { this.stopped = true; } };
  class Room {
    constructor() { this.handlers = new Map(); this.remoteParticipants = new Map(); }
    on(e, cb) { this.handlers.set(e, cb); }
    emit(e, ...args) { this.handlers.get(e)?.(...args); }
    async connect(_url, role) {
      this.localParticipant = { identity: role, attributes: { "foodease.role": role, "foodease.session": "shop", "foodease.generation": "g" },
        publishTrack() {}, unpublishTrack() {}, publishData: async raw => { sent.push(JSON.parse(new TextDecoder().decode(raw))); } };
    }
    disconnect() {}
    startAudio() {}
  }
  let refreshes = 0;
  const application = { snapshot: { revision: 1 }, pending: new Map(), summaries: new Map([["summary", {}]]),
    subscribe: () => () => {}, refresh: async () => { refreshes++; return { revision: 1 }; } };
  const bridge = new LiveKitSeats({ prepared: { session_id: "shop", generation: "g", binding: { app_identity: "app", user_identity: "user", agent_identity: "agent" },
    tokens: { app: { token: "app" }, user: { token: "user" } } }, application,
    sdk: { Room, RoomEvent: events, Track: { Source: { Microphone: "mic" } } },
    media: { getTracks: () => [track], getAudioTracks: () => [track] }, mode, onStatus: s => statuses.push(s) });
  return { bridge, statuses, sent, track, application, refreshes: () => refreshes };
}
test("both seats must reconnect before fresh context, old summary is cleared, end defeats late recovery", async () => {
  const f = bridgeFixture();
  await f.bridge.connect();
  f.bridge.app.emit("Reconnecting"); f.bridge.user.emit("Reconnecting");
  assert.equal(f.track.enabled, false);
  assert.equal(f.application.summaries.size, 0);
  let attachments = 0;
  const agent = { identity: "agent", attributes: { "foodease.role": "agent", "foodease.session": "shop", "foodease.generation": "g" } };
  f.bridge.user.emit("TrackSubscribed", { kind: "audio", attach() { attachments++; } }, { trackSid: "late" }, agent);
  assert.equal(attachments, 0);
  await assert.rejects(f.bridge.text("add a wrap"), /reconnect/i);
  f.bridge.app.emit("Reconnected");
  await new Promise(resolve => setTimeout(resolve, 5));
  assert.equal(f.refreshes(), 0);
  f.bridge.user.emit("Reconnected");
  await new Promise(resolve => setTimeout(resolve, 5));
  assert.equal(f.refreshes(), 1);
  assert.ok(f.sent.some(e => e.payload?.intent === "resume"));
  await f.bridge.disconnect();
  f.bridge.user.emit("Reconnected");
  await new Promise(resolve => setTimeout(resolve, 5));
  assert.equal(f.track.stopped, true);
  assert.equal(f.statuses.includes("reconnected"), false);
});
test("bound agent loss ends locally while foreign participant loss is ignored", async () => {
  const { bridge } = bridgeFixture("typed");
  await bridge.connect();
  let stopped = 0;
  bridge.onDisconnected(() => { stopped++; });
  bridge.app.emit("ParticipantDisconnected", { identity: "foreign" });
  assert.equal(stopped, 0);
  bridge.app.emit("ParticipantDisconnected", { identity: "agent" });
  assert.equal(stopped, 1);
  await bridge.disconnect();
});
test("a paused mode stays paused after reconnect and an unanswered chooser never becomes voice", async () => {
  const f = bridgeFixture();
  await f.bridge.connect();
  f.bridge.paused = true;
  f.bridge.app.emit("Reconnecting"); f.bridge.app.emit("Reconnected");
  await new Promise(resolve => setTimeout(resolve, 5));
  assert.equal(f.statuses.at(-1), "paused");
  assert.equal(f.sent.some(e => e.payload?.intent === "resume"), false);
  assert.equal(f.track.enabled, false);
  await f.bridge.disconnect();
  const c = bridgeFixture("choice");
  await c.bridge.connect();
  c.bridge.app.emit("Reconnecting");
  assert.equal(c.bridge.closed, true);
  assert.equal(c.track.stopped, true);
});
test("duplicate tab lease is refused until its owner releases", async () => {
  let held = false;
  const locks = { request: async (_name, _options, callback) => {
    if (held) return callback(null);
    held = true;
    try { await callback({}); } finally { held = false; }
  } };
  const release = await acquireTabLease("shop", locks);
  await assert.rejects(acquireTabLease("shop", locks), /another tab/);
  release();
  await new Promise(resolve => setTimeout(resolve, 0));
  const next = await acquireTabLease("shop", locks);
  next();
});
for (const failure of ["expiry", "status"]) test(`active ${failure} stops resources and never restarts capture`, async () => {
  let stopped = 0, starts = 0, statuses = 0;
  const c = new AssistanceController({ monitorMs: failure === "status" ? 5 : 1000,
    acquireMedia: async () => { starts++; return { getTracks: () => [{ stop: () => stopped++ }] }; },
    api: async name => {
      if (name === "start") return { state: "preparing", generation: "g", ttl_seconds: failure === "expiry" ? 0.02 : 3600 };
      if (name === "status" && statuses++ > 0) throw new Error("expired credentials");
      return { state: name === "end" ? "ended" : "active" };
    }, connectSeats: async () => ({ registerApp() {}, publishFreshContext: async () => ({ revision: 1 }), playbackReady() {}, disconnect() {} }) });
  await c.start();
  await new Promise(resolve => setTimeout(resolve, 50));
  assert.ok(stopped > 0);
  assert.equal(starts, 1);
  assert.equal(c.current.cancelled, true);
});
test("credentials expiring during startup never activate or greet", async () => {
  let activated = 0;
  const c = new AssistanceController({ acquireMedia: async () => ({ getTracks: () => [] }),
    api: async name => {
      if (name === "start") return { state: "preparing", generation: "g", ttl_seconds: 0.001 };
      if (name === "status") await new Promise(resolve => setTimeout(resolve, 5));
      return { state: name === "end" ? "ended" : "active" };
    }, connectSeats: async () => ({ registerApp() {}, publishFreshContext: async () => ({ revision: 1 }), playbackReady() {}, activate() { activated++; }, disconnect() {} }) });
  await assert.rejects(c.start(), /expired/);
  assert.equal(activated, 0);
});
test("only the current resume receipt releases the reconnect barrier; later old receipts stay ignored", async () => {
  const f = bridgeFixture();
  let controls = 0;
  f.bridge.onControl = () => controls++;
  await f.bridge.connect();
  f.bridge.app.emit("Reconnecting"); f.bridge.app.emit("Reconnected");
  await new Promise(resolve => setTimeout(resolve, 5));
  const agent = { identity: "agent", attributes: { "foodease.role": "agent", "foodease.session": "shop", "foodease.generation": "g" } };
  const receipt = turnId => f.bridge.receive(new TextEncoder().encode(JSON.stringify({ schema_version: "2.0", session_id: "shop", event_id: crypto.randomUUID(),
    type: "agent.control", turn_id: turnId, timestamp: new Date().toISOString(), payload: { intent: "resume", mode: "voice" } })), agent, "foodease.events.v2");
  receipt("old");
  assert.equal(f.bridge.recovering, true);
  assert.equal(f.track.enabled, false);
  receipt(f.bridge.recoveryTurnId);
  assert.equal(f.bridge.recovering, false);
  assert.equal(f.track.enabled, true);
  f.bridge.paused = true; f.track.enabled = false;
  receipt("old-again");
  assert.equal(controls, 0);
  assert.equal(f.track.enabled, false);
  await f.bridge.disconnect();
});
test("reconnect deadline ends capture without a new submission", async t => {
  const { bridge, track, sent } = bridgeFixture();
  await bridge.connect();
  t.mock.timers.enable({ apis: ["setTimeout"] });
  bridge.app.emit("Reconnecting");
  t.mock.timers.tick(15000);
  assert.equal(bridge.closed, true);
  assert.equal(track.stopped, true);
  assert.equal(sent.some(e => e.type === "agent.action_request"), false);
});
test("a nonterminal found reply cannot clear uncertainty", async () => {
  const request = actionRequest("shop", "turn", 1, "cart.add_item", { item_id: "wrap-veg", quantity: 1 });
  const app = new Application({ sessionId: "shop", render() {}, transport: { lookup: async () => ({ state: "found",
    result: { ...request, type: "app.action_result", reply_to: request.event_id,
      payload: { ...request.payload, status: "timeout_unknown", verified_state: null } } }) } });
  app.pending.set(request.payload.action_id, request);
  assert.equal(await app.reconcile(request.payload.action_id), null);
  assert.equal(app.pending.size, 1);
});
