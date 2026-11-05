import { test, expect } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('html')).toHaveAttribute('data-foodease-revision', /\d+/);
});

for (const [width, height] of [[375, 812], [667, 375], [768, 1024], [1024, 768], [1440, 1000]]) {
  test(`ordering remains readable and usable at ${width} by ${height}`, async ({ page }) => {
    await page.setViewportSize({ width, height });
    await page.evaluate(() => scrollTo({ top: 0, behavior: 'instant' }));
    expect(await page.locator('.site-header').evaluate(el => el.getBoundingClientRect().top)).toBe(0);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    const targets = page.locator('.main-nav a, .menu-card:not(.is-hidden) [data-add-item]');
    for (const box of await targets.evaluateAll(elements => elements.map(el => {
      const r = el.getBoundingClientRect(); return { left: r.left, right: r.right };
    }))) {
      expect(box.left).toBeGreaterThanOrEqual(0);
      expect(box.right).toBeLessThanOrEqual(width);
    }
    await page.locator('[data-menu-item][data-id="wrap-hot-chicken"] [data-detail-item]').click();
    await expect(page.locator('[data-item-dialog]')).toBeVisible();
    await page.locator('[data-detail-add]').scrollIntoViewIfNeeded();
    await expect(page.locator('[data-detail-add]')).toBeInViewport();
    await page.keyboard.press('Escape');
    await expect(page.locator('[data-item-dialog]')).not.toBeVisible();
  });
}

test('dark mobile browsing preserves filters, selection, and checkout', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.locator('[data-header-theme]').click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.locator('[data-filter=vegetarian]').click();
  await expect(page.locator('[data-menu-item][data-id="wrap-hot-chicken"]')).toBeHidden();
  await page.locator('[data-filter=all]').click();
  const add = page.locator('[data-menu-item][data-id="wrap-hot-chicken"] [data-add-item]');
  await add.click();
  await expect(page.locator('[data-cart-count]')).toHaveText('1');
  await page.locator('[data-cart-trigger]').click();
  await page.locator('[data-checkout-button]').click();
  await expect(page.locator('[data-confirm-order]')).toBeVisible();
  await expect(page.locator('[data-checkout-dialog] .assistant-controls')).toHaveCount(0);
  await expect(page.locator('[data-checkout-dialog] [data-assistant-form]')).toHaveCount(0);
  await expect(page.locator('.mobile-cart-link')).toBeHidden();
  await page.keyboard.press('Escape');
  await expect(page.locator('[data-checkout-dialog]')).not.toBeVisible();
});

test('popular item picks open focused details without exposing demo controls', async ({ page }) => {
  let starts = 0;
  page.on('request', request => { if (request.url().endsWith('/v2/assist/start')) starts++; });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.locator('[data-preview-item="zinger-classic"]').click();
  await expect(page.locator('[data-detail-name]')).toHaveText('Zinger Burger');
  await expect(page.locator('.hero-food-rail button')).toHaveCount(4);
  await expect(page.locator('[data-item-dialog]')).toBeVisible();
  await expect(page.locator('[data-item-dialog] .assistant-controls')).toHaveCount(0);
  await expect(page.locator('[data-item-dialog] [data-assistant-form]')).toHaveCount(0);
  await page.keyboard.press('Escape');
  await expect(page.locator('#assistant')).toBeHidden();
  await page.locator('.main-nav a[href="#assistant"]').click();
  await expect(page.locator('#project-details')).toHaveAttribute('open', '');
  await expect(page.locator('#assistant')).toBeVisible();
  expect(starts).toBe(0);
});

test('larger text and contrast preserve the mobile ordering path', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  const heading = page.locator('.menu-card h4').first();
  const before = await heading.evaluate(el => parseFloat(getComputedStyle(el).fontSize));
  await page.locator('[data-access-toggle=large]').click();
  expect(await heading.evaluate(el => parseFloat(getComputedStyle(el).fontSize))).toBeGreaterThan(before);
  await page.locator('[data-access-toggle=contrast]').click();
  await expect(page.locator('[data-access-toggle=contrast]')).toHaveAttribute('aria-pressed', 'true');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.locator('[data-menu-item][data-id="wrap-hot-chicken"] [data-add-item]').click();
  await expect(page.locator('[data-cart-count]')).toHaveText('1');
});

test('desktop navigation and checkout remain reachable while browsing a long menu', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.locator('[data-menu-item][data-id="wrap-hot-chicken"] [data-add-item]').click();
  await expect(page.locator('[data-checkout-button]')).toBeEnabled();
  await page.evaluate(() => {
    const top = document.querySelector('#popular').getBoundingClientRect().top + scrollY;
    scrollTo({ top: top + 900, behavior: 'instant' });
  });
  await expect(page.locator('[data-cart-trigger]')).toBeInViewport();
  await expect(page.locator('[data-header-theme]')).toBeInViewport();
  expect(await page.locator('.site-header').evaluate(el => el.getBoundingClientRect().top)).toBe(0);
  await page.locator('[data-cart-trigger]').click();
  await expect(page.locator('[data-checkout-button]')).toBeInViewport();
});

test('lower-page copy reveals on scroll and motion preferences keep it readable', async ({ page }) => {
  await page.locator('#project-details > summary').click();
  const heading = page.locator('#ar-title');
  await expect(heading).toHaveCSS('opacity', '0');
  await heading.scrollIntoViewIfNeeded();
  await expect(heading).toHaveCSS('opacity', '1');
  await expect(heading).toBeInViewport();
  await page.locator('[data-access-toggle=motion]').click();
  await expect(page.locator('.footer-wordmark')).toHaveCSS('opacity', '1');
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.reload();
  await expect(page.locator('#ar-title')).toHaveCSS('opacity', '1');
  await expect(page.locator('.footer-wordmark')).toHaveCSS('opacity', '1');
});
