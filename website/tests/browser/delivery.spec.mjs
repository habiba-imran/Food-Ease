// DOM/keyboard checks only; these do not substitute for human screen-reader acceptance.
import { test, expect } from "@playwright/test";
import { readFile } from "node:fs/promises";
const fake = await readFile(new URL("../fake-livekit.mjs", import.meta.url), "utf8");
test.beforeEach(async ({ page }) => {
  await page.route("**/static/vendor/livekit-client.2.15.4.mjs", r => r.fulfill({ body: fake, contentType: "text/javascript" }));
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("data-foodease-revision", /\d+/);
});
async function keyActivate(page, selector) {
  const target = page.locator(selector);
  await expect(target).toBeVisible();
  await target.focus();
  await expect(target).toBeFocused();
  await page.keyboard.press("Enter");
}
test("keyboard-activated manual checkout uses real authority with no capture or dispatch", async ({ page }) => {
  let starts = 0;
  page.on("request", r => { if (r.url().endsWith("/v2/assist/start")) starts++; });
  await page.evaluate(() => { navigator.mediaDevices.getUserMedia = () => { throw new Error("Manual mode cannot capture"); }; });
  await keyActivate(page, "[data-assist-manual]");
  await keyActivate(page, '[data-menu-item][data-id="wrap-hot-chicken"] [data-add-item]');
  await expect(page.locator("[data-cart-count]")).toHaveText("1");
  await keyActivate(page, "[data-checkout-button]");
  await expect(page.locator("[data-confirm-order]")).toBeEnabled();
  await keyActivate(page, "[data-confirm-order]");
  await expect(page.locator("[data-receipt-panel]")).toBeVisible();
  await expect(page.locator("[data-receipt-id]")).toHaveText(/^DEMO-/);
  await expect(page.locator("[data-receipt-id]")).not.toHaveText("DEMO-0000");
  await expect(page.locator("[data-cart-count]")).toHaveText("0");
  await keyActivate(page, "[data-receipt-close]");
  await expect(page.locator("[data-checkout-dialog]")).not.toBeVisible();
  expect(starts).toBe(0);
});
test("Tab reaches manual exit within checkout while typed assistance is active", async ({ page }) => {
  await keyActivate(page, "[data-assist-start]");
  await expect(page.locator("html")).toHaveAttribute("data-assistance-state", "typed_active");
  await keyActivate(page, '[data-menu-item][data-id="wrap-hot-chicken"] [data-add-item]');
  await expect(page.locator("[data-cart-count]")).toHaveText("1");
  await keyActivate(page, "[data-checkout-button]");
  await expect(page.locator("[data-checkout-dialog]")).toBeVisible();
  let reached = false;
  for (let index = 0; index < 30; index++) {
    if (await page.locator("[data-assist-manual]").evaluate(el => el === document.activeElement)) { reached = true; break; }
    await page.keyboard.press("Tab");
  }
  expect(reached).toBe(true);
  await page.keyboard.press("Enter");
  await expect(page.locator("html")).toHaveAttribute("data-assistance-state", "manual");
  await expect(page.locator("[data-checkout-dialog]")).toBeVisible();
  await expect(page.locator("[data-cart-count]")).toHaveText("1");
});
test("two actual browser cookie contexts retain separate shopping carts", async ({ page, browser }) => {
  await keyActivate(page, '[data-menu-item][data-id="wrap-hot-chicken"] [data-add-item]');
  await expect(page.locator("[data-cart-count]")).toHaveText("1");
  const second = await browser.newContext();
  try {
    const other = await second.newPage();
    await other.goto("/");
    await expect(other.locator("html")).toHaveAttribute("data-foodease-revision", /\d+/);
    await expect(other.locator("[data-cart-count]")).toHaveText("0");
    expect(await other.evaluate(() => sessionStorage.getItem("foodease.shopping-session.v2")))
      .not.toBe(await page.evaluate(() => sessionStorage.getItem("foodease.shopping-session.v2")));
  } finally { await second.close(); }
});
