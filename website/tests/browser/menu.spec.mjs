import { test, expect } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
const evidence = process.env.FOODEASE_UI_EVIDENCE || '../artifacts/menu-experience-2026-11-07';
const card = (page, id) => page.locator(`[data-menu-item][data-id="${id}"]`);
test.beforeEach(async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/');
  await expect(page.locator('html')).toHaveAttribute('data-foodease-revision', /\d+/);
});
for (const width of [375, 768, 1440]) {
  test(`photo and description open details with voice access at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 });
    await expect(page.locator('[data-menu-item]:visible')).toHaveCount(28);
    await expect(page.locator('[data-menu-item] [data-add-item]:disabled')).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Details', exact: true })).toHaveCount(0);
    const item = card(page, 'biryani-chicken');
    for (const target of ['.food-photo', '.menu-description-trigger']) {
      await item.locator(target).click();
      await expect(page.locator('[data-item-dialog]')).toBeVisible();
      await expect(page.locator('[data-detail-name]')).toHaveText('Chicken Biryani');
      await expect(page.locator('[data-item-dialog] [data-voice-launcher]')).toBeVisible();
      await page.keyboard.press('Escape');
    }
    await mkdir(evidence, { recursive: true });
    await item.scrollIntoViewIfNeeded();
    await page.screenshot({ path: `${evidence}/cards-${width}.png` });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  });
  test(`cart moves from navbar to corner and successful Add notifies at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 });
    await expect(page.locator('.site-header [data-cart-trigger]')).toBeVisible();
    await expect(page.locator('[data-menu-category-nav]')).toBeHidden();
    await page.locator('[data-order-manual]').click();
    await expect(page.locator('[data-menu-category-nav]')).toBeVisible();
    await expect(page.locator('body > .is-floating-cart')).toBeVisible();
    await card(page, 'biryani-chicken').locator('[data-add-item]').click();
    await expect(page.locator('[data-cart-count]')).toHaveText('1');
    await expect(page.locator('[data-cart-toast]')).toBeVisible();
    await expect(page.locator('[data-cart-toast]')).toContainText('Chicken Biryani added to cart');
    const [cartBox, voiceBox] = await Promise.all([page.locator('.is-floating-cart').boundingBox(), page.locator('body > [data-voice-launcher]').boundingBox()]);
    expect(voiceBox.y + voiceBox.height + 8 <= cartBox.y).toBe(true);
    await expect(page.locator("[data-floating-cart-quantity]")).toHaveText("1 item");
    await expect(page.locator("[data-floating-cart-total]")).toHaveText("600 PKR");
    await expect(page.locator("[data-floating-cart-quantity]")).toBeVisible();
    await expect(page.locator("[data-floating-cart-total]")).toBeVisible();
    await expect(page.locator("[data-cart-toast-summary]")).toContainText(/1 item .* Total/);
    await page.screenshot({ path: `${evidence}/added-${width}.png` });
    await expect(page.locator('[data-cart-toast]')).toBeHidden({ timeout: 5000 });
    await page.locator('.is-floating-cart').click();
    await expect(page.locator('[data-cart-dialog]')).toBeVisible();
    await page.keyboard.press('Escape');
    await page.evaluate(() => scrollTo({ top: 0, behavior: 'instant' }));
    await expect(page.locator('.site-header [data-cart-trigger]')).toBeVisible();
    await expect(page.locator('.is-floating-cart')).toHaveCount(0);
  });
}

test('category navigation follows scrolling and brings its active pill into view', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await page.locator('[data-order-manual]').click();
  const nav = page.locator('[data-menu-category-nav]');
  await expect(nav.locator('a')).toHaveCount(9);
  await nav.locator('[data-category-jump=wraps]').click();
  await expect(nav.locator('[data-category-jump=wraps]')).toHaveAttribute('aria-current', 'location');
  const group = page.locator('#menu-category-section-wraps');
  await expect.poll(() => group.evaluate(el => el.getBoundingClientRect().top >= document.querySelector('.site-header').getBoundingClientRect().bottom)).toBe(true);
  await page.locator('#menu-category-section-desserts').evaluate(el => el.scrollIntoView({ block:'start', behavior:'instant' }));
  const selected = nav.locator('[data-category-jump=desserts]');
  await expect(selected).toHaveAttribute('aria-current', 'location');
  await expect.poll(async () => {
    const n = await nav.boundingBox(), s = await selected.boundingBox();
    return s.x >= n.x && s.x + s.width <= n.x + n.width + 1;
  }).toBe(true);
  await expect(page.locator('.category-banner')).toHaveCount(9);
});

test('category jumps recover a hidden category without losing the complete catalog', async ({ page }) => {
  await page.locator('[data-category-trigger=burgers]').click();
  await page.locator('#menu-search').fill('Zinger');
  await expect(page.locator('[data-menu-item]:visible')).toHaveCount(2);
  await page.locator('[data-category-jump=wraps]').click();
  await expect(page.locator('[data-menu-item]:visible')).toHaveCount(28);
  await expect(page.locator('#menu-search')).toHaveValue('');
  await card(page, 'burger-soldout').locator('[data-add-item]').click();
  await expect(page.locator('[data-cart-count]')).toHaveText('1');
  await expect(page.locator('[data-cart-toast]')).toContainText('Smoky BBQ Burger added to cart');
});

