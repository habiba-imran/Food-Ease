import { test, expect } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
const evidence = process.env.FOODEASE_UI_EVIDENCE || '../artifacts/footer-cart-2026-11-07';
const add = (page, id) => page.locator(`[data-menu-item][data-id="${id}"] [data-add-item]`);
test.beforeEach(async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/');
  await expect(page.locator('html')).toHaveAttribute('data-foodease-revision', /\d+/);
});
for (const width of [320, 375, 768, 1440]) {
  test(`footer information and search text align at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 });
    await page.locator('.search-shell').scrollIntoViewIfNeeded();
    const [shell, prefix, suggestion] = await Promise.all(['.search-shell', '.search-prefix', '[data-search-suggestion]'].map(selector => page.locator(selector).boundingBox()));
    for (const text of [prefix, suggestion]) expect(Math.abs(text.y + text.height / 2 - shell.y - shell.height / 2)).toBeLessThan(1);
    const footer = page.locator('.restaurant-footer');
    await expect(footer.getByRole('link', { name: 'support@megpakistan.com' })).toHaveAttribute('href', 'mailto:support@megpakistan.com');
    await expect(footer.getByRole('link', { name: '042 111 634 111' })).toHaveAttribute('href', 'tel:+9242111634111');
    await expect(footer.locator('address')).toContainText('318-B, Main Khayaban-e-Jinnah');
    await expect(footer.locator('dt')).toHaveCount(7);
    await expect(footer.locator('dd')).toHaveText(Array(7).fill(/11:00 AM.*03:50 AM/));
    expect(await footer.evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await mkdir(evidence, { recursive: true });
    await page.screenshot({ path: `${evidence}/search-${width}.png` });
    await footer.screenshot({ path: `${evidence}/footer-${width}.png` });
  });
}

test('queued additions update immediately, charge one fee, and settle without doubling', async ({ page }) => {
  let release; const gate = new Promise(resolve => { release = resolve; });
  let writes = 0;
  await page.route('**/api/v2/app/action', async route => {
    if (route.request().postDataJSON().payload.operation === 'cart.add_item') { writes++; await gate; }
    await route.continue();
  });
  try {
    await add(page, 'biryani-chicken').click();
    await expect(page.locator('[data-cart-count]')).toHaveText('1', { timeout: 700 });
    await expect(page.locator('[data-floating-cart-total]')).toHaveText('600 PKR', { timeout: 700 });
    await expect(page.locator('[data-cart-toast]')).toHaveAttribute('data-state', 'pending');
    await add(page, 'drink-cola').click();
    await expect(page.locator('[data-cart-count]')).toHaveText('2', { timeout: 700 });
    await expect(page.locator('[data-floating-cart-total]')).toHaveText('700 PKR');
    const sessionId = await page.evaluate(() => sessionStorage.getItem('foodease.shopping-session.v2'));
    const state = await (await page.request.get('/api/v2/app/context', { headers: { 'X-FoodEase-Session': sessionId } })).json();
    expect(state.cart.lines).toHaveLength(0);
    release();
    await expect(page.locator('[data-cart-trigger]')).toHaveAttribute('aria-busy', 'false');
    await expect(page.locator('[data-cart-count]')).toHaveText('2');
    await expect(page.locator('[data-floating-cart-total]')).toHaveText('700 PKR');
    expect(writes).toBe(2);
    await page.locator('[data-cart-trigger]').click();
    await expect(page.locator('[data-cart-lines] .cart-line')).toHaveCount(2);
    await expect(page.locator('[data-cart-total]')).toHaveText('700 PKR');
  } finally { release(); await page.unrouteAll({ behavior: 'wait' }); }
});

test('details Add closes immediately and previews the selected quantity during a slow request', async ({ page }) => {
  let release; const gate = new Promise(resolve => { release = resolve; });
  await page.route('**/api/v2/app/action', async route => {
    if (route.request().postDataJSON().payload.operation === 'cart.add_item') await gate;
    await route.continue();
  });
  try {
    await page.locator('[data-menu-item][data-id=wrap-hot-chicken] .food-photo').click();
    await page.locator('[data-detail-quantity]').fill('2');
    await page.locator('[data-detail-add]').click();
    await expect(page.locator('[data-item-dialog]')).toBeHidden({ timeout: 700 });
    await expect(page.locator('[data-cart-count]')).toHaveText('2', { timeout: 700 });
    await expect(page.locator('[data-floating-cart-total]')).toHaveText('1750 PKR');
    release();
    await expect(page.locator('[data-cart-trigger]')).toHaveAttribute('aria-busy', 'false');
    await expect(page.locator('[data-cart-count]')).toHaveText('2');
    await expect(page.locator('[data-item-dialog]')).toBeHidden();
  } finally { release(); await page.unrouteAll({ behavior: 'wait' }); }
});

test('a rejected addition rolls the preview back and never confirms success', async ({ page }) => {
  await page.route('**/api/v2/app/action', route => {
    const body = route.request().postDataJSON();
    if (body.payload.operation === 'cart.add_item') body.payload.arguments.item_id = 'unknown-dish';
    return route.continue({ postData: JSON.stringify(body) });
  });
  await add(page, 'biryani-chicken').click();
  await expect(page.locator('[data-cart-trigger]')).toHaveAttribute('aria-busy', 'false');
  await expect(page.locator('[data-cart-count]')).toHaveText('0');
  await expect(page.locator('[data-floating-cart-total]')).toHaveText('0 PKR');
  await expect(page.locator('[data-cart-toast]')).toBeHidden();
  await expect(page.locator('[data-order-status]')).toContainText('unavailable');
});

test('lost addition response reconciles its original ID without a duplicate preview or write', async ({ page }) => {
  let writes = 0;
  await page.route('**/api/v2/app/action', async route => {
    if (route.request().postDataJSON().payload.operation === 'cart.add_item') {
      writes++; await route.fetch(); await route.abort();
    } else await route.continue();
  });
  await add(page, 'biryani-chicken').click();
  await expect(page.locator('[data-cart-trigger]')).toHaveAttribute('aria-busy', 'false');
  await expect(page.locator('[data-cart-count]')).toHaveText('1');
  await expect(page.locator('[data-floating-cart-total]')).toHaveText('600 PKR');
  await expect(page.locator('[data-cart-toast]')).toHaveAttribute('data-state', 'confirmed');
  expect(writes).toBe(1);
});
