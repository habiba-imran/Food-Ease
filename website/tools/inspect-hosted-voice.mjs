// Bounded synthetic-browser diagnosis. Never records tokens, speech or real microphone audio.
import { chromium } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';
const target = 'https://food-ease-seven.vercel.app';
const browser = await chromium.launch({ args: ['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream'] });
const context = await browser.newContext({ permissions: ['microphone'] });
const page = await context.newPage();
const report = { target, failures: [], errors: [], consoleErrors: [], states: [] };
const path = url => { const parsed = new URL(url); return parsed.origin + parsed.pathname; };
page.on('response', response => { if (response.status() >= 400) report.failures.push({ url: path(response.url()), status: response.status() }); });
page.on('requestfailed', request => report.failures.push({ url: path(request.url()), error: request.failure()?.errorText }));
page.on('pageerror', error => report.errors.push(error.message));
page.on('console', message => {
  if (['error', 'warning'].includes(message.type()) && /createOffer|PC manager|closed peer|failed to load|UnexpectedConnectionState/i.test(message.text())) report.consoleErrors.push(message.text());
});
try {
  await page.goto(target, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForFunction(() => document.documentElement.dataset.foodeaseRevision, { timeout: 30000 });
  report.orchestrationPath = await page.locator('body').getAttribute('data-orchestration-url');
  report.widget = { source: await page.locator('script[src*="app.js"]').getAttribute('src'),
    welcomeCount: await page.locator('[data-voice-welcome], [data-wake-toggle]').count(),
    panelTag: await page.locator('[data-voice-controls]').evaluate(node => node.tagName) };
  if (process.argv.includes('--start')) {
    await page.locator('[data-voice-launcher]').click();
    if (await page.locator('[data-voice-use]').isVisible()) await page.locator('[data-voice-use]').click();
    const deadline = Date.now() + 55000;
    while (Date.now() < deadline) {
      const state = await page.locator('html').getAttribute('data-assistance-state');
      if (report.states.at(-1)?.state !== state) report.states.push({ state, time: new Date().toISOString() });
      if (['voice_active', 'error', 'manual'].includes(state)) break;
      await page.waitForTimeout(500);
    }
    report.message = await page.locator('[data-voice-controls] [data-dialog-status]').textContent();
  }
  await mkdir('../deployment/evidence/voice-widget-2026-11-21', { recursive: true });
  await writeFile(`../deployment/evidence/voice-widget-2026-11-21/hosted-${process.argv.includes('--after') ? 'after' : 'before'}.json`, JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
} finally {
  const stop = page.locator('[data-voice-end]');
  if (await stop.isVisible().catch(() => false)) await stop.click().catch(() => {});
  await page.waitForTimeout(1000).catch(() => {});
  await browser.close();
}
