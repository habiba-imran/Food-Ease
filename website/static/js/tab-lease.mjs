// Hold a browser-native lock across the entire assistance lifetime, including cleanup.
export async function acquireTabLease(sessionId, locks = globalThis.navigator?.locks) {
  if (!locks) return () => {}; // Server-side generation admission remains mandatory.
  let acquired, rejected, release;
  const ready = new Promise((resolve, reject) => { acquired = resolve; rejected = reject; });
  const held = new Promise(resolve => { release = resolve; });
  const request = locks.request(`foodease.assistance:${sessionId}`, { ifAvailable: true }, async lock => {
    if (!lock) { rejected(new Error("Assistance is already open in another tab. End it there first.")); return; }
    acquired(() => { release(); return request; });
    await held;
  });
  void request.catch(rejected);
  return ready;
}
