import { test, expect } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { mkdir } from "node:fs/promises";

const fake = await readFile(new URL("../fake-livekit.mjs", import.meta.url), "utf8");
test.beforeEach(async ({ page }) => {
  await page.route("**/static/vendor/livekit-client.2.15.4.mjs", (route) => route.fulfill({ body: fake, contentType: "text/javascript" }));
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("data-foodease-revision", /\d+/);
});
test.afterEach(async ({ page }, info) => {
  if (info.status !== info.expectedStatus) {
    const sid = await page.evaluate(() => sessionStorage.getItem("foodease.shopping-session.v2"));
    console.log("Offline failure state:", await (await page.request.get(`/_test/state/${sid}`)).json());
    console.log("Offline RPCs:", await page.evaluate(() => window.fakeLiveKit?.rpcCalls));
  }
});
async function start(page) {
  await page.evaluate(() => {
    window.typedMicrophoneCalls = 0;
    navigator.mediaDevices.getUserMedia = async () => { window.typedMicrophoneCalls++; throw new Error("Typed mode must not request a microphone."); };
  });
  await page.getByRole("button", { name: "Start typed guidance", exact: true }).click();
  await expect(page.locator("[data-agent-status]")).toHaveText("ready/listening", { timeout: 15000 });
}
async function say(page, text) {
  await page.locator("[data-assistant-input]").fill(text);
  await page.locator("[data-assistant-form] button[type=submit]").click();
}
test("actual browser + website + worker: typed order, exact summary and demo receipt", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await start(page);
  await say(page, "Add two Hot Chicken Wraps to my cart");
  await expect(page.locator("[data-cart-lines]")).toContainText("2 x 850 PKR");
  await expect(page.locator("[data-cart-total]")).toHaveText("1750 PKR");
  await expect(page.locator("[data-agent-transcript]")).toContainText("one thousand seven hundred fifty rupees");
  await say(page, "Read my checkout summary");
  await expect(page.locator("[data-checkout-dialog]")).toBeVisible();
  await expect(page.locator("[data-checkout-total]")).toHaveText("1750 PKR");
  await expect(page.locator("[data-agent-transcript]")).toContainText("Shall I place this demo order?");
  await say(page, "yes");
  await expect(page.locator("[data-receipt-panel]")).toBeVisible();
  await expect(page.locator("[data-receipt-id]")).toHaveText(/^DEMO-/);
  await expect(page.locator("[data-cart-count]")).toHaveText("0");
  expect(await page.evaluate(() => window.typedMicrophoneCalls)).toBe(0);
  await page.locator("[data-receipt-panel]").scrollIntoViewIfNeeded();
  await mkdir("../orchestration/evidence/final/phase-08/browser", { recursive: true });
  await page.screenshot({ path: "../orchestration/evidence/final/phase-08/browser/typed-receipt.png" });
  expect(errors).toEqual([]);
  const receipt = await page.locator("[data-receipt-id]").textContent();
  await page.reload();
  await expect(page.locator("[data-receipt-panel]")).toBeVisible();
  await expect(page.locator("[data-receipt-id]")).toHaveText(receipt);
});
test("manual filtering exactly matches authoritative IDs; search clear and availability", async ({ page }) => {
  await page.locator("[data-filter=budget]").click();
  await expect(page.locator("[data-filter=budget]")).toHaveAttribute("aria-pressed", "true");
  const authoritative = await page.evaluate(async () => (await fetch("/api/v2/app/context", {
    headers: { "X-FoodEase-Session": sessionStorage.getItem("foodease.shopping-session.v2") },
  })).json());
  const visible = await page.locator("[data-menu-item]:not(.is-hidden)").evaluateAll((cards) => cards.map((c) => c.dataset.id));
  expect(visible).toEqual(authoritative.visible_items.map((i) => i.item_id));
  await page.locator("[data-filter=available]").click();
  await expect(page.locator("[data-filter=available]")).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator("[data-menu-item][data-available=false]:not(.is-hidden)")).toHaveCount(0);
  await page.locator("#menu-search").fill("no-such-food");
  await expect(page.locator("[data-visible-count]")).toHaveText("0");
  await page.locator("[data-clear-menu-state]").click();
  await expect(page.locator("#menu-search")).toHaveValue("");
  await expect(page.locator("[data-visible-count]")).toHaveText("25");
  await page.locator("a.brand-mark").click();
  await expect(page.locator("html")).toHaveAttribute("data-foodease-route", "home");
});

