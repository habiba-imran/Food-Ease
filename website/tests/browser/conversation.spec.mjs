// Real worker/website/DOM, local fake streaming model; not a model quality campaign.
import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';
const fake = await readFile(new URL('../fake-livekit.mjs', import.meta.url), 'utf8');
test.beforeEach(async ({ page }) => {
  await page.route('**/static/vendor/livekit-client.2.15.4.mjs', r => r.fulfill({ body: fake, contentType: 'text/javascript' }));
  await page.goto('/');
  await expect(page.locator('html')).toHaveAttribute('data-foodease-revision', /\d+/);
  await page.locator('[data-assist-start]').click();
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'typed_active');
});
async function say(page, text) {
  await page.locator('[data-assistant-input]').fill(text);
  await page.locator('[data-assistant-form] button[type=submit]').click();
}
async function snapshot(page) {
  return page.evaluate(async () => (await fetch('/api/v2/app/context', {
    headers: { 'X-FoodEase-Session': sessionStorage.getItem('foodease.shopping-session.v2') },
  })).json());
}
test('read page, presented second item and add button have matching caption and visible effect', async ({ page }) => {
  const initial = await snapshot(page);
  await say(page, 'read this page');
  const transcript = page.locator('[data-agent-transcript]');
  await expect(transcript).toContainText('home page');
  await expect(transcript).toContainText(initial.visible_items[1].name);
  await say(page, 'open the second one');
  await expect(page.locator('[data-item-dialog]')).toBeVisible();
  await expect(page.locator('[data-detail-name]')).toHaveText(initial.visible_items[1].name);
  await say(page, 'press add to cart');
  await expect(page.locator('[data-cart-count]')).toHaveText('1');
  await expect(transcript).toContainText('The total is');
  expect((await snapshot(page)).cart.lines[0].item_id).toBe(initial.visible_items[1].item_id);
});
test('manual context change requires clarification for an old ordinal without a select action', async ({ page }) => {
  await say(page, 'read the page');
  await expect(page.locator('[data-agent-transcript]')).toContainText('First:');
  await page.locator('#menu-search').fill('wrap');
  await expect(page.locator('html')).toHaveAttribute('data-foodease-route', 'menu');
  await say(page, 'open the second one');
  await expect(page.locator('[data-agent-transcript]')).toContainText('Which item do you mean');
  await expect(page.locator('[data-item-dialog]')).not.toBeVisible();
  expect(await page.evaluate(() => window.fakeLiveKit.rpcCalls.filter(r => r.operation === 'select_item').length)).toBe(0);
});
test('next and previous deliver small actual windows with stable ordinal identity', async ({ page }) => {
  const initial = await snapshot(page);
  await say(page, 'read the page');
  await expect(page.locator('[data-agent-transcript]')).toContainText(initial.visible_items[2].name);
  await say(page, 'next please');
  await expect(page.locator('[data-agent-transcript]')).toContainText(initial.visible_items[5].name);
  await say(page, 'previous');
  await expect.poll(() => page.locator('[data-agent-transcript] > p').last().textContent()).toContain(initial.visible_items[0].name);
  await say(page, 'open the third one');
  await expect(page.locator('[data-detail-name]')).toHaveText(initial.visible_items[2].name);
});
test('actual model/tool pipeline refines filters and completes ordered combined tools', async ({ page }) => {
  await say(page, 'show spicy food under 950');
  await expect.poll(async () => (await snapshot(page)).max_price_pkr).toBe(950);
  await say(page, 'actually under 600');
  await expect.poll(async () => (await snapshot(page)).max_price_pkr).toBe(600);
  expect((await snapshot(page)).filter_tags).toContain('spicy');
  await page.locator('[data-filter="all"]').click();
  await expect.poll(async () => (await snapshot(page)).filter_tags.length).toBe(0);
  await say(page, 'find burgers then add one veggie burger');
  await expect(page.locator('[data-cart-count]')).toHaveText('1');
  expect((await snapshot(page)).cart.lines[0].item_id).toBe('burger-veg');
  const operations = await page.evaluate(() => window.fakeLiveKit.rpcCalls.map(r => r.operation).filter(Boolean));
  expect(operations.lastIndexOf('cart.add_item')).toBeGreaterThan(operations.lastIndexOf('search_menu'));
});
test('quantity correction sets the latest cart instead of adding again', async ({ page }) => {
  await say(page, 'add two Hot Chicken Wraps');
  await expect(page.locator('[data-cart-count]')).toHaveText('2');
  await say(page, 'actually make it one');
  await expect(page.locator('[data-cart-count]')).toHaveText('1');
  const operations = await page.evaluate(() => window.fakeLiveKit.rpcCalls.map(r => r.operation));
  expect(operations.filter(op => op === 'cart.add_item')).toHaveLength(1);
  expect(operations.filter(op => op === 'cart.set_quantity')).toHaveLength(1);
});
