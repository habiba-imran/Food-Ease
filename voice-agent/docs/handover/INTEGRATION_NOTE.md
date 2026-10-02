# Integration note (Habiba → Zainab)

Self-serve summary so the website can replace MockApp **without rewriting** STT/TTS/LLM or conversation logic.

## Entry / exit points

| Role | How it starts / stops |
|---|---|
| **Agent worker** | `uv run foodease-worker` → LiveKit Agents job; joins room when dispatched; proactive greeting after ready |
| **Text CLI** | `uv run foodease-cli` → in-process `MockAdapter` (no LiveKit) |
| **App (website)** | Join same LiveKit room as participant with attribute `foodease.role=app` (or be the sole non-agent participant) |
| **Harness** | `harness/token_server.py` + browser client for demos |

**Exit:** user goodbye / harness Leave / room disconnect → agent ends session; cart state lives in the **app**, not the agent process.

## What the frontend must register

| Method / topic | Direction | Payload |
|---|---|---|
| RPC `foodease.action` | Agent → App | `ActionRequestPayload` JSON; **response** = `ActionResultPayload` JSON |
| RPC `foodease.text_input` | Agent → App (optional) | `{ "text": "..." }` typed input from agent/harness path |
| Data topic `foodease.context` | App → Agent | `ContextSnapshot` (or envelope wrapping it — see contract) |
| Data topic `foodease.control` | App → Agent | Mute/pause/end style `AppControlPayload` |

Schemas: `contract/v1/schemas/`. Transport defaults: `contract/v1/schemas/transport_defaults.json`.

Destination resolution (agent side): participant with `foodease.role=app`, else first non-agent participant (`LiveKitRpcAdapter`).

## State sync (revision rules)

1. Every GUI or cart change that matters to voice **bumps `revision`** and pushes a fresh context on `foodease.context`.
2. Agent ignores **stale** inbound revisions (lower than last applied) — see `inbound.InboundHandler`.
3. After GUI navigation without voice, push context so “Where am I?” matches the screen (T09).
4. Checkout: agent may receive optional `confirmation_token` on `checkout.get_summary` success and must echo it on `checkout.submit_demo_order` when present.
5. Never auto-retry mutations after `timeout_unknown` / failure (R4). Reconcile via snapshot first.

## Mute ownership (default)

- **Browser mic mute** is owned by the **client** (harness: `setMicrophoneEnabled`).
- App may also send `app.control` mute/pause; agent maps to `muted/paused` product state.
- Default until joint change: **client mic mute does not cancel in-flight cart mutations** (R5). Documented in `OPEN_DECISIONS.md`.

## Languages

- **Demo language: English** (Flux / Sonic / Gemini as configured).
- Urdu / multilingual: **not promised** for v1 handover.

## Hard constraints

- Allowlist of 13 operations only (`docs/SPEC.md` / contract).
- Speak verified outcomes only (`action_id` match).
- No keys in repo; `.env` local only.
- Payload size default max **15360** bytes (raise only after measuring LiveKit limits).

## Known limitations (honest)

| Area | Status |
|---|---|
| Phase 5 live free-conversation (5.10) | Waived ADR-0009 — untested with real mic echo/overlap |
| Phase 6 listening panel / dogfood | Waived ADR-0010 |
| Phase 9 Mode 1/2 latency campaign | Waived ADR-0011 — tooling only; no fabricated §7 numbers |
| Phase 10 live audio / usability | Waived ADR-0012 — automated T-record kept |
| Noise cancellation | Toggle present; Cloud NC module not wired on free tier |
| Preemptive generation | Default **off** (ADR-0008) |
| Speed/volume | Preferences acknowledged; frontend volume forwarding is [LATER] |

## Conformance

```bash
uv run pytest tests/adapter_conformance tests/test_phase7.py -q
```

When Zainab’s adapter is ready: run the same suite against it; adapt only `LiveKitRpcAdapter` / contract minor version (task 11.8 [LATER]).
