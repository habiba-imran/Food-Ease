// Local, reproducible rendering/semantics/solid-color contrast checks.
// This is not a substitute for a human screen-reader or WCAG conformance audit.
import { chromium } from 'playwright';
import { mkdir, writeFile } from 'node:fs/promises';

const base = process.argv[2] || 'http://127.0.0.1:8186';
const output = process.argv[3] || 'docs/ui-audit-evidence';
await mkdir(output, { recursive: true });
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
const errors = [];
page.on('pageerror', error => errors.push(error.message));
page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
page.on('response', response => { if (response.url().includes('/static/') && response.status() >= 400) errors.push(`Asset HTTP ${response.status()}: ${response.url()}`); });
const report = { base, checks: [], consoleErrors: errors, limits: 'Computed solid-color text pairs only; excludes gradients, images, transparency effects and disabled controls. Native accessibility snapshots are not human screen-reader testing.' };

async function inspect(label, selector) {
  const surface = page.locator(selector);
  const results = await surface.evaluate(root => {
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = 1;
    const context = canvas.getContext('2d', { willReadFrequently: true });
    function rgba(color) {
      context.clearRect(0, 0, 1, 1);
      context.fillStyle = color;
      context.fillRect(0, 0, 1, 1);
      return [...context.getImageData(0, 0, 1, 1).data].map((value, i) => i === 3 ? value / 255 : value);
    }
    function background(element) {
      if (!element) return [255, 255, 255, 1];
      const style = getComputedStyle(element);
      if (style.backgroundImage !== 'none') return null;
      const color = rgba(style.backgroundColor);
      if (color[3] === 1) return color;
      const parent = background(element.parentElement);
      if (!parent) return null;
      return color.slice(0, 3).map((c, i) => c * color[3] + parent[i] * (1 - color[3])).concat(1);
    }
    function luminance(color) {
      return color.slice(0, 3).map(c => { c /= 255; return c <= .04045 ? c / 12.92 : ((c + .055) / 1.055) ** 2.4; })
        .reduce((sum, c, i) => sum + c * [.2126, .7152, .0722][i], 0);
    }
    const pairs = [], excluded = [];
    for (const element of root.querySelectorAll('*')) {
      if (!element.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true }) || element.closest('[aria-hidden=true], :disabled, svg, style, script')) continue;
      const text = [...element.childNodes].filter(node => node.nodeType === Node.TEXT_NODE).map(node => node.textContent.trim()).join(' ').trim();
      if (!text) continue;
      const style = getComputedStyle(element), foreground = rgba(style.color), bg = background(element);
      if (!bg || foreground[3] !== 1 || Number(style.opacity) !== 1 || style.webkitTextFillColor === 'rgba(0, 0, 0, 0)') { excluded.push(text); continue; }
      const l1 = luminance(foreground), l2 = luminance(bg);
      const ratio = (Math.max(l1, l2) + .05) / (Math.min(l1, l2) + .05);
      const size = parseFloat(style.fontSize);
      const minimum = size >= 24 || size >= 18.66 && Number(style.fontWeight) >= 700 ? 3 : 4.5;
      pairs.push({ text: text.slice(0, 100), ratio: Number(ratio.toFixed(2)), minimum, pass: ratio >= minimum, color: style.color, background: bg.slice(0, 3), size });
    }
    return { pairs, excluded };
  });
  const snapshot = await surface.ariaSnapshot();
  report.checks.push({ label, ...results, accessibilitySnapshot: snapshot });
  console.log(`${label}: ${results.pairs.length} text pairs, ${results.pairs.filter(pair => !pair.pass).length} contrast failures`);
}

try {
  await page.goto(base);
  await page.waitForFunction(() => /\d+/.test(document.documentElement.dataset.foodeaseRevision || ''));
  await page.locator('[data-order-manual]').click();
  for (const theme of ['light', 'dark', 'contrast']) {
    if (theme === 'dark') await page.locator('[data-header-theme]').click();
    if (theme === 'contrast') await page.locator('[data-access-toggle=contrast]').click();
    await inspect(`${theme}-menu`, '#popular');
    await inspect(`${theme}-header`, '.site-header');
    await page.locator('[data-menu-item][data-id="wrap-hot-chicken"] [data-detail-item]').click();
    await page.waitForFunction(() => document.querySelector('[data-item-dialog]').open);
    await inspect(`${theme}-details`, '[data-item-dialog]');
    await page.locator('[data-detail-quantity]').fill('2');
    await page.locator('[data-detail-add]').click();
    await page.waitForFunction(() => !document.querySelector('[data-item-dialog]').open);
    await page.locator('[data-cart-trigger]').click();
    await page.waitForFunction(() => document.documentElement.dataset.foodeaseRoute === 'cart');
    await inspect(`${theme}-cart`, '[data-cart-dialog]');
    await page.screenshot({ path: `${output}/${theme}-cart.png` });
    await page.locator('[data-checkout-button]').click();
    await page.waitForFunction(() => document.querySelector('[data-checkout-dialog]').open);
    await inspect(`${theme}-checkout`, '[data-checkout-dialog]');
    await page.screenshot({ path: `${output}/${theme}-checkout.png` });
    await page.keyboard.press('Escape');
    await page.waitForFunction(() => document.querySelector('[data-cart-dialog]').open);
    await page.keyboard.press('Escape');
    await page.waitForFunction(() => !document.querySelector('[data-cart-dialog]').open);
  }
  await page.locator('[data-access-toggle=contrast]').click();
  await page.locator('[data-header-theme]').click();
  for (const [width, height] of [[320, 700], [375, 812], [667, 375], [768, 1024], [1440, 1000]]) {
    await page.setViewportSize({ width, height });
    await page.evaluate(() => scrollTo({ top: 0, behavior: 'instant' }));
    await page.screenshot({ path: `${output}/page-${width}.png`, fullPage: width === 375 || width === 1440 });
    report.checks.push({ label: `viewport-${width}`, overflow: await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), headerOverflow: await page.locator('.site-header').evaluate(el => el.scrollWidth > el.clientWidth) });
  }
} finally {
  await writeFile(`${output}/audit.json`, JSON.stringify(report, null, 2));
  await browser.close();
}
const failures = report.checks.flatMap(check => (check.pairs || []).filter(pair => !pair.pass).map(pair => ({ surface: check.label, ...pair })));
const uniqueFailures = [...new Map(failures.map(row => [`${row.surface}:${row.text}`, row])).values()];
console.log(JSON.stringify({ failures: uniqueFailures, consoleErrors: errors, overflow: report.checks.filter(check => check.overflow || check.headerOverflow) }, null, 2));
if (failures.length || errors.length || report.checks.some(check => check.overflow || check.headerOverflow)) process.exitCode = 1;
