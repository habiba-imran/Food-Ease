// Offline rendered UI evidence. Does not test providers or human hearing.
import { chromium } from 'playwright';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
const output = 'docs/voice-audit-evidence';
const fake = await readFile('tests/fake-livekit.mjs', 'utf8');
const browser = await chromium.launch({ channel: 'chromium', args: ['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream'] });
const page = await browser.newPage({ viewport: { width: 375, height: 812 }, permissions: ['microphone'], reducedMotion: 'reduce' });
const report = { kind: 'offline_browser_fixture', errors: [], checks: [], limits: 'Synthetic microphone; fake RTC/model. Computed solid-color text pairs and native accessibility snapshots; no human screen-reader, real speech recognition or audible voice-quality claim.' };
page.on('pageerror', error => report.errors.push(error.message));
page.on('console', message => { if (message.type() === 'error') report.errors.push(message.text()); });
await mkdir(output, { recursive: true });

async function inspect(label, selector) {
  const surface = page.locator(selector);
  const data = await surface.evaluate(root => {
    const canvas = document.createElement('canvas'); canvas.width = canvas.height = 1;
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    const rgba = value => { ctx.clearRect(0, 0, 1, 1); ctx.fillStyle = value; ctx.fillRect(0, 0, 1, 1); return [...ctx.getImageData(0, 0, 1, 1).data]; };
    function bg(element) {
      if (!element) return [255, 255, 255, 255];
      const style = getComputedStyle(element); if (style.backgroundImage !== 'none') return null;
      const c = rgba(style.backgroundColor); if (c[3] === 255) return c;
      const parent = bg(element.parentElement); if (!parent) return null;
      const alpha = c[3] / 255; return c.slice(0, 3).map((v, i) => v * alpha + parent[i] * (1 - alpha)).concat(255);
    }
    const lum = c => c.slice(0, 3).map(v => { v /= 255; return v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4; }).reduce((sum, v, i) => sum + v * [.2126, .7152, .0722][i], 0);
    const pairs = [];
    for (const el of [root, ...root.querySelectorAll('*')]) {
      if (!el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true }) || el.closest('svg, :disabled, [aria-hidden=true]')) continue;
      const text = [...el.childNodes].filter(n => n.nodeType === Node.TEXT_NODE).map(n => n.textContent.trim()).join(' ').trim();
      if (!text) continue;
      const style = getComputedStyle(el), fg = rgba(style.color), background = bg(el);
      if (!background || fg[3] !== 255) continue;
      const a = lum(fg), b = lum(background), ratio = (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
      const minimum = parseFloat(style.fontSize) >= 24 || parseFloat(style.fontSize) >= 18.66 && Number(style.fontWeight) >= 700 ? 3 : 4.5;
      pairs.push({ text: text.slice(0, 120), ratio: Number(ratio.toFixed(2)), minimum, pass: ratio >= minimum });
    }
    return { pairs, overflow: root.scrollWidth > root.clientWidth };
  });
  report.checks.push({ label, ...data, semantics: await surface.ariaSnapshot() });
}

try {
  await page.route('**/static/vendor/livekit-client.2.15.4.mjs', route => route.fulfill({ body: fake, contentType: 'text/javascript' }));
  await page.goto(process.argv[2] || 'http://127.0.0.1:8186');
  await page.waitForFunction(() => document.documentElement.dataset.foodeaseRevision);
  report.initialWelcome = await page.locator('[data-voice-welcome]').evaluate(element => {
    const rect = element.getBoundingClientRect();
    return { visible: rect.top >= document.querySelector('.site-header').getBoundingClientRect().bottom && rect.bottom <= innerHeight, top: rect.top, bottom: rect.bottom, viewportHeight: innerHeight };
  });
  await page.locator('[data-voice-launcher]').click();
  await page.waitForFunction(() => document.documentElement.dataset.assistanceState === 'voice_active');
  for (const theme of ['light', 'dark', 'contrast']) {
    await page.locator('[data-voice-panel-close]').click();
    if (theme === 'dark') await page.locator('[data-header-theme]').click();
    if (theme === 'contrast') await page.locator('[data-access-toggle=contrast]').click();
    await page.locator('[data-voice-welcome]').scrollIntoViewIfNeeded();
    await inspect(`${theme}-welcome`, '[data-voice-welcome]');
    await page.screenshot({ path: `${output}/${theme}-welcome.png` });
    await page.locator('[data-voice-launcher]').click();
    for (const width of [320, 375, 768, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      await inspect(`${theme}-${width}-controls`, '[data-voice-controls]');
      if (width === 375 || width === 1440) await page.screenshot({ path: `${output}/${theme}-${width}-controls.png` });
    }
  }
  await page.locator('[data-voice-end]').click();
} finally {
  await writeFile(`${output}/audit.json`, JSON.stringify(report, null, 2));
  await browser.close();
}
const failures = report.checks.flatMap(check => check.pairs.filter(pair => !pair.pass).map(pair => ({ surface: check.label, ...pair })));
console.log(JSON.stringify({ initialWelcome: report.initialWelcome, checks: report.checks.length, pairs: report.checks.reduce((sum, check) => sum + check.pairs.length, 0), failures, errors: report.errors, overflow: report.checks.filter(check => check.overflow).map(check => check.label) }, null, 2));
if (!report.initialWelcome?.visible || failures.length || report.errors.length || report.checks.some(check => check.overflow)) process.exitCode = 1;
