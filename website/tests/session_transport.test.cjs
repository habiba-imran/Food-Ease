// Tests the actual request functions with simulated storage/fetch, not browser rendering.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { test } = require("node:test");

const app = fs.readFileSync(path.join(__dirname, "../static/js/app.js"), "utf8");
const source = app.slice(app.indexOf("let shoppingSessionPromise"), app.indexOf("let selectedDetailItem"));
const key = "foodease.shopping-session.v2";

function transport(storage, fetch, setStatus = () => {}) {
  const sandbox = vm.createContext({ window: { sessionStorage: storage }, fetch, setStatus });
  vm.runInContext(source, sandbox);
  return (url = "/api/app/context") => vm.runInContext(`shoppingFetch(${JSON.stringify(url)})`, sandbox);
}

function storage() {
  const values = new Map();
  return {
    getItem: (key) => values.get(key) || null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
  };
}

const ok = (data) => ({ ok: true, status: 200, json: async () => data });

test("one session is created for concurrent requests; reload reattaches", async () => {
  const saved = storage();
  const calls = [];
  const fetch = async (url, options) => {
    calls.push({ url, options });
    return ok({ session_id: "tab-one" });
  };
  const request = transport(saved, fetch);
  await Promise.all([request(), request()]);
  assert.equal(calls.filter((call) => call.url === "/api/v2/app/sessions").length, 1);
  assert.equal(saved.getItem(key), "tab-one");
  assert.equal(calls[1].options.headers["X-FoodEase-Session"], "tab-one");
  assert.equal(calls[1].options.credentials, "same-origin");
  const reloaded = transport(saved, fetch);
  await reloaded();
  assert.equal(calls[3].url, "/api/v2/app/sessions/attach");
  assert.deepEqual(JSON.parse(calls[3].options.body), { session_id: "tab-one" });
});

test("a fresh tab creates its own handle", async () => {
  let next = 0;
  const fetch = async () => ok({ session_id: `tab-${++next}` });
  const first = storage(), second = storage();
  await transport(first, fetch)();
  await transport(second, fetch)();
  assert.notEqual(first.getItem(key), second.getItem(key));
});

test("expired attachment reports uncertainty and never replaces/retries a mutation", async () => {
  const saved = storage();
  saved.setItem(key, "expired");
  const calls = [];
  const request = transport(saved, async (url) => {
    calls.push(url);
    return { ok: false, status: 410, json: async () => ({ error: "session_expired" }) };
  });
  await assert.rejects(request("/api/app/action"), /earlier order status is unavailable/);
  await assert.rejects(request("/api/app/action"), /earlier order status is unavailable/);
  assert.deepEqual(calls, ["/api/v2/app/sessions/attach"]);
  assert.equal(saved.getItem(key), null);
});

test("blocked storage still keeps one in-memory tab session", async () => {
  const blocked = {
    getItem() { throw new Error("blocked"); },
    setItem() { throw new Error("blocked"); },
  };
  let created = 0;
  const request = transport(blocked, async (url) => {
    if (url === "/api/v2/app/sessions") created += 1;
    return ok({ session_id: "memory-only" });
  });
  await request();
  await request();
  assert.equal(created, 1);
});

test("unknown transport failures do not trigger a mutation retry", async () => {
  const saved = storage();
  let writes = 0;
  const request = transport(saved, async (url) => {
    if (url === "/api/v2/app/sessions") return ok({ session_id: "one" });
    writes += 1;
    throw new Error("connection lost after commit");
  });
  await assert.rejects(request("/api/app/action"), /connection lost/);
  assert.equal(writes, 1);
});

test("mid-session expiry clears the saved handle and shows an honest status", async () => {
  const saved = storage();
  const messages = [];
  const request = transport(saved, async (url) => {
    if (url === "/api/v2/app/sessions") return ok({ session_id: "one" });
    return { ok: false, status: 410, json: async () => ({ error: "session_expired" }) };
  }, (message) => messages.push(message));
  await assert.rejects(request(), /earlier order status is unavailable/);
  assert.equal(saved.getItem(key), null);
  assert.match(messages[0], /earlier order status is unavailable/);
});
