// Bound lifecycle owner; the bridge supplies SDK seats and application rendering.
export class AssistanceController {
  constructor({ api, acquireMedia, connectSeats, onState = () => {}, timeoutMs = 30000,
                pollMs = 1000, monitorMs = 15000, storage = null, sessionId = null,
                acquireLease = () => null, newId = () => crypto.randomUUID() }) {
    Object.assign(this, { api, acquireMedia, connectSeats, onState, timeoutMs, pollMs, monitorMs, storage, acquireLease, newId });
    this.ownerKey = `foodease.assistance-owner.v2:${sessionId}`;
    try {
      const saved = JSON.parse(storage?.getItem(this.ownerKey) || "null");
      if (typeof saved?.request_id === "string" && saved.request_id.length <= 128
          && (!saved.generation || typeof saved.generation === "string" && saved.generation.length <= 128)) this.orphan = saved;
    } catch { /* Storage unavailable; server admission still prevents duplicates. */ }
    this.current = null;
    this.state = "awaiting_spoken_choice_consent";
    this.hasActivated = false;
  }

  start({ mode = "voice" } = {}) {
    if (!["choice", "voice", "typed"].includes(mode)) return Promise.reject(new Error("Invalid assistance mode."));
    const stopEpoch = this.stopEpoch || 0;
    if (this.orphan) return this.recover().then(() => {
      if ((this.stopEpoch || 0) !== stopEpoch) throw new Error("Assistance start cancelled.");
      return this.start({ mode });
    });
    if (this.current && !this.current.cancelled) return this.current.promise;
    if (this.current?.serverPending) {
      if (!this.cleanupRetry) this.cleanupRetry = this._serverStop(this.current).then(() => {
        if ((this.stopEpoch || 0) !== stopEpoch) throw new Error("Assistance start cancelled.");
        if (this.current?.serverPending) throw new Error("Cleanup is still pending. Retry when connected; your microphone is off.");
        return this.start({ mode });
      }).finally(() => { this.cleanupRetry = null; });
      return this.cleanupRetry;
    }
    const run = { request_id: this.newId(), mode, cancelled: false, sent: false,
                  media: null, seats: null, generation: null, serverPending: false,
                  abort: new AbortController() };
    this.current = run;
    run.promise = this._start(run);
    return run.promise;
  }

  recover() {
    if (!this.orphan) return this.recoveryPromise || Promise.resolve();
    if (this.recoveryPromise) return this.recoveryPromise;
    this.recoveryPromise = (async () => {
      const releaseLease = await this.acquireLease();
      const run = { ...this.orphan, cancelled: true, sent: true, serverPending: true,
        abort: new AbortController(), releaseLease };
      this.orphan = null;
      this.current = run;
      const result = await this._serverStop(run);
      if (!run.serverPending) this.current = null;
      return result;
    })().finally(() => { this.recoveryPromise = null; });
    return this.recoveryPromise;
  }

  _save(run) {
    if (this.current !== run) return;
    try {
      if (run.serverPending || run.sent && !run.cancelled) this.storage?.setItem(this.ownerKey,
        JSON.stringify({ request_id: run.request_id, ...(run.generation ? { generation: run.generation } : {}) }));
      else this.storage?.removeItem(this.ownerKey);
    } catch { /* No credentials or business arguments are persisted. */ }
  }

  _watch(run, ttl) {
    if (Number.isFinite(ttl) && ttl > 0) {
      run.expiry = setTimeout(() => {
        if (run.cancelled) return;
        this._localStop(run);
        void this._serverStop(run);
        this._emit(run, { state: "error", localStopped: true,
          detail: "Assistance credentials expired. Choose voice or typing again when ready." });
      }, Math.min(ttl * 1000, 2147483647));
      run.expiry.unref?.();
    }
    const poll = async () => {
      if (run.cancelled) return;
      try {
        const status = await this.api("status", { request_id: run.request_id }, run.abort.signal);
        if (run.cancelled) return;
        if (status.state !== "active") throw new Error("Assistance expired.");
      } catch {
        if (!run.cancelled) {
          this._localStop(run); void this._serverStop(run);
          this._emit(run, { state: "manual", localStopped: true,
            detail: "Assistance lost its connection. Manual ordering remains available." });
        }
      }
      if (!run.cancelled) { run.monitor = setTimeout(poll, this.monitorMs); run.monitor.unref?.(); }
    };
    run.monitor = setTimeout(poll, this.monitorMs);
    run.monitor.unref?.();
  }

  _check(run) {
    if (run.cancelled) throw new Error("Assistance start cancelled.");
  }

  _emit(run, state) {
    if (this.current !== run) return;
    this.state = state.modeState || state.state;
    const microphoneActive = !run.cancelled && (run.media?.getAudioTracks?.() || [])
      .some(track => track.readyState !== "ended" && track.enabled !== false);
    this.onState({ ...state, modeState: this.state, microphoneActive });
  }

