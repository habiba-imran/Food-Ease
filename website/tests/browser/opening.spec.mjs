import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';
const fake = await readFile(new URL('../fake-livekit.mjs', import.meta.url), 'utf8');
test.use({ channel: 'chromium', permissions: ['microphone'], launchOptions: { args: ['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream'] } });
test.beforeEach(async ({ page }) => {
  await page.route('**/static/vendor/livekit-client.2.15.4.mjs', r => r.fulfill({ body: fake, contentType: 'text/javascript' }));
  await page.goto('/');
  await expect(page.locator('html')).toHaveAttribute('data-foodease-revision', /\d+/);
});
test.afterEach(async ({ page }, info) => {
  if (info.status !== info.expectedStatus) {
    console.log('Opening failure:', await page.locator('[data-order-status]').textContent());
    console.log('Media tracks:', await page.evaluate(() => window.captured?.map(t => ({ kind: t.kind, state: t.readyState }))));
  }
});
async function trackMedia(page) {
  await page.evaluate(() => {
    window.captured = [];
    const original = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
    navigator.mediaDevices.getUserMedia = async constraints => {
      let stream;
      try { stream = await original(constraints); }
      catch (error) { throw new Error(`${error.name}: ${error.message}; devices: ${(await navigator.mediaDevices.enumerateDevices()).map(d => d.label).join(',')}`); }
      window.captured.push(...stream.getTracks());
      return stream;
    };
  });
}
async function input(page, text) {
  await page.locator('[data-assistant-input]').fill(text);
  await page.locator('[data-assistant-form] button[type=submit]').click();
}
test('fresh visitor and direct manual never request media or a dispatch', async ({ page }) => {
  let starts = 0;
  page.on('request', r => { if (r.url().endsWith('/v2/assist/start')) starts++; });
  await page.evaluate(() => { navigator.mediaDevices.getUserMedia = () => { throw new Error('Unexpected capture'); }; });
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'awaiting_spoken_choice_consent');
  await page.locator('[data-assist-manual]').click();
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'manual');
  expect(starts).toBe(0);
});
test('chooser rejects shopping, clarifies once, and manual ends actual capture and playback', async ({ page }) => {
  await trackMedia(page);
  await page.locator('[data-assist-choice]').click();
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'choosing_mode');
  await expect(page.locator('[data-agent-transcript]')).toContainText('How would you like to order');
  await page.locator('[data-assist-pause]').click();
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'paused');
  await page.locator('[data-assist-pause]').click();
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'choosing_mode');
  await input(page, 'add a wrap');
  await expect(page.locator('[data-agent-transcript]')).toContainText('Say use voice');
  await expect(page.locator('[data-cart-count]')).toHaveText('0');
  await page.evaluate(async () => {
    const user = window.fakeLiveKit.rooms.find(r => r.role === 'user' && !r.closed);
    const ctx = window.audioContext = new AudioContext();
    await ctx.resume();
    const osc = ctx.createOscillator(), dest = ctx.createMediaStreamDestination();
    osc.connect(dest); osc.start();
    window.playingAudio = document.createElement('audio');
    window.playingAudio.srcObject = dest.stream;
    const track = { kind: 'audio', attach: () => window.playingAudio, detach() {} };
    user.emit('TrackSubscribed', track, { trackSid: 'real-browser-audio' }, user.agent);
  });
  await expect.poll(() => page.evaluate(() => window.playingAudio.paused)).toBe(false);
  await input(page, "I'll order myself");
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'manual');
  await expect.poll(() => page.evaluate(() => window.captured.every(t => t instanceof MediaStreamTrack && t.readyState === 'ended'))).toBe(true);
  expect(await page.evaluate(() => ({ paused: window.playingAudio.paused, detached: window.playingAudio.srcObject === null }))).toEqual({ paused: true, detached: true });
  expect(await page.evaluate(() => window.fakeLiveKit.rooms.find(r => r.role === 'user').unpublishedTracks.length)).toBe(1);
  await page.evaluate(() => window.audioContext.close());
});
test('voice manual voice and typing preserve cart/session; each generation greets once', async ({ page }) => {
  await trackMedia(page);
  const sid = await page.evaluate(() => sessionStorage.getItem('foodease.shopping-session.v2'));
  await page.locator('[data-assist-voice]').click();
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'voice_active');
  await input(page, 'add a wrap');
  await expect(page.locator('[data-cart-count]')).toHaveText('1');
  await page.locator('[data-assist-manual]').click();
  await expect.poll(() => page.evaluate(() => window.captured.every(t => t.readyState === 'ended'))).toBe(true);
  await page.locator('[data-assist-voice]').click();
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'voice_active');
  await expect(page.locator('[data-agent-transcript]')).toContainText('Welcome back');
  await input(page, 'switch to typing');
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'typed_active');
  await expect.poll(() => page.evaluate(() => window.captured.every(t => t.readyState === 'ended'))).toBe(true);
  await expect(page.locator('[data-cart-count]')).toHaveText('1');
  expect(await page.evaluate(() => sessionStorage.getItem('foodease.shopping-session.v2'))).toBe(sid);
  expect(await page.evaluate(() => window.fakeLiveKit.rooms.filter(r => r.role === 'user').length)).toBe(2);
  await page.locator('[data-assist-manual]').click();
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'manual');
});
for (const problem of ['denied', 'missing', 'pending']) {
  test(`microphone ${problem} never dispatches; late permission is stopped after manual`, async ({ page }) => {
    let starts = 0;
    page.on('request', r => { if (r.url().endsWith('/v2/assist/start')) starts++; });
    await page.evaluate(problem => {
      navigator.mediaDevices.getUserMedia = () => problem === 'pending'
        ? new Promise(resolve => { window.releasePermission = resolve; })
        : Promise.reject(new DOMException(problem, problem === 'denied' ? 'NotAllowedError' : 'NotFoundError'));
    }, problem);
    await page.locator('[data-assist-choice]').click();
    if (problem === 'pending') {
      await page.locator('[data-assist-manual]').click();
      await page.evaluate(() => {
        const dest = new AudioContext().createMediaStreamDestination();
        window.lateTrack = dest.stream.getAudioTracks()[0];
        window.releasePermission(dest.stream);
      });
      await expect.poll(() => page.evaluate(() => window.lateTrack.readyState)).toBe('ended');
    } else await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'error');
    expect(starts).toBe(0);
  });
}
test('return visit uses explicit activation fallback and never silently reopens microphone', async ({ page }) => {
  await page.locator('[data-assist-start]').click();
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'typed_active');
  await page.locator('[data-assist-manual]').click();
  await page.reload();
  // Phase 8 may finish retained teardown after reload; both states require a gesture.
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', /^(awaiting_spoken_choice_consent|manual)$/);
  await page.evaluate(() => { navigator.mediaDevices.getUserMedia = () => { throw new Error('No new consent'); }; });
  await page.locator('[data-assist-start]').click();
  await expect(page.locator('[data-agent-transcript]')).toContainText('Welcome back');
});
test('autoplay blocked before readiness stops capture without a greeting', async ({ page }) => {
  await trackMedia(page);
  await page.route('**/static/vendor/livekit-client.2.15.4.mjs', r => r.fulfill({
    body: fake.replace('async startAudio() {}', 'async startAudio() { throw new Error("autoplay blocked"); }'),
    contentType: 'text/javascript',
  }));
  let ready = 0;
  page.on('request', r => { if (r.url().endsWith('/v2/assist/ready')) ready++; });
  await page.locator('[data-assist-choice]').click();
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'error');
  await expect.poll(() => page.evaluate(() => window.captured.every(t => t.readyState === 'ended'))).toBe(true);
  await expect(page.locator('[data-agent-transcript]')).not.toContainText('Hi!');
  expect(ready).toBe(0);
});
test('manual during a committed cart request preserves its outcome and stops capture', async ({ page }) => {
  await trackMedia(page);
  let release, entered;
  const blocked = new Promise(resolve => { entered = resolve; });
  const hold = new Promise(resolve => { release = resolve; });
  let submissions = 0;
  await page.route('**/api/v2/app/action', async route => {
    if (route.request().postDataJSON().payload.operation !== 'cart.add_item') return route.continue();
    submissions++;
    const response = await route.fetch(); // The authority commits before manual selection.
    entered();
    await hold;
    await route.fulfill({ response });
  });
  await page.locator('[data-assist-voice]').click();
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'voice_active');
  await input(page, 'add a wrap');
  await blocked;
  await page.locator('[data-assist-manual]').click();
  await expect.poll(() => page.evaluate(() => window.captured.every(t => t.readyState === 'ended'))).toBe(true);
  release();
  await expect(page.locator('[data-cart-count]')).toHaveText('1');
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'manual');
  expect(submissions).toBe(1);
  await expect(page.locator('audio[data-foodease-audio]')).toHaveCount(0);
});
test('explicit typed audio preference never opens capture and can be switched off', async ({ page }) => {
  await page.evaluate(() => {
    window.captureCalls = 0;
    navigator.mediaDevices.getUserMedia = () => { window.captureCalls++; throw new Error('Typing does not capture'); };
  });
  await page.locator('[data-assist-start]').click();
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'typed_active');
  await page.evaluate(() => {
    const user = window.fakeLiveKit.rooms.find(r => r.role === 'user' && !r.closed);
    const track = { kind: 'audio', attach() {
      const element = document.createElement('audio');
      element.play = async () => {}; // Attachment preference only; actual playback covered above.
      return element;
    }, detach() {} };
    user.emit('TrackSubscribed', track, { trackSid: 'typed-opt-in' }, user.agent);
  });
  await expect(page.locator('audio[data-foodease-audio]')).toHaveCount(0);
  await page.locator('[data-assist-typed-audio]').check();
  await expect(page.locator('audio[data-foodease-audio]')).toHaveCount(1);
  await page.locator('[data-assist-typed-audio]').uncheck();
  await expect(page.locator('audio[data-foodease-audio]')).toHaveCount(0);
  expect(await page.evaluate(() => window.captureCalls)).toBe(0);
});
test('spoken chooser voice choice opens shopping once; manual during greeting revokes it', async ({ page }) => {
  await trackMedia(page);
  await page.locator('[data-assist-choice]').click();
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'choosing_mode');
  await input(page, 'talk me through it');
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'voice_active');
  await expect(page.locator('[data-agent-transcript]')).toContainText('What would you like to eat');
  await page.locator('[data-assist-manual]').click();
  await expect.poll(() => page.evaluate(() => window.captured.every(t => t.readyState === 'ended'))).toBe(true);
  await expect(page.locator('[data-cart-count]')).toHaveText('0');
  expect(await page.evaluate(() => window.fakeLiveKit.sent.filter(row => row.event.payload.intent === 'start').length)).toBe(1);
});
test('mode controls and typed input remain usable inside the preserved checkout dialog', async ({ page }) => {
  await trackMedia(page);
  await page.locator('[data-assist-voice]').click();
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'voice_active');
  await input(page, 'add a wrap');
  await expect(page.locator('[data-cart-count]')).toHaveText('1');
  await input(page, 'Read my checkout summary');
  const dialog = page.locator('[data-checkout-dialog]');
  await expect(dialog).toBeVisible();
  await dialog.locator('[data-assist-start]').click();
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'typed_active');
  await expect(dialog.locator('[data-assistant-input]')).toBeVisible();
  await expect(page.locator('html')).toHaveAttribute('data-foodease-route', 'checkout');
  await expect(page.locator('[data-cart-count]')).toHaveText('1');
  await dialog.locator('[data-assist-manual]').click();
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'manual');
  await expect(dialog).toBeVisible();
});
