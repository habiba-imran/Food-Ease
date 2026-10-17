export const RoomEvent = Object.fromEntries(["DataReceived", "TrackSubscribed", "TrackUnsubscribed",
  "Disconnected", "Reconnecting", "Reconnected", "ParticipantDisconnected"].map((name) => [name, name]));
export const Track = { Source: { Microphone: "microphone" } };
export class LocalAudioTrack {}
const rooms = [];
window.fakeLiveKit = { rooms, contexts: [], sent: [], rpcCalls: [], audioAttachments: 0 };
export class Room {
  constructor() { this.handlers = new Map(); this.rpc = new Map(); this.remoteParticipants = new Map(); rooms.push(this); }
  on(name, callback) { this.handlers.set(name, callback); return this; }
  emit(name, ...args) { this.handlers.get(name)?.(...args); }
  registerRpcMethod(name, callback) { this.rpc.set(name, callback); }
  async connect(url, token) {
    [this.sid, this.generation, this.role] = token.split(":");
    const person = (role) => ({ identity: role, attributes: { "foodease.role": role,
      "foodease.session": this.sid, "foodease.generation": this.generation } });
    this.agent = person("agent");
    this.remoteParticipants.set("agent", this.agent);
    this.publishedTracks = new Set();
    this.unpublishedTracks = [];
    this.localParticipant = { ...person(this.role),
      publishTrack: async (track) => { this.publishedTracks.add(track); },
      unpublishTrack: async (track) => { this.publishedTracks.delete(track); this.unpublishedTracks.push(track); },
      publishData: async (raw, options) => {
        const event = JSON.parse(new TextDecoder().decode(raw));
        window.fakeLiveKit.sent.push({ role: this.role, event, ...options });
        if (options.topic === "foodease.context.v2") window.fakeLiveKit.contexts.push(event);
        await fetch(`/_test/data/${this.sid}`, { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ role: this.role, event, topic: options.topic }) });
      } };
    if (this.role === "app") { this.offset = 0; this.timer = setInterval(() => this.poll(), 20); }
  }
  async poll() {
    if (this.polling || this.closed) return;
    this.polling = true;
    try {
      const batch = await (await fetch(`/_test/poll/${this.sid}?offset=${this.offset}`)).json();
      this.offset = batch.offset;
      for (const message of batch.rpc) {
        window.fakeLiveKit.rpcCalls.push({ method: message.method, operation: JSON.parse(message.payload).payload?.operation });
        let result;
        try { result = { result: await this.rpc.get(message.method)(message) }; }
        catch { result = { error: true }; }
        await fetch(`/_test/result/${this.sid}/${message.id}`, { method: "POST",
          headers: { "Content-Type": "application/json" }, body: JSON.stringify(result) });
      }
      for (const output of batch.output) {
        const user = rooms.find((r) => r.role === "user" && r.sid === this.sid && !r.closed);
        user?.emit(RoomEvent.DataReceived, new TextEncoder().encode(JSON.stringify(output.event)), this.agent, null, output.topic);
      }
    } finally { this.polling = false; }
  }
  async startAudio() {}
  async disconnect() { this.closed = true; clearInterval(this.timer); }
}
