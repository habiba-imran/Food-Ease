# Integration note (Habiba → Zainab)

Self-serve summary so the website can replace MockApp **without rewriting** STT/TTS/LLM or conversation logic.

Habiba glue status: `PACK_STATUS.md`. Ownership: `OWNERSHIP.md`.

## Entry / exit points

| Role | How it starts / stops |
|---|---|
| **Session / assist API** | `orchestration/` → `uv run foodease-session` (`:8090`) — JWTs + Start/End assistance |
| **Agent worker** | `uv run foodease-worker` → LiveKit Agents job; joins when dispatched; proactive greeting after ready |
| **App (your website)** | Join same room with `foodease.role=app` via `POST /v1/token` role=app |
| **User (mic)** | `POST /v1/assist/start` after consent → user JWT + agent dispatch |
| **Text CLI (Habiba only)** | `uv run foodease-cli` → in-process MockAdapter (no LiveKit) |
| **Harness (demo user)** | `harness/token_server.py` — debug inspector, not product UI |

**Exit:** End assistance / goodbye / disconnect → agent leaves; **cart stays in the app**.

## What the frontend must register

| Method / topic | Direction | Payload |
|---|---|---|
| RPC `foodease.action` | Agent → App | `ActionRequestPayload` JSON; **response** = `ActionResultPayload` JSON |
| RPC `foodease.text_input` | App path (optional) | `{ "text": "..." }` typed input |
| Data topic `foodease.context` | App → Agent | `ContextSnapshot` (see contract) |
| Data topic `foodease.control` | App → Agent | Mute/pause/end style `AppControlPayload` |

Schemas: `../contract/v1/schemas/`. Transport: `../contract/v1/schemas/transport_defaults.json`.

Destination resolution (agent side): participant with `foodease.role=app`, else first non-agent (`LiveKitRpcAdapter`).

## Room topology (three seats)

| Seat | Demo today | You |
|---|---|---|
| user | Harness | Your mic client after Start assistance |
| app | MockApp `--livekit` | **Your website** |
| agent | `foodease-worker` | Unchanged |

See `SESSION_API.md` and `../orchestration/docs/TOPOLOGY.md`.

## State sync (revision rules)

1. Every GUI or cart change that matters to voice **bumps `revision`** and pushes context on `foodease.context`.
2. Agent ignores **stale** inbound revisions (lower than last applied).
3. After GUI navigation without voice, push context so “Where am I?” matches the screen.
4. Checkout: optional `confirmation_token` on `checkout.get_summary` success must be echoed on `checkout.submit_demo_order` when present.
5. Never auto-retry mutations after `timeout_unknown` / failure. Reconcile via snapshot first.
6. Cart edit while awaiting checkout confirm **invalidates** confirm (IR-05).

## Mute ownership (default)

- **Browser mic mute** owned by the **user** client (`setMicrophoneEnabled`).
- App may also send `app.control` mute/pause → `muted/paused` product state.
- Mic mute ≠ cancel in-flight cart mutations (R5 / L9).

## Languages

- **Demo: English.** Urdu / multilingual not promised for v1 (L16).

## Hard constraints

- Allowlist of **13 operations** only (`contract/v1`).
- Speak verified outcomes only (`action_id` match).
- No LiveKit API keys in the frontend — Habiba’s `orchestration/` mints JWTs (L18).
- Payload size default max **15360** bytes (L7).

## Known limitations (honest)

| Area | Status |
|---|---|
| Phase 5 live free-conversation | Waived ADR-0009 |
| Phase 6 listening panel / dogfood | Waived ADR-0010 |
| Phase 9 Mode 1/2 latency campaign | Waived ADR-0011 — tooling only |
| Phase 10 live audio / usability | Waived ADR-0012 — automated T-record kept |
| Noise cancellation | Toggle present; Cloud NC not wired on free tier |
| Preemptive generation | Default **off** (ADR-0008) |
| Speed/volume | Preferences acknowledged; frontend volume forwarding is [LATER] |

## Conformance + joint IR

```bash
# Habiba adapter suite (when your adapter is ready — task 11.8 / L15)
cd voice-agent && uv run pytest tests/adapter_conformance tests/test_phase7.py -q

# Joint scenarios (MockApp auto today; Live column = you)
cd voice-agent && uv run python tools/run_integration.py
```

See `JOINT_ACCEPTANCE.md`.
