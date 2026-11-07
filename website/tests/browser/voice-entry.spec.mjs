// Native synthetic media + real website/worker logic; RTC/model are offline fixtures.
import { test, expect } from '@playwright/test';
import { readFile, mkdir } from 'node:fs/promises';
const fake = await readFile(new URL('../fake-livekit.mjs', import.meta.url), 'utf8');
test.use({ channel: 'chromium', permissions: ['microphone'], launchOptions: { args: ['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream'] } });
const panel = page => page.locator('[data-voice-controls]');
const launcher = page => page.locator('[data-voice-launcher]');

test.beforeEach(async ({ page }) => {
  await page.route('**/static/vendor/livekit-client.2.15.4.mjs', route => route.fulfill({ body: fake, contentType: 'text/javascript' }));
  await page.addInitScript(() => {
    window.captured = [];
    const get = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
    navigator.mediaDevices.getUserMedia = async options => {
      const stream = await get(options); window.captured.push(...stream.getTracks()); return stream;
    };
  });
  await page.goto('/');
  await expect(page.locator('html')).toHaveAttribute('data-foodease-revision', /\d+/);
});

test('visible welcome and manual choice require no microphone or dispatch', async ({ page }) => {
  let starts = 0;
  page.on('request', request => { if (request.url().endsWith('/v2/assist/start')) starts++; });
  await expect(page.getByRole('heading', { name: 'Welcome to FoodEase' })).toBeVisible();
  await expect(page.locator('[data-voice-welcome]')).toContainText('Would you like to order manually or use our voice assistant?');
  await page.locator('[data-welcome-manual]').click();
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'manual');
  await expect(page.locator('#popular')).toBeFocused();
  await expect(launcher(page)).toHaveAccessibleName('Start Voice Assistant');
  expect(await page.evaluate(() => window.captured.length)).toBe(0);
  expect(starts).toBe(0);
});

test('spoken welcome, unclear answer and spoken manual choice clean up without ordering', async ({ page }) => {
  await page.locator('[data-welcome-voice]').click();
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'choosing_mode');
  await expect(panel(page).locator('[data-agent-transcript]')).toContainText('Welcome to FoodEase');
  await panel(page).locator('[data-assistant-input]').fill('voice or manual');
  await panel(page).locator('[data-assistant-form] button[type=submit]').click();
  await expect(page.locator('[data-agent-transcript]')).toContainText('Say use voice');
  await panel(page).locator('[data-assistant-input]').fill("I'd like to order manually");
  await panel(page).locator('[data-assistant-form] button[type=submit]').click();
  await expect(panel(page)).toBeHidden();
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'manual');
  await expect.poll(() => page.evaluate(() => window.captured.every(track => track.readyState === 'ended'))).toBe(true);
  await expect(page.locator('[data-cart-count]')).toHaveText('0');
  await expect(launcher(page)).toBeVisible();
});

test('floating activation, pause/resume and reactivation share the current cart', async ({ page }) => {
  await page.locator('[data-menu-item][data-id="drink-cola"] [data-add-item]').click();
  await launcher(page).click();
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'voice_active');
  await expect(panel(page).locator('[data-voice-microphone]')).toHaveText('Microphone on');
  await expect(panel(page).getByRole('status')).not.toContainText('Connecting');
  await expect(launcher(page)).toContainText('Listening');
  await panel(page).locator('[data-voice-pause]').click();
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'paused');
  expect(await page.evaluate(() => window.captured.every(track => !track.enabled))).toBe(true);
  await panel(page).locator('[data-voice-pause]').click();
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'voice_active');
  await panel(page).locator('[data-voice-panel-close]').click();
  await expect(launcher(page)).toBeFocused();
  await launcher(page).click();
  expect(await page.evaluate(() => window.fakeLiveKit.rooms.filter(room => room.role === 'user').length)).toBe(1);
  await panel(page).locator('[data-voice-end]').click();
  await expect.poll(() => page.evaluate(() => window.captured.every(track => track.readyState === 'ended'))).toBe(true);
  await expect(page.locator('[data-cart-count]')).toHaveText('1');
  await launcher(page).click();
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'voice_active');
  await panel(page).locator('[data-assistant-input]').fill('read my cart');
  await panel(page).locator('[data-assistant-form] button[type=submit]').click();
  await expect(panel(page).locator('[data-agent-transcript]')).toContainText('one hundred');
  await expect(page.locator('[data-cart-count]')).toHaveText('1');
});

test('permission failure gives a clear retry without duplicate sessions', async ({ page }) => {
  await page.evaluate(() => {
    const get = navigator.mediaDevices.getUserMedia;
    let attempts = 0;
    navigator.mediaDevices.getUserMedia = options => ++attempts === 1
      ? Promise.reject(new DOMException('blocked', 'NotAllowedError')) : get(options);
  });
  await launcher(page).click();
  await expect(launcher(page)).toContainText('Retry Voice Assistant');
  await expect(panel(page).getByRole('status')).toContainText('permission is blocked');
  expect(await page.evaluate(() => window.fakeLiveKit?.rooms.length || 0)).toBe(0);
  await panel(page).locator('[data-voice-retry]').click();
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'voice_active');
  expect(await page.evaluate(() => window.fakeLiveKit.rooms.filter(room => room.role === 'user').length)).toBe(1);
});

