// Uses the real website authority. No paid provider or real order/payment.
import { test, expect } from '@playwright/test';
import { mkdir } from 'node:fs/promises';

const card = (page, id) => page.locator(`[data-menu-item][data-id="${id}"]`);
const cart = page => page.locator('[data-cart-dialog]');
const row = (page, id) => cart(page).locator(`[data-item-id="${id}"]`);
const evidence = process.env.FOODEASE_UI_EVIDENCE || 'docs/ui-audit-evidence';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.manualMediaRequests = 0;
    navigator.mediaDevices.getUserMedia = async () => { window.manualMediaRequests++; throw new Error('Unexpected microphone capture'); };
  });
  await page.goto('/');
  await expect(page.locator('html')).toHaveAttribute('data-foodease-revision', /\d+/);
  await page.emulateMedia({ reducedMotion: 'reduce' });
});

for (const [width, height, label] of [[1440, 1000, 'desktop'], [768, 1024, 'tablet'], [375, 812, 'mobile']]) {
  test(`complete manual order and dialog focus at ${label}`, async ({ page }) => {
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.setViewportSize({ width, height });
    await page.locator('[data-order-manual]').click();
    await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'manual');
    await page.locator('[data-category-trigger="wraps"]').click();
    await expect(page.locator('[data-menu-item]:visible')).toHaveCount(28);
    const trigger = card(page, 'wrap-hot-chicken').locator('[data-detail-item]');
    await trigger.click();
    await expect(page.getByRole('dialog', { name: 'Hot Chicken Wrap', exact: true })).toBeVisible();
    await expect(page.locator('[data-detail-close]')).toBeFocused();
    await page.locator('[data-detail-quantity]').fill('2');
    await expect(page.locator('[data-detail-total]')).toHaveText('1700 PKR');
    await mkdir(evidence, { recursive: true });
    await page.screenshot({ path: `${evidence}/${label}-details.png` });
    await page.locator('[data-detail-add]').click();
    await expect(page.locator('[data-item-dialog]')).toBeHidden();
    await expect(trigger).toBeFocused();
    await expect(page.locator('[data-cart-count]')).toHaveText('2');
    await page.locator('[data-filter="all"]').click();
    await card(page, 'drink-cola').locator('[data-add-item]').click();
    await expect(page.locator('[data-cart-count]')).toHaveText('3');
    await page.locator('[data-cart-trigger]').click();
    await expect(page.getByRole('dialog', { name: 'YOUR ORDER.' })).toBeVisible();
    await expect(page.locator('[data-cart-close]')).toBeFocused();
    await expect(page.locator('[data-cart-subtotal]')).toHaveText('1800 PKR');
    await expect(page.locator('[data-cart-fee]')).toHaveText('50 PKR');
    await expect(page.locator('[data-cart-total]')).toHaveText('1850 PKR');
    await row(page, 'wrap-hot-chicken').getByRole('button', { name: 'Increase Hot Chicken Wrap' }).click();
    await expect(page.locator('[data-cart-count]')).toHaveText('4');
    await expect(row(page, 'wrap-hot-chicken').getByRole('button', { name: 'Increase Hot Chicken Wrap' })).toBeFocused();
    await row(page, 'wrap-hot-chicken').getByRole('button', { name: /^Decrease/ }).click();
    await expect(page.locator('[data-cart-count]')).toHaveText('3');
    await row(page, 'drink-cola').getByRole('button', { name: /^Remove/ }).click();
    await expect(row(page, 'drink-cola')).toHaveCount(0);
    expect(await cart(page).evaluate(el => el.contains(document.activeElement))).toBe(true);
    await expect(page.locator('[data-cart-total]')).toHaveText('1750 PKR');
    await page.screenshot({ path: `${evidence}/${label}-cart.png` });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    expect(await cart(page).evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true);
    await page.locator('[data-checkout-button]').click();
    await expect(cart(page)).toBeHidden();
    await expect(page.getByRole('dialog', { name: 'Review your demo order' })).toBeVisible();
    await expect(page.locator('[data-checkout-total]')).toHaveText('1750 PKR');
    await page.screenshot({ path: `${evidence}/${label}-checkout.png` });
    await page.locator('[data-confirm-order]').click();
    await expect(page.locator('[data-receipt-id]')).toHaveText(/^DEMO-/);
    await expect(page.locator('[data-receipt-id]')).toBeFocused();
    await expect(page.locator('[data-receipt-summary]')).toContainText('No payment was collected');
    await expect(page.locator('[data-cart-count]')).toHaveText('0');
    const receipt = await page.locator('[data-receipt-id]').textContent();
    await page.reload();
    await expect(page.locator('[data-receipt-id]')).toHaveText(receipt);
    await page.locator('[data-receipt-close]').click();
    await expect(page.locator('[data-checkout-dialog]')).toBeHidden();
    expect(await page.evaluate(() => window.manualMediaRequests)).toBe(0);
    expect(errors).toEqual([]);
  });
}

