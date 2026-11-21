// Real SDK worker -> bound RPC -> server cart -> existing DOM. Speech/model/RTC are fakes.
import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';
const fake = await readFile(new URL('../fake-livekit.mjs', import.meta.url), 'utf8');
const panel = page => page.locator('[data-voice-controls]');
// Inject a synthetic recognized request through the existing worker data path;
// no typing controls are exposed by the production UI. This is not an audio test.
async function say(page, text) {
  const id = await page.evaluate(async text => {
    const user = window.fakeLiveKit.rooms.find(r => r.role === 'user' && !r.closed);
    const context = window.fakeLiveKit.contexts.at(-1);
    const event = {schema_version:'2.0', session_id:user.sid, event_id:crypto.randomUUID(),
      turn_id:crypto.randomUUID(), timestamp:new Date().toISOString(), type:'app.text_input',
      context_revision:context.context_revision, payload:{text}};
    await user.localParticipant.publishData(new TextEncoder().encode(JSON.stringify(event)),
      {reliable:true, topic:'foodease.text_input.v2'});
    return event.turn_id;
  }, text);
  // Ordinary dialogue waits for the reply's real SDK completion, not just an
  // optimistic DOM mutation before its action acknowledgment reaches the worker.
  // Deliberate mid-speech manual actions have separate native playout tests.
  await page.waitForFunction(id => [...document.querySelectorAll('[data-agent-transcript] [data-turn-id]')]
    .some(row => row.dataset.turnId===id && row.dataset.phase==='completed' && row.textContent.trim()), id);
}
async function snapshot(page) {
  return page.evaluate(async () => (await fetch('/api/v2/app/context', {
    headers: { 'X-FoodEase-Session': sessionStorage.getItem('foodease.shopping-session.v2') },
  })).json());
}
test.use({permissions:['microphone'], launchOptions:{args:['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream']}});

test.beforeEach(async ({ page, context }) => {
  await context.addCookies([{ name: 'foodease_test_language', value: 'ur', url: 'http://127.0.0.1:8186' }]);
  await page.route('**/static/vendor/livekit-client.2.15.4.mjs', r => r.fulfill({ body: fake, contentType: 'text/javascript' }));
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/');
  await expect(page.locator('html')).toHaveAttribute('data-foodease-revision', /\d+/);
  { await page.locator('[data-voice-launcher]').click(); await page.locator('[data-voice-use]').click(); }
  await expect(page.locator('html')).toHaveAttribute('data-assistance-state', 'voice_active');
});

for (const width of [1440, 390]) test(`Urdu category requests scroll without hiding other dishes at ${width}px`, async ({ page }) => {
  await page.setViewportSize({width, height:900});
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  for (const [text, category] of [
    ['کڑاہی دکھاؤ', 'karahi'], ['برگر دکھاؤ', 'burgers'],
    ['کڑاہی کے کھانے دکھاؤ', 'karahi'],
  ]) {
    await say(page, text);
    await expect.poll(async () => (await snapshot(page)).category).toBe(category);
    await expect(page.locator(`#menu-category-section-${category}`)).toBeInViewport();
    await expect(page.locator('[data-menu-item]:visible')).toHaveCount(28);
    await expect(page.locator('[data-menu-category-group]:not([hidden])')).toHaveCount(9);
    await expect(page.locator('[data-filter=all]')).toHaveAttribute('aria-pressed', 'true');
  }
  // Dishes in other sections remain usable after a voice category request.
  await page.locator('[data-menu-item][data-id="drink-cola"] [data-add-item]').click();
  await expect(page.locator('[data-cart-count]')).toHaveText('1');
  expect((await snapshot(page)).cart.lines[0].item_id).toBe('drink-cola');
  await expect(page.locator('[data-menu-item]:visible')).toHaveCount(28);
  expect(errors).toEqual([]);
});

for (const width of [1440, 390]) test(`Urdu browsing and Roman Urdu followup update the actual cart at ${width}px`, async ({ page }) => {
  await page.setViewportSize({ width, height: 900 });
  await panel(page).locator('[data-voice-panel-close]').click();
  await page.locator('#menu-search').fill('juice');
  await expect.poll(async () => (await snapshot(page)).search_query).toBe('juice');
  await page.locator('[data-voice-launcher]').click();
  await say(page, 'برگر دکھاؤ');
  await expect.poll(async () => (await snapshot(page)).category).toBe('burgers');
  await expect(page.locator('#menu-search')).toHaveValue('');
  await expect(page.locator('#menu-category-section-burgers')).toBeInViewport();
  await say(page, 'سب سے سستا برگر دکھاؤ');
  await expect(page.locator('[data-agent-transcript]')).toContainText('سبزی کی پیٹی والا برگر');
  await say(page, 'pehle wale do add kar do');
  await expect(page.locator('[data-cart-count]')).toHaveText('2');
  expect((await snapshot(page)).cart.lines[0]).toMatchObject({ item_id: 'burger-veg', quantity: 2 });
  await expect(page.locator('[data-cart-toast]')).toHaveAttribute('lang', 'ur');
  await say(page, 'تعداد تین کر دو');
  await expect(page.locator('[data-cart-count]')).toHaveText('3');
  await say(page, 'کارٹ دکھاؤ');
  await expect(page.locator('[data-cart-dialog]')).toBeVisible();
  await expect(page.locator('[data-cart-lines]')).toContainText('Veggie Patty Burger');
  await say(page, 'کارٹ بند کرو');
  await expect(page.locator('[data-cart-dialog]')).toBeHidden();
  await say(page, 'یہ والا ہٹا دو');
  await expect(page.locator('[data-cart-count]')).toHaveText('0');
});

test('manual and Urdu voice share a cart; missing audio delivery cannot authorize clear', async ({ page }) => {
  await say(page, 'دو کولا شامل کرو');
  await expect(page.locator('[data-cart-count]')).toHaveText('2');
  await panel(page).locator('[data-voice-panel-close]').click();
  await page.locator('[data-menu-item][data-id="side-fries"] [data-add-item]').click();
  await expect(page.locator('[data-cart-count]')).toHaveText('3');
  await page.locator('[data-voice-launcher]').click();
  await say(page, 'کل کتنا ہوا');
  await expect(page.locator('[data-agent-transcript]')).toContainText('فرائز');
  await say(page, 'کارٹ خالی کرو');
  await expect(page.locator('[data-agent-transcript]')).toContainText('کیا کارٹ کی تمام چیزیں');
  await expect(page.locator('[data-cart-count]')).toHaveText('3');
  await say(page, 'جی ہاں');
  // This fixture has a transcription sink but no TTS/playback receipt. A visible
  // transcript alone cannot stand in for the spoken review in voice mode.
  await expect(page.locator('[data-agent-transcript]')).toContainText('تصدیق سے پہلے');
  await expect(page.locator('[data-cart-count]')).toHaveText('3');
  expect((await snapshot(page)).cart.lines).toHaveLength(2);
});
