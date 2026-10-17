import assert from "node:assert/strict";
import { test } from "node:test";
import { Application, actionRequest } from "../static/js/application.mjs";

const snapshot = (revision = 1) => ({ schema_version: "2.0", session_id: "shop", revision,
  route: "menu", focus_item_id: null, visible_items: [], filter_tags: [], category: null,
  max_price_pkr: null, search_query: "", cart: { lines: [], currency: "PKR", subtotal: 0, fees: [], total: 0 },
  valid_actions: [], valid_navigation_targets: [], checkout_available: false, action_pending: false, language: "en" });

test("manual shutdown rejects queued assistance work while retaining the submitted outcome", async () => {
  let release, entered, closed = false, submissions = 0;
  const hold = new Promise(resolve => { release = resolve; });
  const started = new Promise(resolve => { entered = resolve; });
  const app = new Application({ sessionId: "shop", render: () => {}, transport: {
    context: async () => snapshot(),
    action: async request => {
      submissions++;
      entered();
      await hold;
      return { schema_version: "2.0", session_id: "shop", type: "app.action_result",
        turn_id: request.turn_id, reply_to: request.event_id, context_revision: 1,
        payload: { action_id: request.payload.action_id, operation: request.payload.operation,
          status: "success", verified_state: {} } };
    },
  } });
  const first = app.manual("get_cart");
  await started;
  const queued = app.execute(actionRequest("shop", "voice", 1, "cart.add_item", { item_id: "wrap-veg", quantity: 1 }),
    { admit: () => { if (closed) throw new Error("Assistance ended"); } });
  const rejected = assert.rejects(queued, /Assistance ended/);
  closed = true;
  release();
  assert.equal((await first).payload.status, "success");
  await rejected;
  assert.equal(submissions, 1);
  assert.equal(app.pending.size, 0);
});

test("one renderer ignores regressive context and only publishes accepted context", async () => {
  const rendered = [], published = [];
  const app = new Application({ sessionId: "shop", transport: {},
    render: (state) => rendered.push(state.revision) });
  app.subscribe((state) => published.push(state.revision));
  await app.accept(snapshot(3));
  await app.accept(snapshot(2));
  assert.deepEqual(rendered, [3]);
  assert.deepEqual(published, [3]);
});

test("remote request identity/revision survives forwarding and render precedes context publish", async () => {
  const steps = [];
  const request = actionRequest("shop", "turn", 1, "navigate", { target: "cart" });
  const app = new Application({ sessionId: "shop", transport: {
    action: async (value) => {
      assert.deepEqual(value, request);
      steps.push("action");
      return { schema_version: "2.0", type: "app.action_result", session_id: "shop",
        turn_id: "turn", event_id: "result", reply_to: request.event_id, context_revision: 2,
        payload: { action_id: request.payload.action_id, operation: "navigate", status: "success",
          verified_state: { route: "cart" } } };
    }, context: async () => ({ ...snapshot(2), route: "cart" }),
  }, render: () => steps.push("render") });
  app.subscribe(() => steps.push("publish"));
  await app.execute(request);
  assert.deepEqual(steps, ["action", "render", "publish"]);
});

test("uncorrelated and unknown responses cannot become success announcements or write retries", async () => {
  let submissions = 0;
  const app = new Application({ sessionId: "shop", transport: {
    action: async () => { submissions++; throw new TypeError("response lost"); },
    lookup: async () => ({ state: "pending" }), context: async () => snapshot(),
  }, render: () => {} });
  await app.accept(snapshot());
  const result = await app.manual("cart.add_item", { item_id: "wrap-veg", quantity: 1 });
  assert.equal(result.payload.status, "timeout_unknown");
  assert.equal(submissions, 1);
  await assert.rejects(app.manual("cart.add_item", { item_id: "wrap-veg", quantity: 1 }), /unresolved/);
  assert.equal(submissions, 1);
});

test("queued manual commands use the latest revision and an explicit replay retains its envelope", async () => {
  let revision = 1;
  const requests = [];
  const results = new Map();
  const app = new Application({ sessionId: "shop", render: () => {}, transport: {
    context: async () => snapshot(revision),
    action: async (request) => {
      requests.push(request);
      if (results.has(request.payload.action_id)) return results.get(request.payload.action_id);
      assert.equal(request.context_revision, revision);
      const result = { schema_version: "2.0", session_id: "shop", type: "app.action_result",
        turn_id: request.turn_id, reply_to: request.event_id, context_revision: ++revision,
        payload: { action_id: request.payload.action_id, operation: request.payload.operation,
          status: "success", verified_state: { route: "menu" } } };
      results.set(request.payload.action_id, result);
      return result;
    },
  } });
  await app.accept(snapshot());
  await Promise.all([app.manual("navigate", { target: "menu" }, "first"), app.manual("navigate", { target: "menu" }, "second")]);
  assert.deepEqual(requests.map((r) => r.context_revision), [1, 2]);
  await app.manual("navigate", { target: "menu" }, "first");
  assert.equal(requests[0].event_id, requests[2].event_id);
  await assert.rejects(app.manual("navigate", { target: "cart" }, "first"), /different request/);
});

test("an unresolved action survives reload without persisting checkout tokens", async () => {
  const values = new Map();
  const storage = { getItem: (k) => values.get(k), setItem: (k, v) => values.set(k, v), removeItem: (k) => values.delete(k) };
  const transport = { context: async () => snapshot(), action: async () => { throw new Error("offline"); }, lookup: async () => ({ state: "pending" }) };
  const app = new Application({ sessionId: "shop", transport, storage, render: () => {} });
  await app.accept(snapshot());
  await app.manual("checkout.submit_demo_order", { confirmed: true, confirmation_token: "private-cart-token", summary_revision: 1 });
  assert.equal(app.pending.size, 1);
  assert.ok(![...values.values()].join().includes("private-cart-token"));
  const reloaded = new Application({ sessionId: "shop", transport, storage, render: () => {} });
  assert.equal(reloaded.pending.size, 1);
  await assert.rejects(reloaded.manual("cart.add_item", { item_id: "wrap-veg", quantity: 1 }), /unresolved/);
});

test("verified mutation remains owned until failed view delivery is reconciled without resubmit", async () => {
  let failedView = false, submissions = 0, result;
  const app = new Application({ sessionId: "shop", render: () => { if (failedView) throw new Error("renderer unavailable"); }, transport: {
    context: async () => snapshot(2),
    action: async (request) => {
      submissions++;
      result = { schema_version: "2.0", session_id: "shop", type: "app.action_result",
        turn_id: request.turn_id, reply_to: request.event_id, context_revision: 2,
        payload: { action_id: request.payload.action_id, operation: request.payload.operation,
          status: "success", verified_state: { route: "cart" } } };
      return result;
    }, lookup: async () => ({ state: "found", result }),
  } });
  await app.accept(snapshot());
  failedView = true;
  await assert.rejects(app.manual("navigate", { target: "cart" }), /could not synchronize/);
  assert.equal(app.pending.size, 1);
  await assert.rejects(app.manual("navigate", { target: "menu" }), /unresolved/);
  await assert.rejects(app.reconcile([...app.pending.keys()][0]), /renderer unavailable/);
  assert.equal(app.pending.size, 1);
  failedView = false;
  await app.reconcile([...app.pending.keys()][0]);
  assert.equal(app.pending.size, 0);
  assert.equal(submissions, 1);
});
