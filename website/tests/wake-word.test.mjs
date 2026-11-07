import { test } from 'node:test';
import assert from 'node:assert/strict';
import { WakeWordListener, wakeRequest } from '../static/js/wake-word.mjs';

function fixture({ delayedEnd = false, createRecognition, acquireLease } = {}) {
  const instances = [], states = [], wakes = [];
  let releases = 0;
  class Recognition {
    start() { this.onstart?.(); }
    abort() { this.aborted = true; if (!delayedEnd) this.onend?.(); }
    result(text, final = true) {
      const result = Object.assign([{ transcript: text, confidence: 0.95 }], { isFinal: final });
      this.onresult?.({ resultIndex: 0, results: [result] });
    }
  }
  const listener = new WakeWordListener({
    createRecognition: createRecognition || (() => { const r = new Recognition(); instances.push(r); return r; }),
    acquireLease: acquireLease || (async () => () => { releases++; }),
    onState: state => states.push(state), onWake: command => wakes.push(command), stopTimeoutMs: 20, restartMs: 0,
  });
  return { listener, instances, states, wakes, releases: () => releases };
}
const settle = () => new Promise(resolve => setTimeout(resolve, 0));

test('wake addresses are bounded words, in Roman Urdu or Urdu script', () => {
  for (const text of ['Hey Zara', 'Zara', 'Zara, suno', 'Zara meri baat suno', 'زارا', 'ہے زارا', 'زارا، سنو']) {
    assert.equal(wakeRequest(text), '');
  }
  assert.equal(wakeRequest('Hey Zara, add two drinks'), 'add two drinks');
  assert.equal(wakeRequest('زارا، دو جوس ایڈ کر دو'), 'دو جوس ایڈ کر دو');
  for (const text of ['zaraasa', 'bazaar', 'I was talking to Zara yesterday', 'ذرا نمک دینا']) {
    assert.equal(wakeRequest(text), null);
  }
});

test('ambient and interim speech stay out of the assistant; repeated wake triggers once', async () => {
  const f = fixture();
  await f.listener.start();
  assert.equal(f.instances[0].lang, 'ur-PK');
  f.instances[0].result('Hey Zara', false);
  f.instances[0].result('some ambient conversation');
  assert.deepEqual(f.wakes, []);
  f.instances[0].result('Hey Zara, add two drinks');
  f.instances[0].result('Hey Zara, add two drinks');
  await settle();
  assert.deepEqual(f.wakes, ['add two drinks']);
  assert.equal(f.releases(), 1);
  assert.equal(f.listener.enabled, false);
});

test('handoff waits for native recognition to end; late results cannot activate', async () => {
  const f = fixture({ delayedEnd: true });
  await f.listener.start();
  const stopping = f.listener.stop();
  f.instances[0].result('Hey Zara');
  assert.deepEqual(f.wakes, []);
  assert.equal(f.releases(), 0);
  f.instances[0].onend();
  await stopping;
  assert.equal(f.releases(), 1);
});

test('manual cancellation during wake handoff cancels pending activation', async () => {
  const f = fixture({ delayedEnd: true });
  await f.listener.start();
  f.instances[0].result('Hey Zara');
  const stopping = f.listener.stop();
  f.instances[0].onend();
  await stopping;
  await settle();
  assert.deepEqual(f.wakes, []);
});

test('a permission error disables listening without a restart or wake', async () => {
  const f = fixture();
  await f.listener.start();
  f.instances[0].onerror({ error: 'not-allowed' });
  await settle();
  assert.equal(f.listener.enabled, false);
  assert.match(f.states.at(-1).message, /permission/i);
  assert.deepEqual(f.wakes, []);
  assert.equal(f.instances.length, 1);
});

test('unsupported browsers and held leases do not claim to listen', async () => {
  const unsupported = fixture({ createRecognition: () => null });
  await unsupported.listener.start();
  assert.equal(unsupported.listener.enabled, false);
  assert.match(unsupported.states.at(-1).message, /not available/i);
  const busy = fixture({ acquireLease: async () => { throw new Error('Another tab is listening.'); } });
  await busy.listener.start();
  assert.equal(busy.instances.length, 0);
  assert.match(busy.states.at(-1).message, /another tab/i);
});

test('cancellation while acquiring a lease never opens recognition', async () => {
  let acquired, released = false;
  const f = fixture({ acquireLease: () => new Promise(resolve => { acquired = resolve; }) });
  const starting = f.listener.start();
  await settle();
  await f.listener.stop();
  acquired(() => { released = true; });
  await starting;
  assert.equal(f.instances.length, 0);
  assert.equal(released, true);
});

test('missing native end fails closed and prevents a second microphone owner', async () => {
  const f = fixture({ delayedEnd: true });
  await f.listener.start();
  await assert.rejects(f.listener.stop(), /still closing/i);
  assert.equal(f.releases(), 0);
  await f.listener.start();
  assert.equal(f.instances.length, 1);
  f.instances[0].onend();
  await f.listener.stop();
  assert.equal(f.releases(), 1);
});

test('repeated empty native endings stop instead of restarting indefinitely', async () => {
  const f = fixture();
  await f.listener.start();
  for (let i = 0; i < 4; i++) {
    f.instances.at(-1).onend();
    await settle();
  }
  assert.equal(f.instances.length, 4);
  assert.equal(f.listener.enabled, false);
  assert.match(f.states.at(-1).message, /stopped repeatedly/);
  assert.equal(f.releases(), 1);
});

test('wake handoff waits for the asynchronous tab lease release as well as native end', async () => {
  let released;
  const f = fixture({ acquireLease: async () => () => new Promise(resolve => { released = resolve; }) });
  await f.listener.start();
  f.instances[0].result('Hey Zara');
  await settle();
  assert.deepEqual(f.wakes, []);
  released();
  await settle();
  assert.deepEqual(f.wakes, ['']);
});
