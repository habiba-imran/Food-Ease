import { test } from "node:test";
import assert from "node:assert/strict";
import { AssistanceController } from "../static/js/assistance-controller.mjs";

const deferred = () => { let resolve; const promise = new Promise((r) => { resolve = r; }); return { promise, resolve }; };

function fixture(blockStage = null) {
  const pending = deferred(), entered = deferred();
  const calls = [], states = [];
  let stops = 0, disconnects = 0, audioClosed = 0;
  const media = { getTracks: () => [{ stop() { stops += 1; } }] };
  const stage = async (name, result) => {
    calls.push(name);
    if (blockStage === name) { entered.resolve(); await pending.promise; }
    return result;
  };
  const seats = {
    registerApp: () => stage("register"),
    publishFreshContext: () => stage("context", { revision: 1 }),
    playbackReady: () => stage("playback"),
    closeAudio() { audioClosed += 1; },
    disconnect() { disconnects += 1; },
  };
  let failEnd = false;
  const api = async (name) => {
    if (name === "end") {
      calls.push("end");
      return { state: failEnd ? "cleanup_pending" : "ended" };
    }
    return stage(name, name === "start" ? { generation: "g", state: "preparing" }
      : name === "status" ? { state: "active" } : { state: "waiting_worker" });
  };
  const controller = new AssistanceController({ api, acquireMedia: () => stage("permission", media),
    connectSeats: () => stage("join", seats), onState: (state) => states.push(state),
    newId: () => "request", timeoutMs: 1000, pollMs: 0 });
  return { controller, calls, states, pending, entered, counts: () => ({ stops, disconnects, audioClosed }),
    failEnd() { failEnd = true; } };
}

test("permission, join, registration, fresh context and playback precede activation", async () => {
  const f = fixture();
  const first = f.controller.start();
  assert.equal(f.controller.start(), first);
  assert.equal((await first).state, "active");
  assert.deepEqual(f.calls, ["permission", "start", "join", "register", "context", "playback", "ready", "status"]);
  await f.controller.end();
  assert.ok(f.counts().stops > 0 && f.counts().disconnects > 0 && f.counts().audioClosed > 0);
});

for (const stage of ["permission", "start", "join", "register", "context", "playback", "ready", "status"]) {
  test(`manual selection during ${stage} stops late media/seats and cannot become active`, async () => {
    const f = fixture(stage);
    const starting = f.controller.start();
    const rejected = assert.rejects(starting, /cancelled/);
    await f.entered.promise;
    await f.controller.end();
    if (stage !== "permission") assert.ok(f.counts().stops > 0);
    f.pending.resolve();
    await rejected;
    assert.ok(f.counts().stops > 0);
    assert.equal(f.states.some((s) => s.state === "active"), false);
    if (["register", "context", "playback", "ready", "status", "join"].includes(stage)) {
      assert.ok(f.counts().disconnects > 0);
    }
  });
}

test("server cleanup failure does not leave local microphone/audio active", async () => {
  const f = fixture();
  await f.controller.start();
  f.failEnd();
  const ending = f.controller.end();
  assert.ok(f.counts().stops > 0 && f.counts().audioClosed > 0);
  assert.equal((await ending).state, "cleanup_pending");
  assert.equal(f.states.at(-1).serverCleanupPending, true);
  await assert.rejects(f.controller.start(), /Cleanup/);
});

test("permission denial never prepares or dispatches assistance", async () => {
  const calls = [];
  const controller = new AssistanceController({ acquireMedia: async () => { throw new Error("permission denied"); },
    api: async () => calls.push("api"), connectSeats: async () => calls.push("join"), newId: () => "request" });
  await assert.rejects(controller.start(), /permission denied/);
  assert.deepEqual(calls, []);
});

test("late cancelled permission cannot change a newer active generation's state", async () => {
  const late = deferred();
  const states = [];
  let permissionCalls = 0, ids = 0, stopped = 0;
  const media = { getTracks: () => [{ stop() { stopped += 1; } }] };
  const controller = new AssistanceController({ newId: () => `r-${++ids}`,
    acquireMedia: () => ++permissionCalls === 1 ? late.promise : Promise.resolve(media),
    api: async (name) => name === "start" ? { state: "preparing", generation: `g-${ids}` }
      : { state: name === "status" ? "active" : name === "end" ? "ended" : "waiting_worker" },
    connectSeats: async () => ({ registerApp: async () => {}, publishFreshContext: async () => ({ revision: 1 }),
      playbackReady: async () => {}, disconnect() {}, closeAudio() {} }),
    onState: (state) => states.push(state) });
  const old = controller.start();
  const rejected = assert.rejects(old, /cancelled/);
  await controller.end();
  await controller.start();
  late.resolve(media);
  await rejected;
  assert.equal(states.at(-1).state, "active");
  assert.ok(stopped > 0);
  await controller.end();
});
