import { test } from 'node:test';
import assert from 'node:assert/strict';
import { LiveKitSeats } from '../static/js/livekit-bridge.mjs';

function fixture(onControl = () => {}) {
  const calls = [], handlers = new Map();
  class Room {
    constructor() {
      this.remoteParticipants = new Map();
      this.localParticipant = { unpublishTrack: async () => { calls.push('unpublish'); } };
    }
    on(name, handler) { handlers.set(name, handler); }
    async disconnect() { calls.push('disconnect'); }
  }
  const seats = new LiveKitSeats({
    prepared: { session_id: 's', generation: 'g', binding: { agent_identity: 'agent' } },
    application: { subscribe: () => () => {} }, sdk: { Room }, mode: 'voice',
    media: { getTracks: () => [{ stop() { calls.push('stop'); } }] },
    transcript: { update() {} }, onControl,
  });
  return { seats, calls };
}

test('disconnect stops capture without negotiating unpublish against a closing PC', async () => {
  const { seats, calls } = fixture();
  await seats.disconnect();
  assert.ok(calls.includes('stop'));
  assert.equal(calls.includes('unpublish'), false);
  assert.equal(calls.filter(x => x === 'disconnect').length, 2);
});

test('async worker controls cannot leak an unhandled closed-PC rejection', async () => {
  const { seats } = fixture(async () => { throw new Error('PC manager is closed'); });
  const agent = { identity: 'agent', attributes: { 'foodease.role': 'agent', 'foodease.session': 's', 'foodease.generation': 'g' } };
  const event = { schema_version: '2.0', session_id: 's', event_id: 'e', type: 'agent.control', payload: { intent: 'pause' } };
  seats.receive(new TextEncoder().encode(JSON.stringify(event)), agent, 'foodease.events.v2');
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(seats.closed, true);
});

test('abort during app join stops capture now and waits for join before closing SDK PCs', async () => {
  let resolveJoin;
  const joining = new Promise(resolve => { resolveJoin = resolve; });
  const calls = [];
  class Room {
    constructor() { this.remoteParticipants = new Map(); this.localParticipant = {}; }
    on() {}
    async connect() { calls.push('join'); await joining; }
    async disconnect() { calls.push('disconnect'); }
  }
  const abort = new AbortController();
  const seats = new LiveKitSeats({ prepared: { session_id:'s', generation:'g', livekit_url:'wss://offline.invalid', tokens:{app:{token:'fake'}} },
    application:{subscribe:()=>()=>{}}, sdk:{Room,RoomEvent:{}}, mode:'voice',
    media:{getTracks:()=>[{stop(){calls.push('stop');}}]}, transcript:{} });
  const connecting = seats.connect(abort.signal);
  const rejected = assert.rejects(connecting, /cancelled/);
  abort.abort();
  assert.ok(calls.includes('stop'));
  assert.equal(calls.includes('disconnect'), false);
  resolveJoin();
  await rejected;
  assert.deepEqual(calls.filter(x=>x!=='stop'), ['join','disconnect','disconnect']);
});
