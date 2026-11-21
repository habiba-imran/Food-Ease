import { test } from 'node:test';
import assert from 'node:assert/strict';
import { PersistentWake } from '../static/js/persistent-wake.mjs';

function fixture({ delayedEnd = false, saved = 'off' } = {}) {
  const instances = [];
  let value = saved, leases = 0;
  const storage = { getItem: () => value, setItem: (_, v) => { value = v; } };
  const make = () => new PersistentWake({ storage, restartMs: 0,
    createRecognition: () => {
      const r = { start() { this.onstart?.(); }, abort() { if (!delayedEnd) this.onend?.(); } };
      instances.push(r);
      return r;
    },
    acquireLease: async () => { leases++; return () => { leases--; }; },
  });
  return { wake: make(), make, instances, saved: () => value, leases: () => leases };
}

test('wake preference survives conversations and reload, but first visit does not capture', async () => {
  const f = fixture();
  await f.wake.setAvailable(true);
  assert.equal(f.instances.length, 0);
  await f.wake.setEnabled(true);
  assert.equal(f.leases(), 1);
  await f.wake.setAvailable(false); // active voice owns capture
  assert.equal(f.leases(), 0);
  await f.wake.setAvailable(true); // conversation ended
  assert.equal(f.leases(), 1);
  await f.wake.setAvailable(false);
  const restored = f.make();
  assert.equal(restored.enabled, true);
  await restored.setAvailable(true);
  assert.equal(f.leases(), 1);
  await restored.setEnabled(false);
  assert.equal(f.saved(), 'off');
  assert.equal(f.leases(), 0);
  assert.equal(f.make().enabled, false);
});

test('manual startup waits for native end; changing availability during stop cannot reopen capture', async () => {
  const f = fixture({ saved: 'on', delayedEnd: true });
  await f.wake.setAvailable(true);
  let stopped = false;
  const stop = f.wake.setAvailable(false).then(() => { stopped = true; });
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.equal(stopped, false);
  assert.equal(f.leases(), 1);
  f.wake.setAvailable(true);
  f.wake.setAvailable(false);
  f.instances[0].onend();
  await stop;
  assert.equal(f.leases(), 0);
  assert.equal(f.instances.length, 1);
});

test('ordinary idle recognition endings keep Hey Zara enabled beyond four cycles', async () => {
  const f = fixture({ saved: 'on' });
  await f.wake.setAvailable(true);
  for (let i = 0; i < 6; i++) {
    f.instances.at(-1).onend();
    await new Promise(resolve => setTimeout(resolve, 5));
  }
  assert.equal(f.instances.length, 7);
  assert.equal(f.wake.listener.enabled, true);
  assert.equal(f.leases(), 1);
  await f.wake.setEnabled(false);
});

test('suspending a pending lease cancels recognition before acquisition completes', async () => {
  let acquired, created = 0, released = false;
  const wake = new PersistentWake({ storage: {getItem: () => 'on'},
    acquireLease: () => new Promise(resolve => { acquired = resolve; }),
    createRecognition: () => { created++; return {}; },
  });
  const starting = wake.setAvailable(true);
  await new Promise(resolve => setTimeout(resolve, 0));
  const stopping = wake.setAvailable(false);
  acquired(() => { released = true; });
  await Promise.all([starting, stopping]);
  assert.equal(created, 0);
  assert.equal(released, true);
});
