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
    window.wakeInstances = [];
    window.SpeechRecognition = class {
      constructor() { window.wakeCreated++; window.wakeInstances.push(this); }
      start() { this.started = true; this.onstart?.(); }
      abort() { this.started = false; this.onend?.(); }
      result(text) { this.onresult?.({ resultIndex: 0, results: [Object.assign([{transcript:text}], {isFinal:true})] }); }
    };
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
  await expect(page.locator('[data-voice-welcome], [data-voice-typed], [data-assistant-form], [data-dialog-typing]')).toHaveCount(0);
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
  await expect(panel(page).locator('[data-wake-status]')).toContainText('Wake microphone on');
  expect(await page.evaluate(() => window.wakeInstances.at(-1).started)).toBe(true);
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
  await mkdir('../deployment/evidence/persistent-wake-2026-11-21', { recursive: true });
  await page.screenshot({ path:'../deployment/evidence/persistent-wake-2026-11-21/widget-desktop.png' });
  await panel(page).locator('[data-voice-end]').click();
});

test('blocked microphone is explained inside the widget without enabling wake or typing', async ({ page }) => {
  await page.evaluate(() => { navigator.mediaDevices.getUserMedia = async () => { throw new DOMException('blocked', 'NotAllowedError'); }; });
  await open(page);
  await panel(page).locator('[data-voice-use]').click();
  await expect(panel(page).locator('[data-dialog-status]')).toContainText('permission is blocked');
  await expect(panel(page).locator('[data-voice-retry]')).toBeVisible();
  await expect(page.locator('[data-assistant-input], [data-voice-typed]')).toHaveCount(0);
  expect(await page.evaluate(() => window.wakeCreated)).toBe(0);
});

test('Hey Zara re-arms, activates once, survives reload and can be turned off', async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await start(page);
  expect(await page.evaluate(() => window.wakeCreated)).toBe(0);
  await panel(page).locator('[data-voice-end]').click();
  await expect(page.locator('html')).toHaveAttribute('data-wake-state', 'listening');
  let starts = 0;
  page.on('request', request => { if (request.url().endsWith('/v2/assist/start')) starts++; });
  await page.evaluate(() => {
    const r = window.wakeInstances.at(-1);
    r.result('زارا، دو کولا شامل کرو'); r.result('زارا، دو کولا شامل کرو');
  });
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'voice_active', {timeout:15000});
  expect(starts).toBe(1);
  await expect(page.locator('[data-cart-count]')).toHaveText('2');
  expect(await page.evaluate(() => window.fakeLiveKit.sent.filter(packet => packet.event.type === 'app.text_input').length)).toBe(1);
  expect(await page.evaluate(() => window.wakeInstances.some(r => r.started))).toBe(false);
  await page.evaluate(() => {
    Object.defineProperty(document, 'hidden', {value:true, configurable:true});
    document.dispatchEvent(new Event('visibilitychange'));
  });
  await expect.poll(() => page.evaluate(() => window.captured.every(track => track.readyState === 'ended'))).toBe(true);
  expect(await page.evaluate(() => window.wakeInstances.some(r => r.started))).toBe(false);
  await page.evaluate(() => {
    Object.defineProperty(document, 'hidden', {value:false, configurable:true});
    document.dispatchEvent(new Event('visibilitychange'));
  });
  await expect(page.locator('html')).toHaveAttribute('data-wake-state', 'listening');
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-wake-state', 'listening');
  expect(await page.evaluate(() => window.captured.length)).toBe(0);
  await open(page);
  await panel(page).locator('[data-wake-toggle]').click();
  await expect(panel(page).locator('[data-wake-status]')).toContainText('Hey Zara is off');
  expect(await page.evaluate(() => window.wakeInstances.some(r => r.started))).toBe(false);
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-foodease-revision', /\d+/);
  expect(await page.evaluate(() => window.wakeCreated)).toBe(0);
  expect(errors).toEqual([]);
});

