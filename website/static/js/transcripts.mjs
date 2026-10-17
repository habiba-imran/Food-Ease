// Canonical envelope captions only. Native LiveKit audio is attached once elsewhere.
export class TranscriptView {
  constructor(container, { maxRows = 32 } = {}) {
    this.container = container;
    this.maxRows = maxRows;
    this.rows = new Map();
  }
  update({ kind, turnId, utteranceId, text, phase = "completed", timestamp = "" }) {
    if (!this.container || !["user", "assistant", "system"].includes(kind)
        || !["started", "updated", "completed", "interrupted"].includes(phase)
        || typeof text !== "string" || text.length > 2000 || !utteranceId || !turnId) return false;
    const key = `${kind}:${turnId}:${utteranceId}`;
    let row = this.rows.get(key);
    const terminal = (value) => ["completed", "interrupted"].includes(value);
    if (row && ((terminal(row.phase) && !terminal(phase)) || timestamp < row.timestamp)) return false;
    if (!row) {
      const element = this.container.ownerDocument.createElement("p");
      element.className = kind === "user" ? "user-message" : kind === "system" ? "harness-message" : "assistant-message";
      element.dataset.utteranceId = utteranceId;
      element.dataset.turnId = turnId;
      this.container.append(element);
      row = { element };
      this.rows.set(key, row);
      while (this.rows.size > this.maxRows) {
        const oldest = this.rows.keys().next().value;
        this.rows.get(oldest).element.remove();
        this.rows.delete(oldest);
      }
    }
    row.phase = phase;
    row.timestamp = timestamp;
    row.element.dataset.phase = phase;
    row.element.textContent = text + (phase === "interrupted" ? " (interrupted)" : "");
    return true; // textContent update never moves focus or replaces the input form
  }
}
