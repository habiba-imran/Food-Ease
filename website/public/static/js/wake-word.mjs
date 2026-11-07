// Optional browser recognition. Ambient transcripts are discarded, never sent to FoodEase.
// Browser recognition may itself use a remote service; the opt-in explains this.
export function wakeRequest(text) {
  const normalized = text.normalize('NFKC').trim();
  const match = /^(?:(?:hey|hi|hello|ہے|ہی|ہیلو)\s+)?(?:zara|زارا)(?=$|[\s,،.!!?؟۔])(?:[\s,،]+(?:(?:meri\s+baat\s+)?suno|میری\s+بات\s+سنو|سنو))?[\s,،.!!?؟۔]*/iu.exec(normalized);
  return match ? normalized.slice(match[0].length).trim() : null;
}

export class WakeWordListener {
  constructor({ createRecognition, acquireLease = async () => () => {}, onWake = () => {},
                onState = () => {}, stopTimeoutMs = 2000, restartMs = 350 }) {
    Object.assign(this, { createRecognition, acquireLease, onWake, onState, stopTimeoutMs, restartMs });
    this.enabled = false;
    this.epoch = 0;
    this.emptyEnds = 0;
    this.recognition = null;
  }

  emit(state, message) { this.onState({ state, message, enabled: this.enabled }); }

  async start() {
    if (this.enabled || this.starting) return;
    if (this.recognition) {
      this.emit('error', 'Wake microphone is still closing. Wait, or reload before starting voice.');
      return;
    }
    this.enabled = true;
    this.starting = true;
    const epoch = ++this.epoch;
    this.emit('starting', 'Starting wake listening. Allow microphone access if your browser asks.');
    try {
      await this.releasing;
      if (!this.enabled || epoch !== this.epoch) return;
      const release = await this.acquireLease();
      if (!this.enabled || epoch !== this.epoch) { await release?.(); return; }
      this.release = release;
      this.emptyEnds = 0;
      this.listen(epoch);
    } catch (error) {
      this.enabled = false;
      this.emit('error', error.message || 'Wake listening could not start. Use Start Voice Assistant.');
    } finally { this.starting = false; }
  }

  listen(epoch) {
    if (!this.enabled || epoch !== this.epoch) return;
    try {
      const recognition = this.createRecognition();
      if (!recognition) throw new Error('Wake listening is not available in this browser. Use Start Voice Assistant.');
      this.recognition = recognition;
      recognition.lang = 'ur-PK';
      recognition.continuous = true;
      recognition.interimResults = false;
      recognition.onstart = () => {
        if (this.enabled && this.recognition === recognition && epoch === this.epoch) {
          this.emit('listening', 'Wake microphone on. Say the assistant’s name, then your request.');
        }
      };
      recognition.onresult = event => {
        if (!this.enabled || this.recognition !== recognition || epoch !== this.epoch) return;
        this.emptyEnds = 0;
        for (let i = event.resultIndex; i < event.results.length; i++) {
          if (!event.results[i].isFinal) continue;
          const command = wakeRequest(event.results[i][0].transcript);
          if (command === null) continue;
          this.enabled = false; // latch before abort; repeated results cannot activate twice
          this.emit('stopping', 'Zara is connecting. Wake microphone is closing.');
          void this.stopNative().then(() => {
            if (epoch === this.epoch) return this.onWake(command);
          }).catch(() => {}); // stopNative supplies an accessible error
          break;
        }
      };
      recognition.onerror = event => {
        if (this.recognition !== recognition || !this.enabled) return;
        if (event.error === 'no-speech') return; // native end schedules a bounded restart
        const message = ['not-allowed', 'service-not-allowed'].includes(event.error)
          ? 'Wake microphone permission is blocked. Allow it in browser settings, or use typing.'
          : 'Wake listening stopped. Your browser may need a connection or support for Urdu. Use Start Voice Assistant or typing.';
        this.enabled = false;
        ++this.epoch;
        void this.stopNative().catch(() => {}).finally(() => this.emit('error', message));
      };
      recognition.onend = () => {
        if (this.recognition !== recognition) return;
        this.recognition = null;
        this.finishStop?.();
        if (!this.enabled || epoch !== this.epoch) { void this.releaseLease(); return; }
        if (++this.emptyEnds > 3) {
          this.enabled = false;
          void this.releaseLease();
          this.emit('error', 'Wake listening stopped repeatedly. Use Start Voice Assistant or turn wake listening on again.');
          return;
        }
        this.emit('starting', 'Wake microphone is restarting.');
        this.restart = setTimeout(() => this.listen(epoch), this.restartMs);
      };
      recognition.start();
    } catch (error) {
      this.recognition = null;
      this.enabled = false;
      void this.releaseLease();
      this.emit('error', error.message || 'Wake listening could not start. Use Start Voice Assistant.');
    }
  }

  async releaseLease() {
    if (this.releasing) return this.releasing;
    const release = this.release;
    this.release = null;
    if (!release) return;
    this.releasing = Promise.resolve().then(() => release()).finally(() => { this.releasing = null; });
    return this.releasing;
  }

  stopNative() {
    clearTimeout(this.restart);
    if (!this.recognition) return this.releaseLease();
    if (this.stopping) return this.stopping;
    let timer;
    const stopped = new Promise(resolve => { this.finishStop = resolve; });
    this.stopping = Promise.race([
      stopped,
      new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('Wake microphone is still closing. Reload before starting voice.')), this.stopTimeoutMs); }),
    ]).then(() => this.releaseLease()).catch(error => {
      this.emit('error', error.message);
      throw error; // never open LiveKit capture unless native recognition ended
    }).finally(() => { clearTimeout(timer); this.stopping = null; });
    try { this.recognition.abort(); } catch { /* Wait for end or fail closed. */ }
    return this.stopping;
  }

  async stop() {
    ++this.epoch; // also cancels a wake awaiting native microphone release
    this.enabled = false;
    await this.stopNative();
    this.emit('off', 'Wake microphone off. Use Start Voice Assistant, or enable wake listening.');
  }
}