test('wake recognition failure clears the microphone indicator immediately', async ({page}) => {
  await start(page);
  await panel(page).locator('[data-voice-end]').click();
  await expect(page.locator('html')).toHaveAttribute('data-wake-state','listening');
  await expect(panel(page).locator('[data-voice-microphone]')).toHaveText('Wake microphone on');
  await page.evaluate(()=>window.wakeInstances.at(-1).onerror({error:'not-allowed'}));
  await expect(page.locator('html')).toHaveAttribute('data-wake-state','error');
  await expect(panel(page).locator('[data-voice-microphone]')).toHaveText('Microphone off');
  await expect(panel(page).locator('[data-wake-status]')).toContainText('permission is blocked');
});

test('wake network recovery accepts Urdu Hey Zara and hands off one command once', async ({page}) => {
  const errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  await start(page);
  await panel(page).locator('[data-voice-end]').click();
  await expect(page.locator('html')).toHaveAttribute('data-wake-state','listening');
  let starts=0;
  page.on('request',r=>{if(r.url().endsWith('/v2/assist/start'))starts++;});
  await page.evaluate(()=>window.wakeInstances.at(-1).onerror({error:'network'}));
  await expect(panel(page).locator('[data-wake-status]')).toContainText('Reconnecting');
  await expect(panel(page).locator('[data-voice-microphone]')).toHaveText('Microphone off');
  await expect.poll(()=>page.evaluate(()=>window.wakeInstances.length)).toBe(2);
  await expect(page.locator('html')).toHaveAttribute('data-wake-state','listening');
  await page.evaluate(()=>{
    const r=window.wakeInstances.at(-1);
    r.result('ہائے زارا، دو کولا شامل کرو');
    r.result('ہائے زارا، دو کولا شامل کرو');
  });
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state','voice_active');
  await expect(page.locator('[data-cart-count]')).toHaveText('2');
  expect(starts).toBe(1);
  expect(await page.evaluate(()=>window.fakeLiveKit.sent.filter(p=>p.event.type==='app.text_input').length)).toBe(1);
  expect(await page.evaluate(()=>window.wakeInstances.some(r=>r.started))).toBe(false);
  expect(errors).toEqual([]);
  await open(page);
  await panel(page).locator('[data-voice-end]').click();
});

test('every item has a short description and no ingredient list or local voice or typing buttons', async ({ page }) => {
  const ids = await page.locator('[data-menu-item]').evaluateAll(cards => cards.map(c => c.dataset.id));
  expect(ids).toHaveLength(28);
  for (const id of ids) {
    const card = page.locator(`[data-menu-item][data-id="${id}"]`);
    const description = await card.getAttribute('data-description');
    expect(description.length).toBeGreaterThan(20);
    expect(description.length).toBeLessThan(110);
    await card.locator('[data-detail-item]').click();
    await expect(page.locator('[data-detail-description]')).toHaveText(description);
    await expect(page.locator('[data-detail-ingredients], [data-assist-voice], [data-dialog-typing]')).toHaveCount(0);
    await expect(panel(page)).toBeHidden();
    await page.locator('[data-detail-close]').click();
  }
  await page.locator('[data-cart-trigger]').click();
  await expect(page.locator('[data-cart-dialog]')).toBeVisible();
  await expect(panel(page)).toBeHidden();
  await expect(page.locator('[data-cart-dialog] > [data-voice-use], [data-cart-dialog] [data-assist-voice]')).toHaveCount(0);
});


test('provider failure and actual interruption are distinct captions', async ({ page }) => {
  await start(page);
  await page.evaluate(() => {
    const user = window.fakeLiveKit.rooms.find(r => r.role === 'user' && !r.closed);
    for (const [phase,text] of [['failed',''], ['interrupted','آپ کے کارٹ']]) {
      user.emit('DataReceived', new TextEncoder().encode(JSON.stringify({schema_version:'2.0', session_id:user.sid,
        event_id:crypto.randomUUID(),turn_id:'audit-'+phase,timestamp:new Date().toISOString(),
        type:'transcript.assistant',payload:{utterance_id:'audit-'+phase,text,phase}})), user.agent,null,'foodease.events.v2');
    }
  });
  await expect(panel(page).locator('[data-phase="failed"]')).toHaveText('جواب مکمل نہیں ہو سکا۔');
  await expect(panel(page).locator('[data-phase="failed"]')).not.toContainText('interrupted');
  await expect(panel(page).locator('[data-phase="interrupted"]')).toContainText('آپ کے کارٹ (interrupted)');
  await panel(page).locator('[data-voice-end]').click();
});
