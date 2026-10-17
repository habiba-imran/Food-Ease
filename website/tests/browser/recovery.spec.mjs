import { test, expect } from "@playwright/test";
import { readFile } from "node:fs/promises";
const fake = await readFile(new URL("../fake-livekit.mjs", import.meta.url), "utf8");
test.use({ channel: "chromium", permissions: ["microphone"], launchOptions: { args: ["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"] } });
test.beforeEach(async ({ page }) => {
  await page.route("**/static/vendor/livekit-client.2.15.4.mjs", r => r.fulfill({ body: fake, contentType: "text/javascript" }));
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("data-foodease-revision", /\d+/);
  await page.evaluate(() => {
    window.captured = [];
    const get = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
    navigator.mediaDevices.getUserMedia = async options => { const media = await get(options); window.captured.push(...media.getTracks()); return media; };
  });
});
async function start(page, mode = "typed") {
  await page.locator(mode === "voice" ? "[data-assist-voice]" : "[data-assist-start]").click();
  await expect(page.locator("html")).toHaveAttribute("data-assistance-state", `${mode}_active`);
}
async function say(page, text) {
  await page.locator("[data-assistant-input]").fill(text);
  await page.locator("[data-assistant-form] button[type=submit]").click();
}
async function stopped(page) {
  await expect.poll(() => page.evaluate(() => window.captured.every(t => t.readyState === "ended"))).toBe(true);
}
test("both seats reconnect with fresh manual state and resume only the existing voice consent", async ({ page }) => {
  await start(page, "voice");
  await page.evaluate(() => { for (const r of window.fakeLiveKit.rooms) r.emit("Reconnecting"); });
  await expect(page.locator("html")).toHaveAttribute("data-assistance-state", "reconnecting");
  expect(await page.evaluate(() => window.captured.every(t => !t.enabled))).toBe(true);
  await page.locator('[data-menu-item][data-id="wrap-hot-chicken"] [data-add-item]').click();
  await expect(page.locator("[data-cart-count]")).toHaveText("1");
  await page.evaluate(() => window.fakeLiveKit.rooms.find(r => r.role === "app").emit("Reconnected"));
  await expect(page.locator("html")).toHaveAttribute("data-assistance-state", "reconnecting");
  await page.evaluate(() => window.fakeLiveKit.rooms.find(r => r.role === "user").emit("Reconnected"));
  await expect(page.locator("html")).toHaveAttribute("data-assistance-state", "voice_active");
  await expect.poll(() => page.evaluate(() => window.captured.every(t => t.enabled && t.readyState === "live"))).toBe(true);
  await say(page, "read my cart");
  await expect(page.locator("[data-agent-transcript]")).toContainText("eight hundred fifty");
  expect(await page.evaluate(() => window.fakeLiveKit.rooms.filter(r => r.role === "user").length)).toBe(1);
});
test("manual end during reconnect prevents old events or tracks from reviving assistance", async ({ page }) => {
  await start(page, "voice");
  await page.evaluate(() => window.fakeLiveKit.rooms[0].emit("Reconnecting"));
  await page.locator("[data-assist-manual]").click();
  await stopped(page);
  await page.evaluate(() => { for (const r of window.fakeLiveKit.rooms) r.emit("Reconnected"); });
  await expect(page.locator("html")).toHaveAttribute("data-assistance-state", "manual");
  expect(await page.evaluate(() => document.querySelectorAll("audio[data-foodease-audio]").length)).toBe(0);
});
for (const component of ["stt", "tts"]) test(`${component} failure switches actual runtime to silent typing with the same cart`, async ({ page }) => {
  await start(page, "voice");
  await say(page, "add a wrap");
  await expect(page.locator("[data-cart-count]")).toHaveText("1");
  const sid = await page.evaluate(() => sessionStorage.getItem("foodease.shopping-session.v2"));
  await page.request.post(`/_test/provider-error/${sid}/${component}`);
  await expect(page.locator("html")).toHaveAttribute("data-assistance-state", "typed_active");
  await stopped(page);
  await say(page, "read my cart");
  await expect(page.locator("[data-agent-transcript]")).toContainText("eight hundred fifty");
  await expect(page.locator("[data-cart-count]")).toHaveText("1");
});
test("actual SDK model stream failure leaves manual ordering available", async ({ page }) => {
  await start(page);
  await say(page, "offline provider failure");
  await expect(page.locator("html")).toHaveAttribute("data-assistance-state", "manual");
  await page.locator('[data-menu-item][data-id="wrap-hot-chicken"] [data-add-item]').click();
  await expect(page.locator("[data-cart-count]")).toHaveText("1");
});
test("bound agent seat loss ends capture; backgrounding also requires a new gesture", async ({ page }) => {
  await start(page, "voice");
  await page.evaluate(() => { const r = window.fakeLiveKit.rooms[0]; r.emit("ParticipantDisconnected", r.agent); });
  await stopped(page);
  await expect(page.locator("html")).toHaveAttribute("data-assistance-state", "manual");
  await start(page, "voice");
  await page.evaluate(() => {
    Object.defineProperty(document, "visibilityState", { value: "hidden", configurable: true });
    document.dispatchEvent(new Event("visibilitychange"));
    Object.defineProperty(document, "visibilityState", { value: "visible", configurable: true });
    document.dispatchEvent(new Event("visibilitychange"));
  });
  await stopped(page);
  await expect(page.locator("html")).toHaveAttribute("data-assistance-state", "manual");
});
test("reload cleans up retained generation without capture and preserves cart", async ({ page }) => {
  await start(page, "voice");
  await say(page, "add a wrap");
  await expect(page.locator("[data-cart-count]")).toHaveText("1");
  await page.reload();
  await expect(page.locator("[data-cart-count]")).toHaveText("1");
  expect(await page.evaluate(() => window.fakeLiveKit?.rooms.length || 0)).toBe(0);
  await expect.poll(() => page.evaluate(() => sessionStorage.getItem(`foodease.assistance-owner.v2:${sessionStorage.getItem("foodease.shopping-session.v2")}`))).toBe(null);
  await start(page);
  await say(page, "read my cart");
  await expect(page.locator("[data-agent-transcript]")).toContainText("eight hundred fifty");
});
test("lost checkout response renders its original receipt once, including after reload", async ({ page }) => {
  await page.locator('[data-menu-item][data-id="wrap-hot-chicken"] [data-add-item]').click();
  await page.locator("[data-checkout-button]").click();
  await expect(page.locator("[data-confirm-order]")).toBeEnabled();
  let attempts = 0;
  await page.route("**/api/v2/app/action", async route => {
    if (route.request().postDataJSON().payload.operation === "checkout.submit_demo_order") {
      attempts++; await route.fetch(); await route.abort();
    } else await route.continue();
  });
  await page.locator("[data-confirm-order]").click();
  await expect(page.locator("[data-receipt-panel]")).toBeVisible();
  await expect(page.locator("[data-receipt-id]")).toHaveText(/^DEMO-/);
  await expect(page.locator("[data-receipt-id]")).not.toHaveText("DEMO-0000");
  const receipt = await page.locator("[data-receipt-id]").textContent();
  await page.reload();
  await expect(page.locator("[data-receipt-panel]")).toBeVisible();
  await expect(page.locator("[data-receipt-id]")).toHaveText(receipt);
  expect(attempts).toBe(1);
});
test("expired credentials stop captured media before seats can activate", async ({ page }) => {
  await page.route("**/v2/assist/start", r => r.fulfill({ status: 410, contentType: "application/json", body: '{}' }));
  await page.locator("[data-assist-voice]").click();
  await expect(page.locator("html")).toHaveAttribute("data-assistance-state", "error");
  await stopped(page);
  expect(await page.evaluate(() => window.fakeLiveKit?.rooms.length || 0)).toBe(0);
});
test("lost authority retention reports unavailable order state without replay", async ({ page }) => {
  await page.route("**/api/v2/app/action", r => r.abort());
  await page.locator('[data-menu-item][data-id="wrap-hot-chicken"] [data-add-item]').click();
  await expect(page.locator("[data-order-status]")).toContainText("unknown");
  const sid = await page.evaluate(() => sessionStorage.getItem("foodease.shopping-session.v2"));
  await page.request.post(`/_test/forget-shopping/${sid}`);
  await page.locator("[data-reconcile-action]").click();
  await expect(page.locator("[data-order-status]")).toContainText(/expired|no longer retained/);
  await expect(page.locator("[data-cart-count]")).toHaveText("0");
});
