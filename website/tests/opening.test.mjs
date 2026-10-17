import { test } from 'node:test';
import assert from 'node:assert/strict';
import { AssistanceController } from '../static/js/assistance-controller.mjs';

function fixture({ permission, playback } = {}) {
  const states = [], calls = [];
  const c = new AssistanceController({ newId: () => crypto.randomUUID(), pollMs: 0,
    onState: (s) => states.push(s),
    acquireMedia: async (mode) => { calls.push(['media', mode]); return permission ? permission() : { getTracks: () => [] }; },
    api: async (name) => { calls.push([name]); return { state: name === 'start' ? 'preparing' : name === 'end' ? 'ended' : 'active', generation: 'g' }; },
    connectSeats: async () => ({ registerApp: async () => {}, publishFreshContext: async () => ({ revision: 1 }),
      playbackReady: playback || (async () => {}), activate: async (...args) => calls.push(['activate', ...args]),
      closeAudio() {}, disconnect() {} }) });
  return { c, states, calls };
}
test('fresh/manual requires no media or dispatch; chooser waits for explicit start', async () => {
  const { c, calls } = fixture();
  assert.equal(c.state, 'awaiting_spoken_choice_consent');
  await c.end();
  assert.equal(c.state, 'manual');
  assert.deepEqual(calls, []);
});
test('chooser and resumed direct mode have distinct activation; double start is shared', async () => {
  const { c, calls } = fixture();
  const p = c.start({ mode: 'choice' });
  assert.equal(c.start({ mode: 'choice' }), p);
  await p;
  assert.equal(c.state, 'choosing_mode');
  await c.end();
  await c.start({ mode: 'typed' });
  assert.equal(c.state, 'typed_active');
  assert.deepEqual(calls.filter(([name]) => name === 'activate'), [['activate', 'choice', false], ['activate', 'typed', true]]);
  await c.end();
});
test('autoplay rejection ends resources and never activates', async () => {
  const { c, calls } = fixture({ playback: async () => { throw new Error('autoplay blocked'); } });
  await assert.rejects(c.start({ mode: 'choice' }), /autoplay/);
  assert.equal(c.state, 'error');
  assert.equal(calls.some(([n]) => n === 'activate'), false);
  assert.equal(calls.some(([n]) => n === 'end'), true);
});
test('paused, reconnecting and ended states cannot create another dispatch', async () => {
  const { c, calls } = fixture();
  await c.start({ mode: 'voice' });
  c.setPhase('paused');
  assert.equal(c.state, 'paused');
  c.setPhase('reconnecting');
  assert.equal(c.state, 'reconnecting');
  c.modeChanged('voice');
  assert.equal(c.state, 'voice_active');
  await c.end({ state: 'ended' });
  assert.equal(c.state, 'ended');
  c.modeChanged('typed');
  assert.equal(c.state, 'ended');
  assert.equal(calls.filter(([n]) => n === 'start').length, 1);
});