test('invalid quantity is explained without silently changing or adding an item', async ({ page }) => {
  await card(page, 'wrap-hot-chicken').locator('[data-detail-item]').click();
  for (const value of ['', '0', '13', '1.5', '-1']) {
    await page.locator('[data-detail-quantity]').fill(value);
    await page.locator('[data-detail-add]').click();
    await expect(page.locator('#quantity-error')).toHaveText('Enter a whole number from 1 to 12.');
    await expect(page.locator('[data-detail-quantity]')).toHaveAttribute('aria-invalid', 'true');
    await expect(page.locator('[data-detail-quantity]')).toBeFocused();
    await expect(page.locator('[data-cart-count]')).toHaveText('0');
  }
  await page.locator('[data-detail-quantity]').fill('12');
  await expect(page.locator('#quantity-error')).toBeHidden();
  await expect(page.locator('[data-detail-total]')).toHaveText('10200 PKR');
  await page.locator('[data-detail-add]').click();
  await expect(page.locator('[data-cart-count]')).toHaveText('12');
});

test('empty cart, Escape, native focus containment and background scroll lock', async ({ page }) => {
  const trigger = page.locator('[data-cart-trigger]');
  await trigger.click();
  await expect(cart(page).getByRole('heading', { name: 'Your cart is empty' })).toBeVisible();
  await expect(page.locator('[data-checkout-button]')).toBeDisabled();
  await expect(page.locator('html')).toHaveCSS('overflow', 'hidden');
  for (let i = 0; i < 8; i++) {
    await page.keyboard.press('Tab');
    expect(await cart(page).evaluate(el => el.contains(document.activeElement) || document.activeElement === document.body)).toBe(true);
  }
  await page.keyboard.press('Escape');
  await expect(cart(page)).toBeHidden();
  await expect(trigger).toBeFocused();
  await expect(trigger).toHaveAttribute('aria-expanded', 'false');
  await expect(page.locator('html')).not.toHaveCSS('overflow', 'hidden');
  await trigger.click();
  await cart(page).getByRole('button', { name: 'Explore menu' }).click();
  await expect(cart(page)).toBeHidden();
  await expect(page.locator('#popular')).toBeFocused();
});

test('cart and edit links each issue one navigation action', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await card(page, 'drink-cola').locator('[data-add-item]').click();
  await expect(page.locator('[data-cart-count]')).toHaveText('1');
  const navigation = [];
  page.on('request', request => {
    if (request.url().endsWith('/api/v2/app/action') && request.postDataJSON()?.payload.operation === 'navigate') navigation.push(request.postDataJSON().payload.arguments.target);
  });
  await test.step('open floating cart', async () => { await page.locator('.is-floating-cart').click(); });
  await expect(page.locator('html')).toHaveAttribute('data-foodease-route', 'cart');
  expect(navigation).toEqual(['cart']);
  await test.step('review checkout', async () => { await page.locator('[data-checkout-button]').click(); });
  await test.step('edit cart from checkout', async () => { await page.locator('[data-edit-cart]').click(); });
  await expect(cart(page)).toBeVisible();
  await expect(page.locator('html')).toHaveAttribute('data-foodease-route', 'cart');
  expect(navigation).toEqual(['cart', 'cart']);
});

