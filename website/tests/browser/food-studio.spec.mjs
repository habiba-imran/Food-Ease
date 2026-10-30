import { test, expect } from '@playwright/test';

test.use({ launchOptions: { args: ['--enable-unsafe-swiftshader'] } });

async function ready(page) {
  await page.goto('/');
  await expect(page.locator('html')).toHaveAttribute('data-foodease-revision', /\d+/);
  await page.locator('[data-scene-view=inspect]').click();
  await expect(page.locator('[data-food-studio]')).toHaveAttribute('data-render-state', 'ready');
}

test('real rendered model rotates, pauses, separates layers, and responds to drag', async ({ page }) => {
  await ready(page);
  const studio = page.locator('[data-food-studio]');
  const canvas = page.locator('[data-food-canvas]');
  await expect.poll(async () => Number(await studio.getAttribute('data-rotation'))).not.toBe(-.6);
  await page.locator('[data-studio-pause]').click();
  await expect(studio).toHaveAttribute('data-motion', 'paused');
  await page.locator('[data-studio-explode]').click();
  await expect.poll(async () => Number(await studio.getAttribute('data-layer-spread'))).toBeGreaterThan(.98);
  await page.locator('[data-studio-explode]').click();
  await expect.poll(async () => Number(await studio.getAttribute('data-layer-spread'))).toBeLessThan(.02);
  const box = await canvas.boundingBox();
  const before = Number(await studio.getAttribute('data-rotation'));
  await page.mouse.move(box.x + box.width * .4, box.y + box.height * .5);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * .7, box.y + box.height * .5, { steps: 12 });
  await page.mouse.up();
  await expect(studio).toHaveAttribute('data-dragged', 'true');
  await expect.poll(async () => Number(await studio.getAttribute('data-rotation'))).toBeGreaterThan(before + .3);
});

test('reduced motion stops automatic 3D rotation but keeps keyboard controls usable', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await ready(page);
  const studio = page.locator('[data-food-studio]');
  await expect(studio).toHaveAttribute('data-motion', 'paused');
  await expect.poll(() => studio.getAttribute('data-rotation')).toBe('-0.600');
  await page.locator('[data-food-canvas]').focus();
  await page.keyboard.press('ArrowRight');
  await expect.poll(async () => Number(await studio.getAttribute('data-rotation'))).toBeGreaterThan(-.1);
  await page.locator('[data-studio-explode]').click();
  await expect(studio).toHaveAttribute('data-layer-spread', '1.000');
  await expect(page.locator('[data-cart-count]')).toHaveText('0');
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'awaiting_spoken_choice_consent');
});

test('the scene stops rendering offscreen and resumes on return', async ({ page }) => {
  await ready(page);
  const studio = page.locator('[data-food-studio]');
  await page.locator('#assistant').evaluate(el => el.scrollIntoView({ block: 'start', behavior: 'instant' }));
  await page.waitForTimeout(250);
  const stopped = await studio.getAttribute('data-rotation');
  await page.waitForTimeout(250);
  expect(await studio.getAttribute('data-rotation')).toBe(stopped);
  await studio.scrollIntoViewIfNeeded();
  await expect.poll(() => studio.getAttribute('data-rotation')).not.toBe(stopped);
});

test('missing WebGL falls back without preventing manual ordering', async ({ browser }) => {
  const context = await browser.newContext();
  const page = await context.newPage();
  try {
    await page.addInitScript(() => {
      const original = HTMLCanvasElement.prototype.getContext;
      HTMLCanvasElement.prototype.getContext = function(type, ...args) {
        if (String(type).includes('webgl')) return null;
        return original.call(this, type, ...args);
      };
    });
    await page.goto('/');
    await page.locator('[data-scene-view=inspect]').click();
    await expect(page.locator('[data-food-studio]')).toHaveAttribute('data-render-state', 'fallback');
    await expect(page.locator('.studio-fallback')).toBeVisible();
    await page.locator('[data-menu-item][data-id="wrap-hot-chicken"] [data-add-item]').click();
    await expect(page.locator('[data-cart-count]')).toHaveText('1');
  } finally { await context.close(); }
});

for (const width of [320, 375, 768, 1000, 1440]) {
  test(`assistant and 3D controls fit ${width}px including direct assistant links`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/#assistant');
    await expect(page.locator('html')).toHaveAttribute('data-foodease-revision', /\d+/);
    await expect(page.locator('#assistant')).toBeInViewport();
    await expect.poll(() => page.evaluate(() => document.querySelector('#assistant').getBoundingClientRect().top >= document.querySelector('.site-header').getBoundingClientRect().bottom - 1)).toBe(true);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
    await page.locator('[data-scene-view=inspect]').click();
    await expect(page.locator('[data-food-studio]')).toHaveAttribute('data-scene-mode', 'inspect');
    const controls = await page.locator('#assistant button, #assistant input:not([type=checkbox]), .studio-control-deck button, .studio-control-deck input').evaluateAll(elements => elements.map(el => {
      const r = el.getBoundingClientRect(); return { left: r.left, right: r.right, width: r.width };
    }));
    for (const control of controls) {
      expect(control.left).toBeGreaterThanOrEqual(0);
      expect(control.right).toBeLessThanOrEqual(width);
      expect(control.width).toBeGreaterThan(25);
    }
  });
}
