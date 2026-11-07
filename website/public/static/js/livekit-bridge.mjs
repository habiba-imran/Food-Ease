import { bounded, correlated, newId, timestamp } from "./application.mjs";

const TOPICS = { context: "foodease.context.v2", control: "foodease.control.v2", text: "foodease.text_input.v2" };
export class LiveKitSeats {
  constructor({ prepared, application, sdk, media, mode, transcript, onStatus = () => {},
                onControl = () => {}, document = globalThis.document }) {
    Object.assign(this, { prepared, application, sdk, media, mode, transcript, onStatus, onControl, document });
    this.app = new sdk.Room();
    this.user = new sdk.Room();
    this.audio = new Map();
    this.remoteAudio = new Map();
    this.typedAudio = false;
    this.paused = false;
    this.closed = false;
    this.recovering = false;
    this.reconnectingSeats = new Set();
    this.recoverySerial = 0;
    this.disconnectedListeners = new Set();
    this.seenEvents = new Set();
    this.lastContextRevision = -1;
    this.lastStatusTimestamp = "";
    this.unsubscribe = application.subscribe((snapshot, turnId) => this.publishContext(snapshot, turnId));
  }
  bound(participant, role) {
    const attrs = participant?.attributes;
    return participant?.identity === this.prepared.binding[`${role}_identity`]
      && attrs?.["foodease.role"] === role
      && attrs?.["foodease.session"] === this.prepared.session_id
      && attrs?.["foodease.generation"] === this.prepared.generation;
  }
  assertCaller(data, readOnly = false) {
    const participant = [...this.app.remoteParticipants.values()].find((p) => p.identity === data.callerIdentity);
    if (this.closed || !this.bound(participant, "agent")) throw new Error("Unbound application caller.");
    if ((this.recovering || this.paused) && !readOnly) throw new Error("Assistance is paused; new changes are unavailable.");
  }
  envelope(type, payload, extra = {}) {
    return { schema_version: "2.0", session_id: this.prepared.session_id, event_id: newId(),
      timestamp: timestamp(), type, payload, ...extra };
  }
  async connect(signal) {
    const { RoomEvent: E } = this.sdk;
    const check = () => { if (signal?.aborted || this.closed) throw new Error("Assistance start cancelled."); };
    this.user.on(E.DataReceived, (raw, participant, _kind, topic) => this.receive(raw, participant, topic));
    this.user.on(E.TrackSubscribed, (track, publication, participant) => {
      if (!this.bound(participant, "agent") || track.kind !== "audio" || this.closed) return;
      this.remoteAudio.set(publication.trackSid, track);
      this.attachAudio(publication.trackSid, track);
    });
    this.user.on(E.TrackUnsubscribed, (_track, publication) => {
      this.remoteAudio.delete(publication.trackSid);
      this.detachAudio(publication.trackSid);
    });
    for (const seat of [this.app, this.user]) {
      seat.on(E.Disconnected, () => {
        if (this.closed) return;
        this.closeAudio();
        for (const listener of this.disconnectedListeners) listener();
      });
      seat.on(E.ParticipantDisconnected, (participant) => {
        if (this.closed || participant?.identity !== this.prepared.binding.agent_identity) return;
        this.failConnection("The assistant disconnected. Manual ordering remains available.");
      });
      seat.on(E.Reconnecting, () => this.beginReconnect(seat));
      seat.on(E.Reconnected, () => {
        if (this.closed || !this.recovering) return;
        this.reconnectingSeats.delete(seat);
        if (!this.reconnectingSeats.size) void this.finishReconnect();
      });
    }
    try {
      await this.app.connect(this.prepared.livekit_url, this.prepared.tokens.app.token, { autoSubscribe: false });
      check();
      await this.user.connect(this.prepared.livekit_url, this.prepared.tokens.user.token, { autoSubscribe: true });
      check();
      if (!this.bound(this.app.localParticipant, "app") || !this.bound(this.user.localParticipant, "user")) {
        throw new Error("The application seats did not match their binding.");
      }
      if (["voice", "choice"].includes(this.mode)) {
        for (const track of this.media.getAudioTracks()) {
          await this.user.localParticipant.publishTrack(track, { source: this.sdk.Track.Source.Microphone });
          check();
        }
      }
      return this;
    } catch (error) { this.closeAudio(); await this.disconnect(); throw error; }
  }
  async registerApp() {
    this.app.registerRpcMethod("foodease.action.v2", async (data) => {
      const request = JSON.parse(data.payload);
      const readOnly = ["get_current_context", "get_cart", "get_item_details"].includes(request.payload?.operation);
      this.assertCaller(data, readOnly);
      const result = await this.application.execute(request, { admit: () => this.assertCaller(data, readOnly) });
      return bounded(result);
    });
    this.app.registerRpcMethod("foodease.action_status.v2", async (data) => {
      this.assertCaller(data, true);
      const request = JSON.parse(data.payload);
      bounded(request);
      if (request.schema_version !== "2.0" || request.session_id !== this.prepared.session_id
          || typeof request.action_id !== "string" || !request.event_id) throw new Error("Invalid action lookup.");
      const result = await this.application.transport.lookup(request.action_id, request.event_id);
      if (result.schema_version !== "2.0" || result.session_id !== request.session_id
          || result.reply_to !== request.event_id || result.action_id !== request.action_id) throw new Error("Uncorrelated action lookup.");
      if (result.state === "found" && result.result?.payload.status !== "timeout_unknown"
          && this.application.pending.has(request.action_id)) {
        // Reuse this original lookup result; no action submission or result rewriting.
        const original = this.application.pending.get(request.action_id);
        correlated(original, result.result);
        await this.application.refresh({ result: result.result, request: original });
        this.application.pending.delete(request.action_id);
        this.application.savePending();
      }
      return bounded(result);
    });
    this.app.registerRpcMethod("foodease.present_summary.v2", async (data) => {
      this.assertCaller(data);
      const request = JSON.parse(data.payload);
      return bounded(await this.presentSummary(request));
    });
  }
  async presentSummary(request) {
    bounded(request);
    if (this.recovering || this.mode !== "typed" || request.schema_version !== "2.0"
        || request.session_id !== this.prepared.session_id || typeof request.text !== "string"
        || !request.text || request.text.length > 2000 || !request.summary_id || !request.turn_id) {
      throw new Error("Summary delivery unavailable.");
    }
    const summary = [...this.application.summaries.values()].find(({ result, request: original }) =>
      original.turn_id === request.turn_id && result.payload.verified_state.summary_revision === request.summary_revision
      && result.context_revision === this.application.snapshot.revision);
    if (!summary || this.application.snapshot.route !== "checkout") throw new Error("Summary is no longer current.");
    // Verify the summary hash using the same canonical JSON as ConfirmationMachine.
    const canonical = (value) => value && typeof value === "object" && !Array.isArray(value)
      ? Object.fromEntries(Object.keys(value).sort().map((key) => [key, canonical(value[key])]))
      : Array.isArray(value) ? value.map(canonical) : value;
    // Python serializes money as floats (100.0), JS JSON as integers (100). Hash
    // the original Python-compatible shape rather than silently accepting a mismatch.
    const pythonJson = JSON.stringify(canonical(summary.result.payload.verified_state))
      .replace(/("(?:unit_price|line_total|subtotal|amount|total)":)(\d+)(?=[,}])/g, "$1$2.0")
      .replace(/[\u007f-\uffff]/g, (char) => `\\u${char.charCodeAt(0).toString(16).padStart(4, "0")}`);
    const digest = [...new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(pythonJson)))]
      .map((v) => v.toString(16).padStart(2, "0")).join("").slice(0, 16);
    if (digest !== request.summary_hash) throw new Error("Summary does not match the reviewed cart.");
    if (!this.transcript.update({ kind: "assistant", turnId: request.turn_id, utteranceId: request.summary_id,
      text: request.text, phase: "completed", timestamp: timestamp() })) throw new Error("Summary was not rendered.");
    const summaryElement = this.transcript.rows.get(`assistant:${request.turn_id}:${request.summary_id}`)?.element;
    summaryElement?.scrollIntoView({ block: "nearest" });
    // Layout/paint boundary, then recheck cart and connection before acknowledging.
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    if (this.closed || this.recovering || this.document.visibilityState !== "visible"
        || !summaryElement?.getClientRects().length
        || this.application.snapshot.revision !== summary.result.context_revision) throw new Error("Summary delivery was interrupted.");
    const { text: _text, ...echo } = request;
    return { ...echo, delivered: true };
  }
  async publishContext(snapshot, turnId = null, destination = null) {
    if (this.closed || (!destination && snapshot.revision <= this.lastContextRevision)) return;
    const event = this.envelope("app.context_updated", snapshot,
      { context_revision: snapshot.revision, turn_id: turnId });
    await this.app.localParticipant.publishData(new TextEncoder().encode(bounded(event)),
      { reliable: true, topic: TOPICS.context, ...(destination && { destinationIdentities: [destination] }) });
    if (!destination) this.lastContextRevision = Math.max(this.lastContextRevision, snapshot.revision);
  }
  async publishStartupContext() {
    // The pre-dispatch snapshot is not buffered for a worker joining the room later.
    const agent = this.app.remoteParticipants.get(this.prepared.binding.agent_identity);
    if (this.bound(agent, "agent") && this.application.snapshot) {
      await this.publishContext(this.application.snapshot, null, agent.identity);
    }
  }
  async publishFreshContext() {
    const snapshot = await this.application.refresh();
    await this.publishContext(snapshot);
    return snapshot;
  }
  async playbackReady() {
    if (["voice", "choice"].includes(this.mode)) {
      await this.user.startAudio();
      if (this.user.canPlaybackAudio === false) throw new Error("Audio playback is blocked. Choose typing or enable playback and start again.");
    }
  }
  activate(mode, resuming = false) {
    return this.control(mode === "choice" ? "start" : resuming ? "resume" : "switch_mode", mode === "choice" ? "voice" : mode);
  }
  attachAudio(id, track) {
    if (this.closed || this.recovering || this.audio.has(id)
        || !["voice", "choice"].includes(this.mode) && !this.typedAudio) return;
    const element = track.attach();
    element.muted = this.paused;
    element.dataset.foodeaseAudio = id;
    this.document.body.append(element);
    this.audio.set(id, { track, element });
    element.play().catch(() => {
      if (this.closed || !this.audio.has(id)) return;
      this.onStatus("Audio playback was blocked. Assistance has stopped; restart when playback is allowed.");
      this.closeAudio();
      for (const listener of this.disconnectedListeners) listener();
    });
  }
  async setAudioPreference(enabled) {
    if (this.mode !== "typed" || this.closed) return;
    this.typedAudio = !!enabled;
    if (!enabled) { this.closeAudio(); return; }
    try {
      await this.user.startAudio();
      if (this.closed || !this.typedAudio) return;
      if (this.user.canPlaybackAudio === false) throw new Error("Audio playback is blocked.");
      for (const [id, track] of this.remoteAudio) this.attachAudio(id, track);
    } catch (error) { this.typedAudio = false; this.closeAudio(); throw error; }
  }
  stopMicrophone() {
    for (const track of this.media?.getTracks() || []) {
      track.stop();
      Promise.resolve(this.user.localParticipant?.unpublishTrack?.(track, true)).catch(() => {});
    }
  }
  async control(intent, mode = null, turnId = null) {
    if (this.closed) throw new Error("Assistance is not connected.");
    await this.user.localParticipant.publishData(new TextEncoder().encode(bounded(
      this.envelope("app.control", { intent, mode }, { turn_id: turnId }))), { reliable: true, topic: TOPICS.control });
  }
  async text(text) {
    if (this.recovering) throw new Error("Assistance is reconnecting. Wait before sending another request.");
    if (this.closed || !text.trim() || text.length > 2000) throw new Error("Enter a request of 1–2000 characters.");
    const turnId = newId();
    const event = this.envelope("app.text_input", { text }, { turn_id: turnId,
      context_revision: this.application.snapshot.revision });
    await this.user.localParticipant.publishData(new TextEncoder().encode(bounded(event)),
      { reliable: true, topic: TOPICS.text });
    this.transcript.update({ kind: "user", turnId, utteranceId: turnId, text, timestamp: event.timestamp });
  }
  receive(raw, participant, topic) {
    if (this.closed || !this.bound(participant, "agent")) return;
    try {
      if (raw.length > 14 * 1024) return;
      const event = JSON.parse(new TextDecoder().decode(raw));
      if (event.schema_version !== "2.0" || event.session_id !== this.prepared.session_id
          || !event.event_id || this.seenEvents.has(event.event_id)) return;
      if (this.seenEvents.size >= 4096) {
        this.onStatus("The assistance event limit was reached. Start a new assistance session.");
        for (const listener of this.disconnectedListeners) listener();
        void this.disconnect();
        return;
      }
      this.seenEvents.add(event.event_id);
      if (topic === "foodease.events.v2" && event.type === "transcript.assistant") {
        this.transcript.update({ kind: "assistant", turnId: event.turn_id,
          utteranceId: event.payload.utterance_id, text: event.payload.text,
          phase: event.payload.phase, timestamp: event.timestamp });
      } else if (topic === "foodease.events.v2" && event.type.startsWith("transcript.user.")) {
        this.transcript.update({ kind: "user", turnId: event.turn_id,
          utteranceId: event.payload.utterance_id, text: event.payload.text,
          phase: event.type.endsWith("final") ? "completed" : "updated", timestamp: event.timestamp });
      } else if (topic === "foodease.events.v2" && event.type === "agent.status") {
        if (event.timestamp >= this.lastStatusTimestamp) {
          this.lastStatusTimestamp = event.timestamp;
          this.onStatus(event.payload.state);
        }
      } else if (topic === "foodease.events.v2" && event.type === "agent.error") {
        this.onStatus(event.payload.message);
      } else if (topic === "foodease.events.v2" && event.type === "agent.control") {
        if (event.payload.intent === "resume" && event.turn_id) {
          if (event.payload.mode === this.mode && this.recoveryReceipt
              && event.turn_id === this.recoveryTurnId) this.recoveryReceipt();
          return; // A stale recovery receipt is never a new user resume command.
        }
        if (this.recovering && ["resume", "unmute"].includes(event.payload.intent)) return;
        this.onControl(event.payload);
      }
    } catch { /* Malformed or foreign output cannot change application state. */ }
  }
  detachAudio(id) {
    const audio = this.audio.get(id);
    if (!audio) return;
    audio.element.pause();
    audio.element.srcObject = null;
    audio.track.detach(audio.element);
    audio.element.remove();
    this.audio.delete(id);
  }
  closeAudio() { for (const id of [...this.audio.keys()]) this.detachAudio(id); }
  onDisconnected(listener) { this.disconnectedListeners.add(listener); }
  failConnection(message) {
    if (this.closed) return;
    this.onStatus(message);
    this.closeAudio();
    this.stopMicrophone();
    for (const listener of this.disconnectedListeners) listener();
    void this.disconnect();
  }
  beginReconnect(seat) {
    if (this.closed) return;
    if (this.mode === "choice") { this.failConnection("The connection was interrupted. Please choose how to order again."); return; }
    this.reconnectingSeats.add(seat);
    this.recoverySerial++;
    if (this.recovering) return;
    this.recovering = true;
    this.wasPaused = this.paused;
    this.application.summaries.clear();
    for (const track of this.media?.getTracks() || []) track.enabled = false;
    this.closeAudio();
    this.onStatus("reconnecting");
    // If the user seat is still connected, revoke the worker immediately too.
    void this.control("pause").catch(() => {});
    this.reconnectDeadline = setTimeout(() => this.failConnection("The connection could not recover. Restart assistance when ready."), 15000);
    this.reconnectDeadline.unref?.();
  }
  async finishReconnect() {
    const serial = this.recoverySerial;
    const current = () => !this.closed && this.recovering && serial === this.recoverySerial && !this.reconnectingSeats.size;
    if (!current() || this.recoveryRunning === serial) return;
    this.recoveryRunning = serial;
    try {
      await this.control("pause");
      if (!current()) return;
      for (const id of [...this.application.pending.keys()]) await this.application.reconcile(id);
      this.lastContextRevision = -1;
      await this.publishFreshContext();
      if (!current()) return;
      if (this.wasPaused) {
        this.recovering = false;
        clearTimeout(this.reconnectDeadline);
        this.onStatus("paused");
        return;
      }
      // Resume only after the worker's own fresh RPC and read-only recovery.
      this.recoveryTurnId = newId();
      this.recoveryReceipt = () => {
        if (!current()) return;
        this.recoveryReceipt = null;
        this.recovering = false;
        clearTimeout(this.reconnectDeadline);
        for (const track of this.media?.getTracks() || []) track.enabled = this.mode === "voice" && !this.paused && track.readyState !== "ended";
        for (const [id, track] of this.remoteAudio) this.attachAudio(id, track);
        this.onStatus("reconnected");
      };
      await this.control("resume", this.mode, this.recoveryTurnId);
    } catch { if (current()) this.failConnection("The current page could not be checked. Manual ordering remains available."); }
  }
  async disconnect() {
    if (this.closed) return;
    this.closed = true;
    this.recoverySerial++;
    this.recoveryReceipt = null;
    clearTimeout(this.reconnectDeadline);
    this.unsubscribe();
    this.closeAudio();
    this.remoteAudio.clear();
    this.stopMicrophone();
    await Promise.allSettled([this.app.disconnect(), this.user.disconnect()]);
  }
}
