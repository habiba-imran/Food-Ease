// Real website/worker/cart with fake RTC, synthetic microphone and scripted model.
import { test, expect } from '@playwright/test';
import { readFile, mkdir } from 'node:fs/promises';
const fake = await readFile(new URL('../fake-livekit.mjs', import.meta.url), 'utf8');
test.use({ channel: 'chromium', permissions: ['microphone'], launchOptions: { args: ['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream'] } });
const panel = page => page.locator('[data-voice-controls]');
const launcher = page => page.locator('[data-voice-launcher]');
test.beforeEach(async ({ page }) => {
  await page.route('**/static/vendor/livekit-client.2.15.4.mjs', r => r.fulfill({ body: fake, contentType: 'text/javascript' }));
  await page.addInitScript(() => {
    window.captured = [];
    const get = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
    navigator.mediaDevices.getUserMedia = async args => { const stream = await get(args); window.captured.push(...stream.getTracks()); return stream; };
    window.wakeCreated = 0;
    window.SpeechRecognition = class { constructor() { window.wakeCreated++; } };
  });
  await page.goto('/');
  await expect(page.locator('html')).toHaveAttribute('data-foodease-revision', /\d+/);
  await page.emulateMedia({ reducedMotion: 'reduce' });
});
async function open(page) { if (!await panel(page).isVisible()) await launcher(page).click(); }
async function start(page) {
  await open(page);
  await panel(page).locator('[data-voice-use]').click();
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'voice_active', { timeout: 15000 });
}

for (const width of [390, 1440]) test(`one corner widget, no welcome or wake capture, non-modal ordering at ${width}px`, async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.setViewportSize({ width, height: 900 });
  await expect(page.locator('[data-voice-widget]')).toHaveCount(1);
  await expect(page.locator('[data-voice-welcome], [data-wake-toggle]')).toHaveCount(0);
  expect(await page.evaluate(() => window.captured.length + window.wakeCreated)).toBe(0);
  await open(page);
  await expect(panel(page)).toBeVisible();
  await expect(page.locator('dialog[open]')).toHaveCount(0);
  expect(await page.evaluate(() => window.captured.length)).toBe(0);
  const bounds = await panel(page).boundingBox();
  expect(bounds.width).toBeLessThanOrEqual(360);
  expect(bounds.x).toBeGreaterThanOrEqual(0);
  expect(bounds.y).toBeGreaterThanOrEqual(0);
  await start(page);
  await expect(panel(page).locator('[data-agent-transcript]')).toContainText('What would you like to eat');
  await page.locator('[data-menu-item][data-id="drink-cola"] [data-add-item]').click();
  await expect(page.locator('[data-cart-count]')).toHaveText('1');
  await page.locator('[data-cart-trigger]').click();
  await expect(page.locator('[data-cart-dialog]')).toBeVisible();
  await expect(page.locator('[data-cart-dialog] [data-voice-widget]')).toHaveCount(1);
  await expect(panel(page).locator('[data-agent-transcript]')).toBeVisible();
  await panel(page).locator('[data-voice-panel-close]').click();
  await expect(panel(page)).toBeHidden();
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'voice_active');
  await open(page);
  await panel(page).locator('[data-voice-end]').click();
  await expect.poll(() => page.evaluate(() => window.captured.every(track => track.readyState === 'ended'))).toBe(true);
  expect(errors).toEqual([]);
});

test('connecting microphone, starting agent, speaking and paused are visible in the same widget', async ({ page }) => {
  await page.route('**/v2/assist/start', async route => { await new Promise(r => setTimeout(r, 500)); await route.continue(); });
  await open(page);
  await panel(page).locator('[data-voice-use]').click();
  await expect(panel(page).locator('[data-voice-feedback]')).toHaveText('Preparing Zara…');
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'voice_active', { timeout: 15000 });
  await page.evaluate(() => {
    const user = window.fakeLiveKit.rooms.find(r => r.role === 'user' && !r.closed);
    user.emit('DataReceived', new TextEncoder().encode(JSON.stringify({ schema_version:'2.0', session_id:user.sid,
      event_id:crypto.randomUUID(), timestamp:new Date(Date.now()+1000).toISOString(), type:'agent.status', payload:{state:'assistant_speaking'} })), user.agent, null, 'foodease.events.v2');
  });
  await expect(launcher(page)).toHaveAttribute('data-voice-activity', 'speaking');
  await expect(panel(page).locator('[data-voice-feedback]')).toHaveText('Assistant Speaking');
  await panel(page).locator('[data-voice-pause]').click();
  await expect(launcher(page)).toHaveAttribute('data-voice-activity', 'paused');
  await expect(panel(page).locator('[data-voice-microphone]')).toHaveText('Microphone off');
  await expect(panel(page).locator('[data-dialog-status]')).not.toContainText('could not be delivered');
  await mkdir('../deployment/evidence/voice-widget-2026-11-21', { recursive: true });
  await page.screenshot({ path:'../deployment/evidence/voice-widget-2026-11-21/widget-desktop.png' });
  await panel(page).locator('[data-voice-end]').click();
});

test('blocked microphone is explained inside the widget; typing remains available', async ({ page }) => {
  await page.evaluate(() => { navigator.mediaDevices.getUserMedia = async () => { throw new DOMException('blocked', 'NotAllowedError'); }; });
  await open(page);
  await panel(page).locator('[data-voice-use]').click();
  await expect(panel(page).locator('[data-dialog-status]')).toContainText('permission is blocked');
  await expect(panel(page).locator('[data-voice-retry]')).toBeVisible();
  await panel(page).locator('[data-voice-typed]').click();
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'typed_active');
  await expect(panel(page).locator('[data-assistant-input]')).toBeVisible();
});
