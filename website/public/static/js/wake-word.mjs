// Optional browser recognition. Ambient transcripts are discarded, never sent to FoodEase.
// Browser recognition may itself use a remote service; the opt-in explains this.
export function wakeRequest(text) {
  const normalized = text.normalize('NFKC').replace(/[\u064B-\u065F\u0670\u0640\u200C\u200D]/gu, '').trim();
  // زرا is also an ordinary Urdu word, so accept that spelling only after an
  // explicit address. Keep name boundaries and ignore mentions mid-sentence.
  const match = /^(?:(?:hey|hi|hello|ہے|ہی|ہیلو|ہائے)[\s,،]+(?:zara|زارا|زارہ|زرا)|(?:zara|زارا|زارہ))(?=$|[\s,،.!?؟۔])(?:[\s,،]+(?:(?:meri\s+baat\s+)?suno|میری\s+بات\s+سنو|سنو))?[\s,،.!?؟۔]*/iu.exec(normalized);
  return match ? normalized.slice(match[0].length).trim() : null;
}

export class WakeWordListener {
  constructor({ createRecognition, acquireLease = async () => () => {}, onWake = () => {},
                onState = () => {}, stopTimeoutMs = 2000, restartMs = 350, persistIdle = false }) {
    Object.assign(this, { createRecognition, acquireLease, onWake, onState, stopTimeoutMs, restartMs, persistIdle });
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
      this.networkErrors = 0;
      this.recovering = false;
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
      recognition.maxAlternatives = 3;
      recognition.onstart = () => {
        if (this.enabled && !this.recovering && this.recognition === recognition && epoch === this.epoch) {
          this.emit('listening', 'Wake microphone on. Say the assistant’s name, then your request.');
        }
      };
      recognition.onresult = event => {
        if (!this.enabled || this.recovering || this.recognition !== recognition || epoch !== this.epoch) return;
        this.emptyEnds = 0;
        for (let i = event.resultIndex; i < event.results.length; i++) {
          if (!event.results[i].isFinal) continue;
          this.networkErrors = 0;
          let command = null;
          for (let j = 0; j < Math.min(3, event.results[i].length); j++) {
            command = wakeRequest(event.results[i][j].transcript);
            if (command !== null) break;
          }
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
        if (event.error === 'aborted' && this.stopping) return;
        if (event.error === 'network' && this.recovering) return;
        if (event.error === 'network' && this.persistIdle && this.networkErrors < 3) {
          this.recoverNetwork(epoch);
          return;
        }
        if (event.error === 'no-speech') return; // native end schedules a bounded restart
        const message = ['not-allowed', 'service-not-allowed'].includes(event.error)
          ? 'Wake microphone permission is blocked. Allow it in browser settings, or order manually.'
          : 'Wake listening stopped. Your browser may need a connection or support for Urdu. Use Start Zara or order manually.';
        this.enabled = false;
        const errorEpoch = ++this.epoch;
        void this.stopNative().catch(() => {}).finally(() => {
          if (this.epoch === errorEpoch && !this.enabled) this.emit('error', message);
        });
      };
      recognition.onend = () => {
        if (this.recognition !== recognition) return;
        this.recognition = null;
        this.finishStop?.();
        if (this.recovering) return; // stopNative/recoverNetwork own release and reacquisition
        if (!this.enabled || epoch !== this.epoch) { void this.releaseLease(); return; }
        if (++this.emptyEnds > 3 && !this.persistIdle) {
          this.enabled = false;
          void this.releaseLease();
          this.emit('error', 'Wake listening stopped repeatedly. Use Start Voice Assistant or turn wake listening on again.');
          return;
        }
        this.emit('starting', 'Wake microphone is restarting.');
        this.restart = setTimeout(() => this.listen(epoch), this.persistIdle
          ? Math.min(5000, this.restartMs * Math.max(1, this.emptyEnds)) : this.restartMs);
      };
      recognition.start();
    } catch (error) {
      this.recognition = null;
      this.enabled = false;
      void this.releaseLease();
      this.emit('error', error.message || 'Wake listening could not start. Use Start Voice Assistant.');
    }
  }

  recoverNetwork(epoch) {
    this.networkErrors++;
    this.recovering = true;
    this.emit('starting', 'Wake connection lost. Reconnecting Hey Zara…');
    // A fresh recognizer cannot share capture or bypass the tab lease. Wait
    // for native end and lease release, then acquire again with cancellation.
    void this.stopNative().then(async () => {
      if (!this.enabled || epoch !== this.epoch) return;
      const release = await this.acquireLease();
      if (!this.enabled || epoch !== this.epoch) { await release?.(); return; }
      this.release = release;
      this.restart = setTimeout(() => {
        this.recovering = false;
        this.listen(epoch);
      }, Math.min(5000, this.restartMs * 2 ** this.networkErrors));
    }).catch(error => {
      if (!this.enabled || epoch !== this.epoch) return;
      this.enabled = false;
      this.recovering = false;
      ++this.epoch;
      this.emit('error', error.message || 'Wake listening could not reconnect. Use Start Zara.');
    });
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
    this.recovering = false;
    await this.stopNative();
    this.emit('off', 'Wake microphone off. Use Start Voice Assistant, or enable wake listening.');
  }
}
