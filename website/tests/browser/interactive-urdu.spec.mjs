// Real SDK worker -> bound RPC -> server cart -> existing DOM. Speech/model/RTC are fakes.
import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';
const fake = await readFile(new URL('../fake-livekit.mjs', import.meta.url), 'utf8');
const panel = page => page.locator('[data-voice-controls]');
async function say(page, text) {
  const input = page.locator('[data-assistant-input]');
  // Closing a shopping dialog restores the compact launcher; reopen its typing panel.
  if (!await input.isVisible()) await page.locator('[data-voice-launcher]').click();
  await input.fill(text);
  await page.locator('[data-assistant-form] button[type=submit]').click();
}
async function snapshot(page) {
  return page.evaluate(async () => (await fetch('/api/v2/app/context', {
    headers: { 'X-FoodEase-Session': sessionStorage.getItem('foodease.shopping-session.v2') },
  })).json());
}
test.beforeEach(async ({ page, context }) => {
  await context.addCookies([{ name: 'foodease_test_language', value: 'ur', url: 'http://127.0.0.1:8186' }]);
  await page.route('**/static/vendor/livekit-client.2.15.4.mjs', r => r.fulfill({ body: fake, contentType: 'text/javascript' }));
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/');
  await expect(page.locator('html')).toHaveAttribute('data-foodease-revision', /\d+/);
  { await page.locator('[data-voice-launcher]').click(); await page.locator('[data-voice-typed]').click(); }
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'typed_active');
});

for (const width of [1440, 390]) test(`Urdu browsing and Roman Urdu followup update the actual cart at ${width}px`, async ({ page }) => {
  await page.setViewportSize({ width, height: 900 });
  await panel(page).locator('[data-voice-panel-close]').click();
  await page.locator('#menu-search').fill('juice');
  await expect.poll(async () => (await snapshot(page)).search_query).toBe('juice');
  await page.locator('[data-voice-launcher]').click();
  await say(page, 'برگر دکھاؤ');
  await expect.poll(async () => (await snapshot(page)).category).toBe('burgers');
  await expect(page.locator('#menu-search')).toHaveValue('');
  await expect(page.locator('#menu-category-section-burgers')).toBeInViewport();
  await say(page, 'سب سے سستا برگر دکھاؤ');
  await expect(page.locator('[data-agent-transcript]')).toContainText('سبزی کی پیٹی والا برگر');
  await say(page, 'pehle wale do add kar do');
  await expect(page.locator('[data-cart-count]')).toHaveText('2');
  expect((await snapshot(page)).cart.lines[0]).toMatchObject({ item_id: 'burger-veg', quantity: 2 });
  await expect(page.locator('[data-cart-toast]')).toHaveAttribute('lang', 'ur');
  await say(page, 'تعداد تین کر دو');
  await expect(page.locator('[data-cart-count]')).toHaveText('3');
  await say(page, 'کارٹ دکھاؤ');
  await expect(page.locator('[data-cart-dialog]')).toBeVisible();
  await expect(page.locator('[data-cart-lines]')).toContainText('Veggie Patty Burger');
  await say(page, 'کارٹ بند کرو');
  await expect(page.locator('[data-cart-dialog]')).toBeHidden();
  await say(page, 'یہ والا ہٹا دو');
  await expect(page.locator('[data-cart-count]')).toHaveText('0');
});

test('Urdu clear review is delivered before consent; manual cart and voice use one state', async ({ page }) => {
  await say(page, 'دو کولا شامل کرو');
  await expect(page.locator('[data-cart-count]')).toHaveText('2');
  await panel(page).locator('[data-voice-panel-close]').click();
  await page.locator('[data-menu-item][data-id="side-fries"] [data-add-item]').click();
  await expect(page.locator('[data-cart-count]')).toHaveText('3');
  await page.locator('[data-voice-launcher]').click();
  await say(page, 'کل کتنا ہوا');
  await expect(page.locator('[data-agent-transcript]')).toContainText('فرائز');
  await say(page, 'کارٹ خالی کرو');
  await expect(page.locator('[data-agent-transcript]')).toContainText('کیا کارٹ کی تمام چیزیں');
  await expect(page.locator('[data-cart-count]')).toHaveText('3');
  await say(page, 'جی ہاں');
  await expect(page.locator('[data-cart-count]')).toHaveText('0');
  expect((await snapshot(page)).cart.lines).toEqual([]);
});
