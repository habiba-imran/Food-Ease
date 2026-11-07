import { test, expect } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
const evidence = process.env.FOODEASE_UI_EVIDENCE || '../artifacts/ui-polish-2026-11-07';

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
        carousel: box('.hero-carousel-window'), controls: box('.hero-carousel-controls'),
      };
    });
    expect(geometry.overflow).toBe(false);
    expect(geometry.navOverlap).toBe(false);
    expect(geometry.titleOverflow).toBe(false);
    expect(geometry.carousel.bottom + 12).toBeLessThanOrEqual(geometry.description.top);
    expect(geometry.controls.top).toBeGreaterThanOrEqual(geometry.title.bottom);
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

test('food strip moves left, stops on hover, resumes, and loops without a visible seam', async ({ page }) => {
  const carousel = page.locator('[data-hero-carousel]'), track = page.locator('[data-hero-track]');
  await carousel.scrollIntoViewIfNeeded();
  const x = () => track.evaluate(el => new DOMMatrix(getComputedStyle(el).transform).m41);
  const initial = await x(); await expect.poll(x).toBeLessThan(initial - 8);
  await carousel.hover(); await expect(carousel).toHaveAttribute('data-paused', 'true');
  const frozen = await x(); await page.waitForTimeout(250); expect(Math.abs(await x() - frozen)).toBeLessThan(.1);
  await page.mouse.move(5, 5); await expect(carousel).toHaveAttribute('data-paused', 'false');
  await expect.poll(x).toBeLessThan(frozen - 8);
  const seam = await track.evaluate(el => {
    const a = el.getAnimations()[0], duration = a.effect.getTiming().duration; a.pause();
    const nearest = () => [...el.querySelectorAll('img')].map(img => { const r = img.getBoundingClientRect(); return {src: img.getAttribute('src'), x:r.x+r.width/2}; }).sort((a,b)=>Math.abs(a.x-innerWidth/2)-Math.abs(b.x-innerWidth/2))[0];
    a.currentTime=duration-20; const before=nearest(); a.currentTime=duration+20; return {before, after:nearest()};
  });
  expect(seam.before.src).toBe(seam.after.src); expect(Math.abs(seam.before.x-seam.after.x)).toBeLessThan(3);
});

test('reduced motion keeps the strip still and keyboard controls explore all six dishes', async ({ page }) => {
  await page.emulateMedia({ reducedMotion:'reduce' });
  const carousel=page.locator('[data-hero-carousel]'), track=page.locator('[data-hero-track]');
  await carousel.scrollIntoViewIfNeeded(); await expect(carousel).toHaveAttribute('data-paused','true');
  await expect(page.locator('[data-hero-food-pause]')).toBeHidden();
  await page.keyboard.press('Tab'); const next=page.locator('[data-hero-food-next]'); await next.focus();
  const sources=[];
  for(let i=0;i<6;i++) {
    sources.push(await track.evaluate(el=>[...el.querySelectorAll('img')].map(img=>{const r=img.getBoundingClientRect();return{src:img.getAttribute('src'),d:Math.abs(r.x+r.width/2-innerWidth/2)}}).sort((a,b)=>a.d-b.d)[0].src));
    await expect.poll(() => track.evaluate(el => {
      const images=[...el.querySelectorAll('img')].sort((a,b)=>{ const x=a.getBoundingClientRect(),y=b.getBoundingClientRect();return Math.abs(x.x+x.width/2-innerWidth/2)-Math.abs(y.x+y.width/2-innerWidth/2); });
      return images[0].complete && images[0].naturalWidth > 0;
    })).toBe(true);
    await page.locator('.hero').screenshot({ path: `${evidence}/dish-${i}.png` });
    await page.keyboard.press('Enter');
  }
  expect(new Set(sources).size).toBe(6); await expect(next).toBeFocused();
  const time=await track.evaluate(el=>el.getAnimations()[0].currentTime); await page.waitForTimeout(200);
  expect(await track.evaluate(el=>el.getAnimations()[0].currentTime)).toBe(time);
  await page.emulateMedia({reducedMotion:'no-preference'}); await page.locator('[data-access-toggle=motion]').click();
  await expect(carousel).toHaveAttribute('data-paused','true');
});

test('touch controls pause and resume without capturing vertical gestures', async ({ browser }) => {
  const context=await browser.newContext({viewport:{width:375,height:812},hasTouch:true,isMobile:true});
  try {
    const page=await context.newPage();await page.goto('/'); const carousel=page.locator('[data-hero-carousel]');
    await carousel.scrollIntoViewIfNeeded(); await expect(carousel).toHaveAttribute('data-paused','false');
    const pause=page.locator('[data-hero-food-pause]');await pause.tap();await expect(pause).toHaveAttribute('aria-pressed','true');
    await expect(carousel).toHaveAttribute('data-paused','true');await pause.tap();await page.locator('#hero-title').tap();
    await expect(carousel).toHaveAttribute('data-paused','false');
    expect(await carousel.evaluate(el=>getComputedStyle(el).touchAction)).toBe('auto');
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  } finally {await context.close();}
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
  await expect(page.locator('[data-menu-item]:visible')).toHaveCount(28);
  await expect(page.locator('[data-category-jump=burgers]')).toHaveAttribute('aria-current', 'location');
  await page.locator('#menu-search').fill('Zinger');
  await expect(page.locator('[data-menu-item]:visible')).toHaveCount(2);
  const add = page.locator('[data-menu-item][data-id="zinger-classic"] [data-add-item]');
  await add.click();
  await expect(add).toHaveClass(/is-added/);
  await expect(page.locator('[data-cart-count]')).toHaveText('1');
  await page.locator('[data-cart-trigger]').click();
  await expect(page.locator('[data-cart-dialog]')).toBeVisible();
});