test('welcome choice continues in the same generation and reflects speaking status', async ({ page }) => {
  await page.locator('[data-welcome-voice]').click();
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'choosing_mode');
  await panel(page).locator('[data-voice-use]').click();
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'voice_active');
  expect(await page.evaluate(() => window.fakeLiveKit.rooms.filter(room => room.role === 'user').length)).toBe(1);
  await page.evaluate(() => {
    const user = window.fakeLiveKit.rooms.find(room => room.role === 'user' && !room.closed);
    user.emit('DataReceived', new TextEncoder().encode(JSON.stringify({
      schema_version: '2.0', session_id: user.sid, event_id: crypto.randomUUID(),
      timestamp: new Date(Date.now() + 1000).toISOString(), type: 'agent.status',
      payload: { state: 'assistant_speaking' },
    })), user.agent, null, 'foodease.events.v2');
  });
  await expect(launcher(page)).toContainText('Assistant Speaking');
});

test('failed mode-control delivery stops capture before offering retry', async ({ page }) => {
  await page.locator('[data-welcome-voice]').click();
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'choosing_mode');
  await page.evaluate(() => {
    const user = window.fakeLiveKit.rooms.find(room => room.role === 'user' && !room.closed);
    user.localParticipant.publishData = async () => { throw new Error('The voice control connection failed.'); };
  });
  await panel(page).locator('[data-voice-use]').click();
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'error');
  await expect.poll(() => page.evaluate(() => window.captured.every(track => track.readyState === 'ended'))).toBe(true);
  await expect(panel(page).locator('[data-voice-microphone]')).toHaveText('Microphone off');
  await expect(panel(page).locator('[data-voice-retry]')).toBeVisible();
});

test('explicit retry reconciles a failed end before replacing the old generation', async ({ page }) => {
  await launcher(page).click();
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'voice_active');
  await page.route('**/v2/assist/end', route => route.fulfill({ status: 503, contentType: 'application/json', body: '{}' }));
  await panel(page).locator('[data-voice-end]').click();
  await expect(launcher(page)).toContainText('Retry Voice Assistant');
  expect(await page.evaluate(() => window.captured.every(track => track.readyState === 'ended'))).toBe(true);
  await page.unroute('**/v2/assist/end');
  await launcher(page).click();
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'voice_active');
  expect(await page.evaluate(() => window.fakeLiveKit.rooms.filter(room => room.role === 'user' && !room.closed).length)).toBe(1);
});

test('voice ordering writes real cart data and follows a later manual quantity change', async ({ page }) => {
  await launcher(page).click();
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'voice_active');
  await panel(page).locator('[data-assistant-input]').fill('add two Hot Chicken Wraps');
  await panel(page).locator('[data-assistant-form] button[type=submit]').click();
  await expect(page.locator('[data-cart-count]')).toHaveText('2');
  await expect(page.locator('[data-cart-total]')).toHaveText('1750 PKR');
  await panel(page).locator('[data-voice-end]').click();
  await page.locator('[data-cart-trigger]').click();
  await page.getByRole('button', { name: 'Increase Hot Chicken Wrap' }).click();
  await expect(page.locator('[data-cart-count]')).toHaveText('3');
  await page.keyboard.press('Escape');
  await launcher(page).click();
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'voice_active');
  await panel(page).locator('[data-assistant-input]').fill('read my cart');
  await panel(page).locator('[data-assistant-form] button[type=submit]').click();
  await expect(panel(page).locator('[data-agent-transcript]')).toContainText('two thousand six hundred');
  await expect(page.locator('[data-cart-total]')).toHaveText('2600 PKR');
});

test('floating controls fit mobile and remain keyboard reachable inside the cart', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.locator('[data-order-manual]').click();
  await expect(page.locator('.is-floating-cart')).toBeVisible();
  const boxes = await page.locator('[data-voice-launcher], .is-floating-cart').evaluateAll(elements => elements.map(el => el.getBoundingClientRect().toJSON()));
  expect(boxes[0].right <= boxes[1].left || boxes[1].right <= boxes[0].left || boxes[0].bottom <= boxes[1].top || boxes[1].bottom <= boxes[0].top).toBe(true);
  await page.locator('[data-cart-trigger]').click();
  await expect(page.locator('[data-cart-dialog] [data-voice-launcher]')).toBeVisible();
  await launcher(page).focus();
  await page.keyboard.press('Enter');
  await expect(panel(page)).toBeVisible();
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'voice_active');
  await mkdir('docs/voice-audit-evidence', { recursive: true });
  await page.screenshot({ path: 'docs/voice-audit-evidence/mobile-controls.png' });
  await panel(page).locator('[data-voice-end]').click();
  await expect(page.locator('[data-cart-dialog]')).toBeVisible();
  await expect(launcher(page)).toBeFocused();
});
