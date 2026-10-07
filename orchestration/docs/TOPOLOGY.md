# Room topology (orchestration rehearsal)

Three seats in **one** LiveKit room. Zainab later replaces only the **app** seat.

| Seat | Identity (demo) | How they join |
|---|---|---|
| **user** | `harness-user` | Harness → `POST /v1/assist/start` → mic JWT |
| **app** | `mock-app` | MockApp `--livekit` → `POST /v1/token` role=app (`foodease.role=app`) |
| **agent** | LiveKit Agents job | Assist dispatch → `foodease-worker` with `FOODEASE_APP_TRANSPORT=livekit` |

## Wire contract (unchanged)

| Channel | Name |
|---|---|
| RPC | `foodease.action`, `foodease.text_input` |
| Data | `foodease.context`, `foodease.control` |

## Join order

1. `foodease-worker` (listening; `FOODEASE_APP_TRANSPORT=livekit`)
2. `foodease-session` on `:8090`
3. MockApp live: `uv run python -m mock_app --livekit --room foodease-demo`
4. Harness → **Start assistance**

## Pass criteria

1. Room has **user**, **app** (`foodease.role=app`), and **agent** participants.
2. One `foodease.action` round-trip succeeds (`get_current_context` or cart op).
3. App publishes context on `foodease.context` (snapshot non-empty on agent).

Helper: `uv run python tools/topology_up.py` (from `orchestration/`).

## Zainab swap

Your website joins with the **app** JWT, registers the same RPCs/topics, and drops MockApp. Worker and session API stay.

## Integration scenarios

Contract behaviors (stale revision, duplicate `action_id`, checkout confirm, mic → manual):  
`orchestration/docs/INTEGRATION_CHECKLIST.md` · run `cd voice-agent && uv run python tools/run_integration.py`
