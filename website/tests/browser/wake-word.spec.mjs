import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';

const fake = await readFile(new URL('../fake-livekit.mjs', import.meta.url), 'utf8');
test.use({ permissions: ['microphone'], launchOptions: { args: ['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream'] } });
const toggle = page => page.locator('[data-voice-welcome] [data-wake-toggle]');
const status = page => page.locator('[data-voice-welcome] [data-wake-status]');
async function enable(page) {
  await toggle(page).click();
  await expect(status(page)).toContainText('Wake microphone on');
}

test.beforeEach(async ({ page }) => {
  await page.route('**/static/vendor/livekit-client.2.15.4.mjs', route => route.fulfill({ body: fake, contentType: 'text/javascript' }));
  await page.addInitScript(() => {
    window.wakeInstances = [];
    window.captureCount = 0;
    const get = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
    navigator.mediaDevices.getUserMedia = (...args) => {
      if (window.wakeInstances.some(r => !r.ended)) throw new Error('Wake microphone still owns capture');
      window.captureCount++;
      return get(...args);
    };
    window.SpeechRecognition = class {
      constructor() { window.wakeInstances.push(this); }
      start() { this.onstart(); }
      abort() { this.aborted = true; if (!window.holdWakeEnd) this.end(); }
      end() { this.ended = true; this.onend(); }
      say(text) { this.onresult({ resultIndex: 0, results: [Object.assign([{ transcript: text }], { isFinal: true })] }); }
    };
  });
  await page.goto('/');
  await expect(page.locator('html')).toHaveAttribute('data-foodease-revision', /\d+/);
});

test('opt-in is keyboard accessible; ambient speech never dispatches; addressed command updates real cart once', async ({ page }) => {
  let starts = 0;
  page.on('request', r => { if (r.url().endsWith('/v2/assist/start')) starts++; });
  expect(await page.evaluate(() => window.wakeInstances.length)).toBe(0);
  await toggle(page).focus();
  await page.keyboard.press('Enter');
  await expect(toggle(page)).toHaveAttribute('aria-pressed', 'true');
  await expect(status(page)).toContainText('Wake microphone on');
  await page.evaluate(() => window.wakeInstances[0].say('add two Hot Chicken Wraps'));
  expect(starts).toBe(0);
  expect(await page.evaluate(() => window.captureCount)).toBe(0);
  await page.evaluate(() => {
    window.wakeInstances[0].say('Hey Zara, add two Hot Chicken Wraps');
    window.wakeInstances[0].say('Hey Zara, add two Hot Chicken Wraps');
  });
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'voice_active');
  await expect(page.locator('[data-cart-count]')).toHaveText('2');
  expect(starts).toBe(1);
  expect(await page.evaluate(() => window.captureCount)).toBe(1);
  await expect(page.locator('[data-voice-controls] [data-wake-toggle]')).toBeDisabled();
  await page.locator('[data-voice-end]').click();
  await expect(status(page)).toContainText('Wake microphone off');
  expect(await page.evaluate(() => window.wakeInstances.length)).toBe(1);
});

test('voice waits for browser wake microphone release and ignores stale TTS feedback', async ({ page }) => {
  await enable(page);
  await page.evaluate(() => { window.holdWakeEnd = true; window.wakeInstances[0].say('Hey Zara'); });
  await expect(status(page)).toContainText('closing');
  expect(await page.evaluate(() => window.captureCount)).toBe(0);
  await page.evaluate(() => window.wakeInstances[0].end());
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'voice_active');
  await page.evaluate(() => window.wakeInstances[0].say('Hey Zara, add two Hot Chicken Wraps'));
  await expect(page.locator('[data-cart-count]')).toHaveText('0');
  expect(await page.evaluate(() => window.captureCount)).toBe(1);
});

test('unsupported recognition and permission failure keep manual ordering available', async ({ page }) => {
  await page.evaluate(() => { window.SpeechRecognition = undefined; window.webkitSpeechRecognition = undefined; });
  await toggle(page).click();
  await expect(status(page)).toContainText('not available');
  await expect(toggle(page)).toHaveAttribute('aria-pressed', 'false');
  expect(await page.evaluate(() => window.captureCount)).toBe(0);
  await page.locator('[data-menu-item][data-id="drink-cola"] [data-add-item]').click();
  await expect(page.locator('[data-cart-count]')).toHaveText('1');
});

test('permission rejection stops wake listening and offers typing without dispatch', async ({ page }) => {
  await enable(page);
  await page.evaluate(() => window.wakeInstances[0].onerror({ error: 'not-allowed' }));
  await expect(status(page)).toContainText('permission is blocked');
  await expect(toggle(page)).toHaveAttribute('aria-pressed', 'false');
  expect(await page.evaluate(() => window.captureCount)).toBe(0);
});

test('manual choice cancels a wake handoff before a late end event', async ({ page }) => {
  await enable(page);
  await page.evaluate(() => { window.holdWakeEnd = true; window.wakeInstances[0].say('Hey Zara'); });
  await page.locator('[data-welcome-manual]').click();
  await page.evaluate(() => window.wakeInstances[0].end());
  await expect(status(page)).toContainText('off');
  expect(await page.evaluate(() => window.captureCount)).toBe(0);
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'manual');
});

test('autoplay failure after wake gives an accessible error and ends captured tracks', async ({ page }) => {
  await page.route('**/static/vendor/livekit-client.2.15.4.mjs', route => route.fulfill({
    body: fake.replace('async startAudio() {}', 'async startAudio() { throw new Error("Audio playback is blocked."); }'), contentType: 'text/javascript',
  }));
  await page.evaluate(() => {
    window.mediaTracks = [];
    const get = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
    navigator.mediaDevices.getUserMedia = async (...args) => {
      const media = await get(...args); window.mediaTracks.push(...media.getTracks()); return media;
    };
  });
  await enable(page);
  await page.evaluate(() => window.wakeInstances[0].say('Hey Zara'));
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'error');
  await expect(page.locator('[data-voice-controls] [data-dialog-status]')).toContainText('Audio playback is blocked');
  expect(await page.evaluate(() => window.mediaTracks.every(track => track.readyState === 'ended'))).toBe(true);
  await expect(page.locator('[data-voice-controls] [data-voice-typed]')).toBeVisible();
});
