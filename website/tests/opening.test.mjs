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

test('explicit retry finishes pending server cleanup before starting one replacement', async () => {
  const { c, calls } = fixture();
  const original = c.api;
  let stops = 0;
  c.api = async (name, ...args) => {
    if (name === 'end' && ++stops === 1) throw new Error('offline');
    return original(name, ...args);
  };
  await c.start({ mode: 'voice' });
  await c.end();
  assert.equal(c.current.serverPending, true);
  await c.start({ mode: 'voice' });
  assert.equal(c.state, 'voice_active');
  assert.equal(stops, 2);
  assert.equal(calls.filter(([name]) => name === 'start').length, 2);
  await c.end();
});

test('permission completion updates microphone feedback before server preparation resolves', async () => {
  const track = { kind: 'audio', enabled: true, readyState: 'live', stop() { this.readyState = 'ended'; } };
  const { c, states } = fixture({ permission: async () => ({ getTracks: () => [track], getAudioTracks: () => [track] }) });
  await c.start({ mode: 'voice' });
  assert.equal(states.some(state => state.state === 'connecting' && state.microphoneActive), true);
  await c.end();
  assert.equal(states.at(-1).microphoneActive, false);
});

test('manual during a pending cleanup retry prevents a late microphone restart', async () => {
  const { c, calls } = fixture();
  const original = c.api;
  let release, entered;
  const waiting = new Promise(resolve => { entered = resolve; });
  const hold = new Promise(resolve => { release = resolve; });
  let stops = 0;
  c.api = async (name, ...args) => {
    if (name === 'end') {
      stops++;
      if (stops === 1) throw new Error('offline');
      if (stops === 2) { entered(); await hold; }
    }
    return original(name, ...args);
  };
  await c.start({ mode: 'voice' });
  await c.end();
  const retry = c.start({ mode: 'voice' });
  await waiting;
  const ending = c.end(); // Shares the in-flight cleanup instead of sending another end.
  release();
  await ending;
  await assert.rejects(retry, /cancelled/);
  assert.equal(calls.filter(([name]) => name === 'media').length, 1);
});
