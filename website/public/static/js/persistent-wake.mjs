import { WakeWordListener } from './wake-word.mjs?v=wake-4';

// Keep the user's preference across conversations. Native wake recognition and
// the voice session share the same tab lease and never capture together.
export class PersistentWake {
  constructor({ storage, onState = () => {}, ...options }) {
    this.storage = storage;
    this.key = 'foodease.hey-zara.v1';
    try { this.enabled = storage?.getItem(this.key) === 'on'; } catch { this.enabled = false; }
    this.available = false;
    this.state = { state: 'off', message: '' };
    this.listener = new WakeWordListener({ ...options, persistIdle: true, onState: state => {
      this.state = state;
      onState(state);
    } });
  }
  setEnabled(enabled) {
    this.enabled = enabled;
    try { this.storage?.setItem(this.key, enabled ? 'on' : 'off'); } catch { /* Optional storage. */ }
    const stopped = enabled ? Promise.resolve() : this.listener.stop();
    return Promise.all([stopped, this.reconcile()]);
  }
  setAvailable(available) {
    this.available = available;
    // Cancel an in-flight lease acquisition immediately, even while the
    // serialized reconciliation is awaiting it (hidden page/manual startup).
    const stopped = available ? Promise.resolve() : this.listener.stop();
    return Promise.all([stopped, this.reconcile()]);
  }
  reconcile() {
    this.dirty = true;
    if (!this.task) this.task = (async () => {
      // Coalesce lifecycle notifications before acquiring the microphone lease.
      await Promise.resolve();
      while (this.dirty) {
        this.dirty = false;
        if (this.enabled && this.available) await this.listener.start();
        else await this.listener.stop();
      }
    })().finally(() => {
      this.task = null;
      if (this.dirty) return this.reconcile();
    });
    return this.task;
  }
}