  modeChanged(mode) {
    const run = this.current;
    if (!run || run.cancelled) return;
    run.mode = mode;
    this._emit(run, { state: "active", modeState: mode === "choice" ? "choosing_mode" : `${mode}_active`, localStopped: false });
  }

  setPhase(state) {
    if (this.current && !this.current.cancelled) this._emit(this.current, { state, localStopped: false });
  }

  _localStop(run) {
    run.cancelled = true;
    run.abort.abort();
    clearTimeout(run.monitor);
    clearTimeout(run.expiry);
    for (const track of run.media?.getTracks() || []) track.stop();
    if (run.seats && run.closedSeats !== run.seats) {
      run.closedSeats = run.seats;
      run.seats.closeAudio?.();
      // Invocation is immediate; remote disconnect cannot delay track.stop.
      Promise.resolve(run.seats.disconnect?.()).catch(() => {});
    }
    this._emit(run, { state: "manual", modeState: run.stopPhase || "manual", localStopped: true, serverCleanupPending: run.serverPending });
  }

  async _serverStop(run) {
    if (!run.sent) { await run.releaseLease?.(); return; }
    run.serverPending = true;
    this._save(run);
    try {
      const result = await this.api("end", { request_id: run.request_id,
        ...(run.generation ? { generation: run.generation } : {}) });
      run.serverPending = result.state !== "ended";
      this._save(run);
      if (!run.serverPending) { await run.releaseLease?.(); run.releaseLease = null; }
      this._emit(run, { state: "manual", modeState: run.stopPhase || "manual", localStopped: true, serverCleanupPending: run.serverPending });
      return result;
    } catch {
      this._emit(run, { state: "manual", modeState: run.stopPhase || "manual", localStopped: true, serverCleanupPending: true });
      return { state: "cleanup_pending" };
    }
  }

  async _start(run) {
    const deadline = setTimeout(() => { this._localStop(run); void this._serverStop(run); }, this.timeoutMs);
    try {
      const lease = this.acquireLease();
      run.releaseLease = typeof lease?.then === "function" ? await lease : lease;
      this._check(run);
      this._emit(run, { state: "requesting_permission", modeState: "connecting", localStopped: false });
      run.media = await this.acquireMedia(run.mode);
      this._check(run);
      this._emit(run, { state: "connecting", localStopped: false });
      run.sent = true;
      this._save(run);
      const prepared = await this.api("start", { request_id: run.request_id, consent: true }, run.abort.signal);
      const expiresAt = Number.isFinite(prepared.ttl_seconds) ? Date.now() + prepared.ttl_seconds * 1000 : null;
      run.generation = prepared.generation;
      this._save(run);
      this._check(run);
      if (prepared.state !== "preparing") throw new Error("Assistance generation is unavailable.");
      run.seats = await this.connectSeats(prepared, run.media, run.abort.signal, run.mode);
      run.seats.onDisconnected?.(() => {
        this._localStop(run);
        void this._serverStop(run);
      });
      this._check(run);
      await run.seats.registerApp();
      this._check(run);
      const context = await run.seats.publishFreshContext();
      this._check(run);
      await run.seats.playbackReady();
      this._check(run);
      await this.api("ready", { request_id: run.request_id, generation: run.generation,
        context_revision: context.revision, media_ready: true, playback_ready: true,
        app_ready: true }, run.abort.signal);
      this._check(run);
      while (!run.cancelled) {
        const status = await this.api("status", { request_id: run.request_id }, run.abort.signal);
        this._check(run);
        if (status.state === "active") {
          if (expiresAt !== null && Date.now() >= expiresAt) throw new Error("Assistance credentials expired. Start again when ready.");
          await run.seats.activate?.(run.mode, this.hasActivated);
          this._check(run);
          this.hasActivated = true;
          this._watch(run, expiresAt === null ? null : Math.max(0.001, (expiresAt - Date.now()) / 1000));
          this._emit(run, { state: "active", modeState: run.mode === "choice" ? "choosing_mode" : `${run.mode}_active`, localStopped: false });
          return status;
        }
        if (["ended", "cleanup_pending"].includes(status.state)) throw new Error("Assistance unavailable.");
        await new Promise((resolve) => setTimeout(resolve, this.pollMs));
      }
      this._check(run);
    } catch (error) {
      this._localStop(run);
      await this._serverStop(run);
      if (this.current === run && !run.userEnded) this._emit(run, { state: "error", localStopped: true });
      throw error;
    } finally {
      clearTimeout(deadline);
    }
  }

  end({ state = "manual" } = {}) {
    this.stopEpoch = (this.stopEpoch || 0) + 1;
    const run = this.current;
    if (!run) { this.state = state; this.onState({ state: "manual", modeState: state, localStopped: true }); return Promise.resolve({ state: "ended" }); }
    run.userEnded = true;
    run.stopPhase ||= state;
    this._localStop(run);
    return this._serverStop(run);
  }

  disconnected() { return this.end(); }
}