test('pending cart updates and confirmation clicks cannot double submit', async ({ page }) => {
  await card(page, 'drink-cola').locator('[data-add-item]').click();
  await expect(page.locator('[data-cart-count]')).toHaveText('1');
  await page.locator('[data-cart-trigger]').click();
  const writes = [];
  await page.route('**/api/v2/app/action', async route => {
    const operation = route.request().postDataJSON().payload.operation;
    writes.push(operation);
    if (['cart.set_quantity', 'checkout.submit_demo_order'].includes(operation)) await new Promise(resolve => setTimeout(resolve, 250));
    await route.continue();
  });
  await row(page, 'drink-cola').getByRole('button', { name: 'Increase Cola Can' }).dblclick();
  await expect(page.locator('[data-cart-count]')).toHaveText('2');
  expect(writes.filter(op => op === 'cart.set_quantity')).toHaveLength(1);
  await page.locator('[data-checkout-button]').click();
  await expect(page.locator('[data-confirm-order]')).toBeEnabled();
  await page.locator('[data-confirm-order]').evaluate(button => { button.click(); button.click(); });
  await expect(page.locator('[data-receipt-panel]')).toBeVisible();
  expect(writes.filter(op => op === 'checkout.submit_demo_order')).toHaveLength(1);
});

test('failed checkout stays actionable, never shows a receipt, and Escape still closes', async ({ page }) => {
  await card(page, 'drink-cola').locator('[data-add-item]').click();
  await page.locator('[data-cart-trigger]').click();
  await expect(page.locator('html')).toHaveAttribute('data-foodease-route', 'cart');
  await page.route('**/api/v2/app/action', route => route.abort());
  await page.locator('[data-checkout-button]').click();
  await expect(cart(page).getByRole('status')).toContainText('unknown');
  await expect(cart(page).getByRole('button', { name: 'Check pending changes' })).toBeVisible();
  await expect(page.locator('[data-receipt-panel]')).toBeHidden();
  await expect(page.locator('[data-cart-count]')).toHaveText('1');
  await page.keyboard.press('Escape');
  await expect(cart(page)).toBeHidden();
  await expect(page.locator('[data-cart-trigger]')).toBeFocused();
});

test('multiple real products scroll inside cart with reachable totals and full names', async ({ page }) => {
  test.setTimeout(60000);
  await page.setViewportSize({ width: 375, height: 812 });
  const buttons = page.locator('[data-menu-item] [data-add-item]:enabled');
  for (let i = 0; i < 10; i++) {
    await buttons.nth(i).click();
    await expect(page.locator('[data-cart-count]')).toHaveText(String(i + 1));
  }
  await page.locator('[data-cart-trigger]').click();
  expect(await cart(page).evaluate(el => el.scrollHeight > el.clientHeight)).toBe(true);
  await page.locator('[data-checkout-button]').scrollIntoViewIfNeeded();
  await expect(page.locator('[data-checkout-button]')).toBeInViewport();
  await expect(page.locator('[data-cart-close]')).toBeInViewport();
  expect(await cart(page).evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true);
  await page.screenshot({ path: `${evidence}/mobile-many-items.png` });
  await page.keyboard.press('Escape');
  await page.reload();
  await expect(page.locator('[data-cart-count]')).toHaveText('10');
});

async function tabTo(page, selector) {
  for (let i = 0; i < 200; i++) {
    if (await page.locator(selector).evaluate(el => el === document.activeElement)) return;
    await page.keyboard.press('Tab');
  }
  throw new Error(`Keyboard could not reach ${selector}`);
}