async function inject(page, operation, args = {}, overrides = {}) {
  return page.evaluate(async ({ operation, args, overrides }) => {
    const seat = window.fakeLiveKit.rooms.find((r) => r.role === "app" && !r.closed);
    const snapshot = await (await fetch("/api/v2/app/context", { headers: { "X-FoodEase-Session": seat.sid } })).json();
    const request = { schema_version: "2.0", session_id: seat.sid, event_id: crypto.randomUUID(),
      turn_id: `injected-${crypto.randomUUID()}`, context_revision: snapshot.revision, timestamp: new Date().toISOString(),
      type: "agent.action_request", payload: { action_id: crypto.randomUUID(), operation, arguments: args }, ...overrides };
    return JSON.parse(await seat.rpc.get("foodease.action.v2")({ callerIdentity: "agent", payload: JSON.stringify(request) }));
  }, { operation, args, overrides });
}
test("injected bound agent actions visibly render menu, item, cart and checkout", async ({ page }) => {
  await start(page);
  const found = await inject(page, "search_menu", { query: "burger" });
  const ids = found.payload.verified_state.items.map((i) => i.item_id);
  expect(await page.locator("[data-menu-item]:not(.is-hidden)").evaluateAll((items) => items.map((i) => i.dataset.id))).toEqual(ids);
  const available = found.payload.verified_state.items.find((i) => i.available);
  await inject(page, "select_item", { item_id: available.item_id });
  await expect(page.locator("[data-item-dialog]")).toBeVisible();
  await expect(page.locator("[data-detail-name]")).toHaveText(available.name);
  await inject(page, "cart.add_item", { item_id: available.item_id, quantity: 2 });
  await expect(page.locator("[data-cart-count]")).toHaveText("2");
  await inject(page, "checkout.get_summary");
  await expect(page.locator("[data-item-dialog]")).not.toBeVisible();
  await expect(page.locator("[data-checkout-dialog]")).toBeVisible();
  await expect(page.locator("[data-checkout-lines]")).toContainText(available.name);
});
test("reply lost after a real commit reconciles once; rejected actions never announce success", async ({ page }) => {
  let submissions = 0;
  await page.route("**/api/v2/app/action", async (route) => {
    if (route.request().postDataJSON().payload.operation === "cart.add_item") {
      submissions++;
      await route.fetch(); // authoritative commit happened; lose only its response
      await route.abort();
    } else await route.continue();
  });
  await page.locator('[data-menu-item][data-id="wrap-hot-chicken"] [data-add-item]').click();
  await expect(page.locator("[data-cart-count]")).toHaveText("1");
  expect(submissions).toBe(1);
  await page.unroute("**/api/v2/app/action");
  await start(page);
  const result = await inject(page, "cart.add_item", { item_id: "burger-soldout", quantity: 1 });
  expect(result.payload.status).toBe("rejected");
  await expect(page.locator("[data-order-status]")).toContainText("not completed");
  await expect(page.locator("[data-cart-count]")).toHaveText("1");
});
test("typed assistance does not attach remote audio", async ({ page }) => {
  await start(page);
  await page.evaluate(() => {
    const user = window.fakeLiveKit.rooms.find((r) => r.role === "user");
    user.modeForTest = "voice";
    // Live production instance remains typed: remote audio must not attach at all.
    const audio = { kind: "audio", attach() { window.fakeLiveKit.audioAttachments++; return document.createElement("audio"); } };
    user.emit("TrackSubscribed", audio, { trackSid: "track" }, user.agent);
    user.emit("TrackSubscribed", audio, { trackSid: "track" }, user.agent);
  });
  expect(await page.evaluate(() => window.fakeLiveKit.audioAttachments)).toBe(0);
  await page.locator("[data-assist-end]").click();
  await expect(page.locator("[data-agent-status]")).toHaveText("ended");
  await expect(page.locator("audio[data-foodease-audio]")).toHaveCount(0);
});
test("voice audio attaches once and end stops fake media immediately; native captions are ignored", async ({ page }) => {
  await page.evaluate(() => {
    window.fakeStops = 0;
    Object.defineProperty(navigator.mediaDevices, "getUserMedia", { value: async () => ({
      getTracks: () => [{ stop() { window.fakeStops++; } }], getAudioTracks: () => [{ kind: "audio" }],
    }) });
  });
  await page.locator("[data-assist-voice]").click();
  await expect(page.locator("[data-agent-status]")).toHaveText("ready/listening");
  await page.evaluate(() => {
    const user = window.fakeLiveKit.rooms.find((r) => r.role === "user");
    const track = { kind: "audio", attach() {
      window.fakeLiveKit.audioAttachments++;
      const element = document.createElement("audio");
      element.play = async () => {};
      element.pause = () => {};
      return element;
    }, detach(element) { element.remove(); } };
    user.emit("TrackSubscribed", track, { trackSid: "single-audio" }, user.agent);
    user.emit("TrackSubscribed", track, { trackSid: "single-audio" }, user.agent);
    user.emit("transcriptionReceived", [{ id: "native", text: "Duplicate native caption", final: true }], user.agent);
  });
  expect(await page.evaluate(() => window.fakeLiveKit.audioAttachments)).toBe(1);
  await expect(page.locator("audio[data-foodease-audio]")).toHaveCount(1);
  await expect(page.locator("[data-agent-transcript]")).not.toContainText("Duplicate native caption");
  await page.locator("[data-assist-end]").click();
  await expect(page.locator("audio[data-foodease-audio]")).toHaveCount(0);
  expect(await page.evaluate(() => window.fakeStops)).toBeGreaterThan(0);
});
test("foreign RPC callers cannot forward actions", async ({ page }) => {
  await start(page);
  const rejected = await page.evaluate(async () => {
    const seat = window.fakeLiveKit.rooms.find((r) => r.role === "app");
    try { await seat.rpc.get("foodease.action.v2")({ callerIdentity: "intruder", payload: "{}" }); return false; }
    catch { return true; }
  });
  expect(rejected).toBe(true);
  await expect(page.locator("[data-cart-count]")).toHaveText("0");
});
test("stale actions cannot change a newer view and reconnect republishes current context", async ({ page }) => {
  await start(page);
  await inject(page, "search_menu", { query: "burger" });
  const revision = await page.locator("html").getAttribute("data-foodease-revision");
  const old = await inject(page, "cart.add_item", { item_id: "wrap-hot-chicken", quantity: 1 }, { context_revision: 1 });
  expect(old.payload.status).toBe("stale_context");
  await expect(page.locator("html")).toHaveAttribute("data-foodease-revision", revision);
  await expect(page.locator("[data-cart-count]")).toHaveText("0");
  const before = await page.evaluate(() => window.fakeLiveKit.contexts.length);
  await page.evaluate(() => {
    const app = window.fakeLiveKit.rooms.find((r) => r.role === "app");
    app.emit("Reconnecting"); app.emit("Reconnected");
  });
  await expect.poll(() => page.evaluate(() => window.fakeLiveKit.contexts.length)).toBe(before + 1);
  expect(await page.evaluate(() => window.fakeLiveKit.contexts.at(-1).payload.search_query)).toBe("burger");
});
test("unknown action survives reload, blocks resubmit and reconciles a delayed original outcome", async ({ page }) => {
  let original, attempts = 0;
  await page.route("**/api/v2/app/action", async (route) => {
    if (route.request().postDataJSON().payload.operation === "cart.add_item") {
      attempts++;
      original = route.request().postDataJSON();
      await route.abort();
    } else await route.continue();
  });
  const add = page.locator('[data-menu-item][data-id="wrap-hot-chicken"] [data-add-item]');
  await add.click();
  await expect(page.locator("[data-order-status]")).toContainText("unknown");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-foodease-revision", "1");
  await add.click();
  await expect(page.locator("[data-order-status]")).toContainText("unresolved");
  expect(attempts).toBe(1);
  const response = await page.request.post("/api/v2/app/action", { data: original,
    headers: { "X-FoodEase-Session": original.session_id } });
  expect(response.ok()).toBe(true); // release the delayed *original* request once
  await page.locator("[data-reconcile-action]").click();
  await expect(page.locator("[data-cart-count]")).toHaveText("1");
  await expect(page.locator("[data-order-status]")).toContainText("outcomes have been checked");
  expect(attempts).toBe(1);
});
test("manual changes reach worker-visible context; partial captions keep focus and replace", async ({ page }) => {
  await start(page);
  await page.locator('[data-menu-item][data-id="wrap-hot-chicken"] [data-add-item]').click();
  await expect.poll(() => page.evaluate(() => window.fakeLiveKit.contexts.at(-1)?.payload.cart.lines[0]?.quantity)).toBe(1);
  await page.locator("[data-assistant-input]").focus();
  await page.evaluate(() => {
    const user = window.fakeLiveKit.rooms.find((r) => r.role === "user");
    const event = { schema_version: "2.0", session_id: user.sid, turn_id: "caption-turn", timestamp: "2026-10-17T12:00:00Z",
      type: "transcript.assistant", payload: { utterance_id: "caption", text: "Your cart", phase: "updated" } };
    for (const [id, text, phase] of [["partial", "Your cart", "updated"], ["final", "Your cart has one wrap.", "completed"], ["late", "Obsolete", "updated"]]) {
      user.emit("DataReceived", new TextEncoder().encode(JSON.stringify({ ...event, event_id: id,
        payload: { ...event.payload, text, phase } })), user.agent, null, "foodease.events.v2");
    }
  });
  await expect(page.locator('[data-utterance-id="caption"]')).toHaveCount(1);
  await expect(page.locator('[data-utterance-id="caption"]')).toHaveText("Your cart has one wrap.");
  await expect(page.locator("[data-assistant-input]")).toBeFocused();
});