test('failed Add does not produce a success toast', async ({ page }) => {
  await page.route('**/api/v2/app/action', route => route.request().postDataJSON().payload.operation === 'cart.add_item'
    ? route.fulfill({ status: 503, contentType:'application/json', body:'{}' }) : route.continue());
  await card(page, 'biryani-chicken').locator('[data-add-item]').click();
  await expect(page.locator('[data-order-status]')).toContainText('could not be completed');
  await expect(page.locator('[data-cart-count]')).toHaveText('0');
  await expect(page.locator('[data-cart-toast]')).toBeHidden();
});

test('small original preview is visible while the larger photo is delayed', async ({ page }) => {
  let releaseImages;
  const imagesReady = new Promise(resolve => { releaseImages = resolve; });
  await page.route('**/static/img/catalog-v7/*-480.webp', async route => {
    await imagesReady;
    await route.continue();
  });
  try {
    await page.reload();
    const art = card(page, 'biryani-chicken').locator('.menu-art');
    await art.scrollIntoViewIfNeeded();
    await expect.poll(() => art.locator('.food-photo-preview').evaluate(img => img.complete && img.naturalWidth > 0)).toBe(true);
    await expect(art.locator('.food-photo-preview')).toHaveCSS('opacity', '1');
    releaseImages();
    await expect(art).toHaveAttribute('data-image-state', 'ready');
    expect(await art.locator('.food-photo').evaluate(img => img.naturalWidth)).toBeLessThanOrEqual(480);
  } finally {
    releaseImages();
    await page.unrouteAll({ behavior: 'wait' });
  }
});


test('browsing responds immediately despite a slow authority and dismissed details stay closed', async ({ page }) => {
  let release; const gate = new Promise(resolve => { release = resolve; });
  await page.route('**/api/v2/app/action', async route => { await gate; await route.continue(); });
  try {
    await card(page, 'biryani-chicken').locator('.food-photo').click();
    await expect(page.locator('[data-item-dialog]')).toBeVisible({ timeout: 800 });
    await page.keyboard.press('Escape');
    await page.locator('[data-filter=vegetarian]').click();
    await expect(page.locator('[data-filter=vegetarian]')).toHaveAttribute('aria-pressed', 'true', { timeout: 800 });
    const count = await page.locator('[data-menu-item]:visible').count();
    expect(count).toBeGreaterThan(0); expect(count).toBeLessThan(28);
    release();
    await expect(page.locator('html')).toHaveAttribute('data-foodease-route', 'menu');
    await expect(page.locator('[data-item-dialog]')).toBeHidden();
    await expect(page.locator('[data-filter=vegetarian]')).toHaveAttribute('aria-pressed', 'true');
  } finally { release(); await page.unrouteAll({ behavior: 'wait' }); }
});

test('every filter updates matching dishes and category cards jump to their own heading', async ({ page }) => {
  const catalog = await (await page.request.get('/api/catalog/items')).json();
  for (const filter of ['vegetarian', 'spicy', 'budget', 'available', 'all']) {
    await page.locator(`[data-filter=${filter}]`).click();
    const expected = catalog.items.filter(item => filter === 'all' || (filter === 'budget' ? item.unit_price_pkr <= 800 : filter === 'available' ? item.available : item.tags.includes(filter))).map(item => item.item_id).sort();
    await expect.poll(() => page.locator('[data-menu-item]:visible').evaluateAll(cards => cards.map(card => card.dataset.id).sort())).toEqual(expected);
  }
  await page.locator('[data-category-trigger=wraps]').click();
  await expect.poll(() => page.locator('#menu-category-section-wraps').evaluate(el => Math.abs(el.getBoundingClientRect().top - document.querySelector('.site-header').offsetHeight - 20) < 4)).toBe(true);
  await expect(page.locator('[data-menu-item]:visible')).toHaveCount(28);
});

test('search is centered with a stable prefix and decorative typing never enters the query', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  await page.reload();
  const field = page.locator('.search-field');
  await field.scrollIntoViewIfNeeded();
  const box = await field.boundingBox();
  expect(Math.abs(box.x + box.width / 2 - 720)).toBeLessThan(2);
  await expect(page.locator('.search-prefix')).toHaveText('Search for');
  const first = await page.locator('[data-search-suggestion]').textContent();
  await expect.poll(() => page.locator('[data-search-suggestion]').textContent()).not.toBe(first);
  await expect(page.locator('#menu-search')).toHaveValue('');
  await page.locator('#menu-search').fill('biryani');
  await expect(page.locator('[data-menu-item]:visible')).toHaveCount(2);
  await expect(page.locator('[data-search-suggestion]')).toBeHidden();
});

test('rapid filter choices retain the latest preview until the authority catches up', async ({ page }) => {
  let release; const gate = new Promise(resolve => { release = resolve; });
  await page.route('**/api/v2/app/action', async route => { await gate; await route.continue(); });
  try {
    await page.locator('[data-filter=vegetarian]').click();
    await page.locator('[data-filter=budget]').click();
    await page.locator('[data-filter=spicy]').click();
    await expect(page.locator('[data-filter=spicy]')).toHaveAttribute('aria-pressed', 'true', { timeout: 800 });
    const lastAction = page.waitForResponse(r => r.url().endsWith('/api/v2/app/action') && r.request().postDataJSON().payload.arguments.tags?.[0] === 'spicy');
    release(); await lastAction;
    await expect(page.locator('html')).toHaveAttribute('data-foodease-revision', '4');
    await expect(page.locator('[data-filter=spicy]')).toHaveAttribute('aria-pressed', 'true');
    expect(await page.locator('[data-menu-item]:visible').evaluateAll(cards => cards.every(card => card.dataset.tags.includes('spicy')))).toBe(true);
  } finally { release(); await page.unrouteAll({ behavior: 'wait' }); }
});
