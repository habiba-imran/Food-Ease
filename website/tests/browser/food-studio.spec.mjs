import { test, expect } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
const evidence = '../artifacts/ui-polish-2026-11-07';

test.beforeEach(async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('html')).toHaveAttribute('data-foodease-revision', /\d+/);
  await page.evaluate(() => document.fonts.ready);
});

for (const [width, height] of [[320, 740], [375, 812], [667, 375], [768, 1024], [900, 900], [1024, 768], [1440, 1000], [1920, 1080]]) {
  test(`full hero headline and ordering controls fit ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height });
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await expect(page.locator('#hero-title')).toHaveText('FULL OF FLAVOURS.');
    await expect(page.locator('[data-scene-view], [data-campaign-pause], [data-food-canvas], .studio-control-deck')).toHaveCount(0);
    const geometry = await page.evaluate(() => {
      const box = selector => document.querySelector(selector).getBoundingClientRect().toJSON();
      return { title: box('#hero-title'), photo: box('.hero-product'), hero: box('.hero'), rule: box('.hero-rule'), description: box('.hero-description'),
        overflow: document.documentElement.scrollWidth > innerWidth,
        navOverlap: document.querySelector('.main-nav').getBoundingClientRect().right > document.querySelector('.brand-mark').getBoundingClientRect().left && innerWidth > 700,
        titleOverflow: document.querySelector('#hero-title').scrollWidth > document.querySelector('#hero-title').clientWidth,
      };
    });
    expect(geometry.overflow).toBe(false);
    expect(geometry.navOverlap).toBe(false);
    expect(geometry.titleOverflow).toBe(false);
    expect(geometry.title.bottom).toBeLessThanOrEqual(geometry.photo.top + 2);
    expect(geometry.photo.bottom).toBeLessThanOrEqual(geometry.rule.top);
    if (width <= 700) expect(geometry.photo.bottom).toBeLessThanOrEqual(geometry.description.top);
    await mkdir(evidence, { recursive: true });
    await page.screenshot({ path: `${evidence}/hero-${width}.png`, fullPage: true, clip: { x: geometry.hero.x, y: geometry.hero.y + await page.evaluate(() => scrollY), width: geometry.hero.width, height: geometry.hero.height } });
    await page.locator('[data-order-manual]').click();
    await expect(page.locator('#popular')).toBeInViewport();
    await expect.poll(() => page.locator('#popular').evaluate(el => el.getBoundingClientRect().top >= document.querySelector('.site-header').getBoundingClientRect().bottom - 1)).toBe(true);
    if ([375, 768, 1440].includes(width)) {
      await page.screenshot({ path: `${evidence}/menu-${width}.png` });
    }
    await page.locator('[data-menu-item][data-id="wrap-hot-chicken"] [data-add-item]').click();
    await expect(page.locator('[data-cart-count]')).toHaveText('1');
  });
}

test('desktop float and parallax respect live motion preference changes', async ({ page }) => {
  const hero = page.locator('.hero');
  const product = page.locator('.hero-product');
  await expect(product).toHaveCSS('animation-name', 'hero-object-float');
  await hero.scrollIntoViewIfNeeded();
  const box = await hero.boundingBox();
  await page.mouse.move(box.x + box.width * .7, Math.max(100, box.y + box.height * .4));
  await expect.poll(() => hero.evaluate(el => el.style.getPropertyValue('--scene-x'))).not.toBe('');
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await expect(product).toHaveCSS('animation-name', 'none');
  await expect.poll(() => hero.evaluate(el => el.style.getPropertyValue('--scene-x'))).toBe('');
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  await page.locator('[data-access-toggle=motion]').click();
  await expect(product).toHaveCSS('animation-name', 'none');
});

test('mobile hero stays still and never captures touch rotation', async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 375, height: 812 }, hasTouch: true, isMobile: true });
  try {
    const page = await context.newPage();
    await page.goto('/');
    await expect(page.locator('.hero-product')).toHaveCSS('animation-name', 'none');
    const hero = page.locator('.hero');
    await hero.dispatchEvent('pointerdown', {pointerType:'touch',pointerId:1,clientX:100,clientY:350});
    await hero.dispatchEvent('pointermove', {pointerType:'touch',pointerId:1,clientX:250,clientY:350});
    expect(await hero.evaluate(el => el.style.cssText)).not.toContain('--scene-');
  } finally { await context.close(); }
});

test('all product images load and category selection preserves search and cart', async ({ page }) => {
  const cards = page.locator('[data-menu-item]');
  await expect(cards).toHaveCount(28);
  await page.emulateMedia({ reducedMotion: 'reduce' });
  for (const photo of await page.locator('[data-menu-item] img.food-photo').all()) {
    if (await photo.isVisible()) await photo.scrollIntoViewIfNeeded();
    else await photo.evaluate(img => { img.loading = 'eager'; });
    await expect.poll(() => photo.evaluate(img => img.complete && img.naturalWidth > 0)).toBe(true);
  }
  await page.locator('[data-category-trigger=burgers]').click();
  await expect(page.locator('[data-category-trigger=burgers]')).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('[data-menu-item]:visible').first()).toHaveAttribute('data-category', 'burgers');
  await page.locator('#menu-search').fill('Zinger');
  await expect(page.locator('[data-menu-item]:visible')).toHaveCount(2);
  const add = page.locator('[data-menu-item][data-id="zinger-classic"] [data-add-item]');
  await add.click();
  await expect(add).toHaveClass(/is-added/);
  await expect(page.locator('[data-cart-count]')).toHaveText('1');
  await page.locator('[data-cart-trigger]').click();
  await expect(page.locator('[data-cart-dialog]')).toBeVisible();
});
