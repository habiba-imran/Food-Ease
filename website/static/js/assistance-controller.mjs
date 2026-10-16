// Phase 3 lifecycle only. SDK seat/render wiring is supplied by Phase 5.
export class AssistanceController {
  constructor({ api, acquireMedia, connectSeats, onState = () => {}, timeoutMs = 30000,
                pollMs = 1000, newId = () => crypto.randomUUID() }) {
    Object.assign(this, { api, acquireMedia, connectSeats, onState, timeoutMs, pollMs, newId });
    this.current = null;
  }

  start() {
    if (this.current && !this.current.cancelled) return this.current.promise;
    if (this.current?.serverPending) return Promise.reject(new Error("Cleanup is still pending."));
    const run = { request_id: this.newId(), cancelled: false, sent: false,
                  media: null, seats: null, generation: null, serverPending: false,
                  abort: new AbortController() };
    this.current = run;
    run.promise = this._start(run);
    return run.promise;
  }

  _check(run) {
    if (run.cancelled) throw new Error("Assistance start cancelled.");
  }

  _emit(run, state) { if (this.current === run) this.onState(state); }

  _localStop(run) {
    run.cancelled = true;
    run.abort.abort();
    for (const track of run.media?.getTracks() || []) track.stop();
    if (run.seats && run.closedSeats !== run.seats) {
      run.closedSeats = run.seats;
      run.seats.closeAudio?.();
      // Invocation is immediate; remote disconnect cannot delay track.stop.
      Promise.resolve(run.seats.disconnect?.()).catch(() => {});
    }
    this._emit(run, { state: "manual", localStopped: true, serverCleanupPending: run.serverPending });
  }

  async _serverStop(run) {
    if (!run.sent) return;
    run.serverPending = true;
    try {
      const result = await this.api("end", { request_id: run.request_id,
        ...(run.generation ? { generation: run.generation } : {}) });
      run.serverPending = result.state !== "ended";
      this._emit(run, { state: "manual", localStopped: true, serverCleanupPending: run.serverPending });
      return result;
    } catch {
      this._emit(run, { state: "manual", localStopped: true, serverCleanupPending: true });
      return { state: "cleanup_pending" };
    }
  }

  async _start(run) {
    const deadline = setTimeout(() => { this._localStop(run); void this._serverStop(run); }, this.timeoutMs);
    try {
      this.onState({ state: "requesting_permission", localStopped: false });
      run.media = await this.acquireMedia();
      this._check(run);
      run.sent = true;
      const prepared = await this.api("start", { request_id: run.request_id, consent: true }, run.abort.signal);
      run.generation = prepared.generation;
      this._check(run);
      if (prepared.state !== "preparing") throw new Error("Assistance generation is unavailable.");
      run.seats = await this.connectSeats(prepared, run.media, run.abort.signal);
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
          this.onState({ state: "active", localStopped: false });
          return status;
        }
        if (["ended", "cleanup_pending"].includes(status.state)) throw new Error("Assistance unavailable.");
        await new Promise((resolve) => setTimeout(resolve, this.pollMs));
      }
      this._check(run);
    } catch (error) {
      this._localStop(run);
      await this._serverStop(run);
      throw error;
    } finally {
      clearTimeout(deadline);
    }
  }

  end() {
    const run = this.current;
    if (!run) return Promise.resolve({ state: "ended" });
    this._localStop(run);
    return this._serverStop(run);
  }

  disconnected() { return this.end(); }
}
