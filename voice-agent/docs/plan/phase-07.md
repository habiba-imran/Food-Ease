## Phase 7 — Interfaces, metrics, real transport, inspector harness (Size M–L)

**Goal:** everything the spec says must be inspectable independently of the final UI (deliverable 7), the instrumentation Phase 9 needs, and a **full rehearsal of the real integration path**.

**Tasks**

- **7.1 [AGENT] EventBus.** Emits envelope events: `agent.status`, `transcript.user.partial|final`, `transcript.assistant` (started/updated/completed/interrupted), `agent.action_request`, `agent.clarification_required`, `agent.control`, `agent.error`. Final user transcript replaces, not duplicates, the interim. Every outgoing event is validated against the schema before sending.
- **7.2 [AGENT] Product states (VA-07).** Map LiveKit states to `off/awaiting_consent · connecting · ready/listening · user_speaking · thinking · assistant_speaking · waiting_for_action_result · idle · muted/paused · reconnecting · error · ended`; keep a state-transition log.
- **7.3 [AGENT] Inbound handling.** `app.context_snapshot`, `app.context_updated`, `app.action_result`, `app.control`, `app.text_input` via the adapter. Stale revisions are ignored for decisions but logged.
- **7.4 [AGENT] `LiveKitRpcAdapter` (real implementation, P0).** Implements `AppAdapter` over RPC per contract v1.0 (destination resolution configurable; default: the participant with attribute `foodease.role=app`, else the first non-agent participant). Handles RPC timeouts → `timeout_unknown`, payload-size limits, reconnects. Passes the Phase 3 conformance suite against the MockApp.
- **7.5 [AGENT] MockApp participant (P1, strongly recommended).** `mock_app/`: a separate Python process that joins the room as the "website", registers the RPC methods, owns the mock cart/pages (reusing the Phase 3 mock logic), and pushes context updates. Scenario toggles are exposed on a localhost-only control endpoint, enabled only when `DEV_MODE=true`. This rehearses the exact swap Zainab will do: her site registers the same methods instead.
- **7.6 [AGENT] Metrics logger.** Per-turn JSONL: end-of-turn delay, LLM first token, TTS first byte (LiveKit per-turn metrics where available), and **audible TTFA measured on the client side** (7.7/7.8). Each record stores the config hash (models, thresholds, region).
- **7.7 [AGENT] Inspector harness** (extend the Phase 5 client): join/leave, mic mute, typed input, live agent state, interim/final transcripts, assistant text with interrupted marking, raw event log, controls for the MockApp, GUI-navigation simulator. Plain and keyboard-operable; no design effort.
- **7.8 [AGENT] Injection test client** (`tools/inject.py`): a headless LiveKit client that publishes a pre-recorded WAV as its mic track at a known time, records the agent's audio track with timestamps, and can inject an interruption at a chosen moment. This is the reproducible latency measurement source.
- **7.9 [AGENT] Fault-injection toggles** (dev only): fail STT, fail LLM, fail TTS, drop connection.

**Strict guidelines**

- No keys, long-TTL tokens, system prompt or provider stack traces in events or the page.
- `agent.error` messages are user-safe.
- Dev control endpoints are off by default and bind to localhost only.
- No audio is recorded or persisted unless `RECORD_AUDIO=true` and consent exists (R13).

**Verification**

| ID | Check | Pass condition |
|---|---|---|
| V7.1 | Every event emitted in a full scripted session validates against the schema | 100% |
| V7.2 | State-transition log for a session covers every reachable VA-07 state | Documented |
| V7.3 | T15: deny mic or mute | Explicit state; typed/manual fallback works |
| V7.4 | T16: typed request | Same interpretation/action route; no fake audio |
| V7.5 | Interim → final replacement verified in the harness | No duplicate lines |
| V7.6 | Secret scan of harness output/page source; retention check (no audio files created in default config) | Clean |
| V7.7 | Conformance suite passes with `LiveKitRpcAdapter` ↔ MockApp | 100% |
| V7.8 | Full dialogue scenario (DS-06, DS-17) runs over the real transport via MockApp | Same results as in-process |
| V7.9 | Injection client produces a metrics JSONL with all fields | Present |

**Gate:** V7.1–V7.9 (V7.7/V7.8 may be deferred only if 7.5 is deferred, and the deferral is documented).

---

