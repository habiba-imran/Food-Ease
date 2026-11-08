// Real browser/media and local application runtime; RTC and providers are offline fixtures.
import { test, expect as baseExpect } from '@playwright/test';
import { readFile } from 'node:fs/promises';
const expect = baseExpect.configure({ timeout: 15000 });
test.setTimeout(45000);
const fake = await readFile(new URL('../fake-livekit.mjs', import.meta.url), 'utf8');
test.use({ permissions: ['microphone'], launchOptions: { args: ['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream'] } });
const root = page => page.locator('html');
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
  await expect(root(page)).toHaveAttribute('data-foodease-revision', /\d+/);
});

for (const mode of ['voice', 'paused', 'typed']) test(`refresh from ${mode} resets Zara and preserves the cart without reopening capture`, async ({ page }) => {
  await page.locator('[data-menu-item][data-id="drink-cola"] [data-add-item]').click();
  await expect(page.locator('[data-cart-count]')).toHaveText('1');
  if (mode === 'typed') await page.locator('[data-welcome-typed]').click();
  else await launcher(page).click();
  await expect(root(page)).toHaveAttribute('data-assistance-state', mode === 'typed' ? 'typed_active' : 'voice_active');
  const old = await page.evaluate(() => {
    const sid = sessionStorage.getItem('foodease.shopping-session.v2');
    return { sid, ...JSON.parse(sessionStorage.getItem(`foodease.assistance-owner.v2:${sid}`)) };
  });
  if (mode === 'paused') {
    await panel(page).locator('[data-voice-pause]').click();
    await expect(root(page)).toHaveAttribute('data-assistance-state', 'paused');
  }
  await page.reload();
  await expect(root(page)).toHaveAttribute('data-foodease-revision', /\d+/);
  await expect.poll(() => page.evaluate(sid => sessionStorage.getItem(`foodease.assistance-owner.v2:${sid}`), old.sid)).toBeNull();
  await expect(root(page)).toHaveAttribute('data-assistance-state', 'awaiting_spoken_choice_consent');
  await expect(page.locator('[data-cart-count]')).toHaveText('1');
  await expect(panel(page)).toBeHidden();
  expect(await page.evaluate(() => window.captured.length)).toBe(0);
  expect(await page.evaluate(() => document.querySelectorAll('audio[data-foodease-audio]').length)).toBe(0);
  expect((await page.request.get(`/_test/state/${old.sid}`)).ok()).toBe(true);
  await expect.poll(async () => (await (await page.request.get(`/_test/state/${old.sid}`)).json()).state).toBe('ended');
  await expect(page.locator('[data-agent-transcript] [data-utterance-id]')).toHaveCount(0);
  await launcher(page).click();
  await expect(root(page)).toHaveAttribute('data-assistance-state', 'voice_active');
  const fresh = await page.evaluate(() => ({
    generation: window.fakeLiveKit.rooms.find(room => room.role === 'user').generation,
    controls: window.fakeLiveKit.sent.filter(packet => packet.topic === 'foodease.control.v2').map(packet => packet.event.payload.intent),
  }));
  expect(fresh.generation).not.toBe(old.generation);
  expect(fresh.controls[0]).toBe('switch_mode'); // Fresh introduction, never persisted resume.
  expect(fresh.controls).not.toContain('resume');
  await panel(page).locator('[data-voice-end]').click();
});

test('a restored Back/Forward page loads a fresh Zara view instead of frozen conversation state', async ({ page }) => {
  await launcher(page).click();
  await expect(root(page)).toHaveAttribute('data-assistance-state', 'voice_active');
  const loaded = page.waitForEvent('load');
  await page.evaluate(() => {
    // Reproduce a browser BFCache restore notification; routing disables real BFCache.
    window.dispatchEvent(new PageTransitionEvent('pagehide', { persisted: true }));
    window.dispatchEvent(new PageTransitionEvent('pageshow', { persisted: true }));
  });
  await loaded;
  await expect(root(page)).toHaveAttribute('data-foodease-revision', /\d+/);
  await expect(root(page)).toHaveAttribute('data-assistance-state', 'awaiting_spoken_choice_consent');
  await expect(panel(page)).toBeHidden();
  expect(await page.evaluate(() => window.captured.length)).toBe(0);
});

test('failed unload cleanup survives refresh and blocks replacement until explicit retry confirms cleanup', async ({ page }) => {
  await launcher(page).click();
  await expect(root(page)).toHaveAttribute('data-assistance-state', 'voice_active');
  let cleanupAllowed = false, starts = 0;
  page.on('request', request => { if (request.url().endsWith('/v2/assist/start')) starts++; });
  await page.route('**/v2/assist/end', route => cleanupAllowed ? route.continue()
    : route.fulfill({ status: 503, contentType: 'application/json', body: '{}' }));
  await page.reload();
  await expect(launcher(page)).toContainText('Retry Voice Assistant');
  expect(await page.evaluate(() => window.captured.length)).toBe(0);
  await launcher(page).click();
  await expect(panel(page).getByRole('status')).toContainText('Cleanup is still pending');
  expect(await page.evaluate(() => window.captured.length)).toBe(0);
  expect(starts).toBe(0);
  cleanupAllowed = true;
  await panel(page).locator('[data-voice-retry]').click();
  await expect(root(page)).toHaveAttribute('data-assistance-state', 'voice_active');
  expect(starts).toBe(1);
  await panel(page).locator('[data-voice-end]').click();
});