test('complete manual demo with Tab, Enter, number keys and Escape only', async ({ page }) => {
  test.setTimeout(60000);
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: 'Skip to menu' })).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.locator('#popular')).toBeFocused();
  await tabTo(page, '[data-menu-item][data-id="biryani-chicken"] [data-detail-item]');
  await page.keyboard.press('Enter');
  await expect(page.locator('[data-detail-close]')).toBeFocused();
  await tabTo(page, '[data-detail-quantity]');
  await page.keyboard.press('Control+A');
  await page.keyboard.type('2');
  await page.keyboard.press('Tab');
  await expect(page.locator('[data-detail-add]')).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.locator('[data-cart-count]')).toHaveText('2');
  await tabTo(page, '[data-cart-trigger]');
  await page.keyboard.press('Enter');
  await tabTo(page, '[data-checkout-button]');
  await page.keyboard.press('Enter');
  await tabTo(page, '[data-confirm-order]');
  await page.keyboard.press('Enter');
  await expect(page.locator('[data-receipt-id]')).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(page.locator('dialog[open]')).toHaveCount(0);
});

test('accessible names, quantity description, headings and available dish semantics', async ({ page }) => {
  await card(page, 'burger-soldout').locator('[data-detail-item]').click();
  await expect(page.locator('[data-detail-add]')).toBeEnabled();
  await expect(page.locator('[data-detail-quantity]')).toBeEnabled();
  await expect(page.locator('[data-detail-availability]')).toHaveText('Available now');
  await page.keyboard.press('Escape');
  await card(page, 'wrap-hot-chicken').locator('[data-detail-item]').click();
  await expect(page.getByRole('spinbutton', { name: 'Quantity' })).toHaveAccessibleDescription('Choose 1–12 per addition. This dish is served as listed.');
  const snapshot = await page.locator('[data-item-dialog]').ariaSnapshot();
  expect(snapshot).toContain('dialog "Hot Chicken Wrap"');
  expect(snapshot).toContain('button "Close item details"');
  await page.keyboard.press('Escape');
  const headings = await page.locator('#popular h2, #popular h3, #popular h4').evaluateAll(elements => elements.map(el => Number(el.tagName[1])));
  expect(headings[0]).toBe(2);
  expect(headings[1]).toBe(3);
  expect(headings[2]).toBe(4);
});

test('repeat additions merge correctly and enforce the authoritative quantity ceiling', async ({ page }) => {
  test.setTimeout(60000);
  for (let i = 0; i < 9; i++) {
    await card(page, 'drink-cola').locator('[data-detail-item]').click();
    await expect(page.locator('[data-item-dialog]')).toBeVisible();
    await page.locator('[data-detail-quantity]').fill(i === 8 ? '2' : '12');
    await page.locator('[data-detail-add]').click();
    await expect(page.locator('[data-item-dialog]')).toBeHidden();
  }
  await expect(page.locator('[data-cart-count]')).toHaveText('98');
  await page.locator('[data-cart-trigger]').click();
  await row(page, 'drink-cola').getByRole('button', { name: 'Increase Cola Can' }).click();
  await expect(page.locator('[data-cart-count]')).toHaveText('99');
  await expect(row(page, 'drink-cola').getByRole('button', { name: 'Decrease Cola Can' })).toBeFocused();
  await expect(cart(page).locator('.cart-line')).toHaveCount(1);
  await expect(row(page, 'drink-cola').getByRole('button', { name: 'Increase Cola Can' })).toBeDisabled();
  await expect(page.locator('[data-cart-total]')).toHaveText('9950 PKR');
  await page.keyboard.press('Escape');
  await card(page, 'drink-cola').locator('[data-add-item]').click();
  await expect(page.locator('[data-order-status]')).toContainText('up to 99');
  await expect(page.locator('[data-cart-count]')).toHaveText('99');
});
