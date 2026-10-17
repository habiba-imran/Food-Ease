// One authority lane and one renderer for manual input and bound worker RPCs.
export const OPERATIONS = new Set(["navigate", "search_menu", "filter_menu", "select_item",
  "get_item_details", "get_cart", "cart.add_item", "cart.set_quantity", "cart.remove_item",
  "checkout.get_summary", "checkout.submit_demo_order", "undo_last_reversible_action", "get_current_context"]);
export const newId = () => crypto.randomUUID();
export const timestamp = () => new Date().toISOString();
export const bounded = (value) => {
  const raw = JSON.stringify(value);
  if (new TextEncoder().encode(raw).length > 14 * 1024) throw new Error("Application payload is too large.");
  return raw;
};
export function actionRequest(sessionId, turnId, revision, operation, args = {}, actionId = newId()) {
  return { schema_version: "2.0", session_id: sessionId, turn_id: turnId, event_id: newId(),
    timestamp: timestamp(), context_revision: revision, type: "agent.action_request",
    payload: { action_id: actionId, operation, arguments: args } };
}
export function correlated(request, result) {
  if (result?.type !== "app.action_result" || result.schema_version !== "2.0"
      || result.session_id !== request.session_id || result.turn_id !== request.turn_id
      || result.reply_to !== request.event_id || result.payload?.action_id !== request.payload.action_id
      || result.payload.operation !== request.payload.operation
      || !Number.isSafeInteger(result.context_revision) || result.context_revision < request.context_revision) {
    throw new Error("The application reply could not be verified.");
  }
  bounded(result);
  return result;
}
export class Application {
  constructor({ sessionId, transport, render, onError = () => {}, storage = null }) {
    Object.assign(this, { sessionId, transport, render, onError });
    this.snapshot = null;
    this.listeners = new Set();
    this.tail = Promise.resolve();
    this.pending = new Map();
    this.outcomes = new Map();
    this.storage = storage;
    this.pendingKey = `foodease.pending-actions.v2:${sessionId}`;
    this.manualRequests = new Map();
    try {
      const saved = JSON.parse(storage?.getItem(this.pendingKey) || "[]");
      for (const request of saved.slice(0, 32)) {
        if (request.session_id === sessionId && OPERATIONS.has(request.payload?.operation)) this.pending.set(request.payload.action_id, request);
      }
    } catch { /* Storage is optional; in-memory ownership still applies. */ }
    this.summaries = new Map();
  }
  subscribe(listener) { this.listeners.add(listener); return () => this.listeners.delete(listener); }
  async accept(snapshot, { result = null, request = null, force = false } = {}) {
    if (snapshot.schema_version !== "2.0" || snapshot.session_id !== this.sessionId
        || !Number.isSafeInteger(snapshot.revision) || snapshot.revision < 0) throw new Error("Invalid page context.");
    bounded(snapshot);
    if (this.snapshot && snapshot.revision < this.snapshot.revision) return false;
    const changed = !this.snapshot || snapshot.revision > this.snapshot.revision;
    const currentResult = result?.context_revision === snapshot.revision ? result : null;
    if (!changed && !currentResult && !force) return false;
    if (this.snapshot && JSON.stringify(this.snapshot.cart) !== JSON.stringify(snapshot.cart)) this.summaries.clear();
    if (currentResult?.payload.status === "success" && currentResult.payload.operation === "checkout.get_summary" && request) {
      this.summaries.set(currentResult.payload.action_id, { result: currentResult, request });
      while (this.summaries.size > 16) this.summaries.delete(this.summaries.keys().next().value);
    }
    this.snapshot = snapshot;
    await this.render(snapshot, currentResult?.payload || null, request);
    if (changed || force) {
      for (const listener of this.listeners) await listener(snapshot, request?.turn_id || null);
    }
    return true;
  }
  async refresh(options = {}) {
    const snapshot = await this.transport.context();
    await this.accept(snapshot, options);
    return this.snapshot;
  }
  _queue(work) {
    const task = this.tail.then(work);
    this.tail = task.catch(() => {});
    return task;
  }
  savePending() {
    try {
      if (this.pending.size) this.storage?.setItem(this.pendingKey, JSON.stringify([...this.pending.values()].map((request) => ({
        ...request, payload: { ...request.payload, arguments: {} }, // never persist checkout tokens
      }))));
      else this.storage?.removeItem(this.pendingKey);
    } catch { /* Memory-only ownership. */ }
  }
  manual(operation, args = {}, actionId = null, revision = null) {
    return this._queue(async () => {
      if (this.pending.size) throw new Error("A previous action is unresolved. Check its outcome before continuing.");
      if (!this.snapshot) await this.refresh();
      let request = actionId && this.manualRequests.get(actionId);
      if (request && (request.payload.operation !== operation || JSON.stringify(request.payload.arguments) !== JSON.stringify(args))) {
        throw new Error("An action ID cannot be reused for a different request.");
      }
      if (!request) request = actionRequest(this.sessionId, `manual-${newId()}`, revision ?? this.snapshot.revision,
                                           operation, args, actionId || newId());
      if (actionId) this.manualRequests.set(actionId, request);
      return this._execute(request);
    });
  }
  execute(request, { admit = () => {} } = {}) {
    return this._queue(() => {
      // Recheck the bound assistance owner when a queued request actually runs.
      // Submitted work below keeps its identity/outcome after local shutdown.
      admit();
      return this._execute(request);
    });
  }
  async _execute(request) {
    if (request.schema_version !== "2.0" || request.type !== "agent.action_request"
        || request.session_id !== this.sessionId || !OPERATIONS.has(request.payload?.operation)
        || !Number.isSafeInteger(request.context_revision) || !request.turn_id || !request.event_id
        || !request.payload.action_id) throw new Error("Invalid application request.");
    bounded(request);
    const actionId = request.payload.action_id;
    if (this.pending.size && !this.pending.has(actionId)
        && !["get_current_context", "get_cart", "get_item_details"].includes(request.payload.operation)) {
      throw new Error("A previous action is unresolved. Check its outcome before continuing.");
    }
    this.pending.set(actionId, request);
    this.savePending();
    let result;
    try {
      result = correlated(request, await this.transport.action(request));
    } catch (error) {
      // Read-only recovery of the *same* ID, including after response loss. Never retry a write.
      try {
        const lookup = await this.transport.lookup(actionId);
        if (lookup.state === "found") result = correlated(request, lookup.result);
        else this.unknownOutcome(actionId, lookup.state);
      } catch { /* uncertainty remains owned below */ }
      if (!result) {
        if (!this.outcomes.has(actionId)) this.unknownOutcome(actionId, "unknown");
        return { schema_version: "2.0", session_id: this.sessionId, type: "app.action_result",
          event_id: newId(), turn_id: request.turn_id, reply_to: request.event_id, timestamp: timestamp(),
          context_revision: this.snapshot?.revision ?? request.context_revision,
          payload: { action_id: actionId, operation: request.payload.operation,
            status: "timeout_unknown", verified_state: null, error_code: "timeout",
            error_message: "The application outcome could not be verified." } };
      }
    }
    if (result.payload.status !== "timeout_unknown") this.pending.delete(actionId);
    this.savePending();
    // State/render/publication must complete before the worker receives its result.
    // A failed render/refresh is not a new business failure: let RPC reconciliation
    // recover the retained original result, never submit again.
    try {
      let snapshot = await this.transport.context();
      if (snapshot.revision < result.context_revision) snapshot = await this.transport.context();
      if (snapshot.revision < result.context_revision) throw new Error("The current page is not synchronized.");
      await this.accept(snapshot, { result, request });
    } catch {
      // Business outcome is retained by the authority, but view delivery is not
      // complete. Block new mutations until read-only reconciliation renders it.
      this.pending.set(actionId, request);
      this.savePending();
      throw new Error("The action outcome is retained, but the page could not synchronize. Use Check pending changes.");
    }
    if (result.payload.status !== "success") this.onError(
      result.payload.status === "timeout_unknown" ? "The outcome is still unknown. Check your cart."
        : `The action was not completed (${result.payload.error_code || "unavailable"}). Your cart is still available.`);
    return result;
  }
  async reconcile(actionId) {
    const request = this.pending.get(actionId);
    if (!request) return null;
    const lookup = await this.transport.lookup(actionId);
    if (lookup.state !== "found") { this.unknownOutcome(actionId, lookup.state); return null; }
    const result = correlated(request, lookup.result);
    if (result.payload.status === "timeout_unknown") { this.unknownOutcome(actionId, "unknown"); return null; }
    await this.refresh({ result, request });
    this.pending.delete(actionId);
    this.outcomes.delete(actionId);
    this.savePending();
    return result;
  }
  unknownOutcome(actionId, state) {
    this.outcomes.set(actionId, state);
    this.onError({
      not_seen: "The request is not registered yet. It could still arrive; it has not been sent again.",
      pending: "The application is still processing that request. It has not been sent again.",
      expired: "The earlier outcome is no longer retained. We cannot verify whether it completed. It has not been sent again.",
    }[state] || "The outcome is unknown. Check pending changes before continuing.");
  }
}
