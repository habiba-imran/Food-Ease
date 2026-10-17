# FoodEase orchestration (sibling glue package)

Final orchestration Phase 9 provides the current
[delivery runbook](docs/FINAL_RUNBOOK.md), default real-website bring-up, explicit
live opt-in, owned process shutdown, safe correlation logs and acceptance evaluation.
See [evidence and outstanding live checks](evidence/final/phase-09/report.md).
The offline implementation gate and the joint live acceptance gate remain distinct.
Earlier entries below are historical checkpoints; use the final runbook for launch.

Final orchestration Phase 8 adds runtime provider degradation, fresh-state reconnect
barriers, original-ID outcome recovery and cleanup across background/reload/expiry.
See [recovery behavior and limits](docs/PHASE_08_RECOVERY.md) and
[verification](evidence/final/phase-08/report.md). Live vendor outages and audible
interruption measurements remain open, alongside Phase 7's model/listener gate.
Phase 9 is the one planned phase remaining and has not started. Earlier entries
below are historical checkpoints.

Final orchestration Phase 7 adds semantic page assistance, completed-output item
references, filter refinements, finite multi-step/duplicate guards and streaming
speech shaping. See the [conversation handoff](docs/PHASE_07_GROUNDED_CONVERSATION.md)
and [verification](evidence/final/phase-07/report.md). The real-model campaign and
human listening gate remain open. Phases 8 and 9 remain; no next-phase work is included.

Final orchestration Phase 6 adds the consent-gated spoken mode chooser, explicit
manual/voice/typed continuity and optional typed audio. See the
[mode handoff](docs/PHASE_06_OPENING_MODES.md) and
[verification](evidence/final/phase-06/report.md). Returning visits require explicit
activation. Physical-device, Cloud and provider audio activation remain unverified.
Phase 7 has not started. Earlier phase notes below are historical checkpoints.

Final orchestration Phase 5 connects the browser app/user seats, shared renderer,
typed/control transport and canonical worker output. See [browser handoff](docs/PHASE_05_BROWSER_INTEGRATION.md)
and [verification](evidence/final/phase-05/report.md). The opening mode chooser
remains Phase 6. Live provider/audio activation is unverified. Earlier phase notes
below describe their state at completion.

Final orchestration Phase 4 attaches the integrated live conversation/tool runtime.
See [runtime, controls and delivery requirements](docs/PHASE_04_LIVE_CONVERSATION_RUNTIME.md)
and [verification](evidence/final/phase-04/report.md). The browser bridge remains
Phase 5; the opening mode-choice conversation remains Phase 6. No live activation
is claimed. Historical phase notes below describe their state at completion.

Final orchestration Phase 3: [bound lifecycle, endpoints and launch](docs/PHASE_03_ASSISTANCE_LIFECYCLE.md)
and [verification](evidence/final/phase-03/report.md). `/v1/*` is disabled by default;
the integrated path uses `/v2/*` with the existing shopping cookie/session.
Use `tools/demo_up.py --integrated`. The worker now attaches Phase 4's runtime;
the actual page requires Phase 5's bridge before integrated browser use.

Final orchestration Phase 2 implements session-scoped shopping authority in the
website. See [authority and limits](docs/PHASE_02_APPLICATION_AUTHORITY.md) and
[verification](evidence/final/phase-02/report.md). The older assistance scaffold
below is not yet connected to that authority; Phase 3 has not started.

**Habiba-owned.** Session/token minting, consent/dispatch gate, demo bring-up.  
Not the voice brain (`voice-agent/`). Not the shopping UI (future `website/`).

See [`docs/OWNERSHIP.md`](docs/OWNERSHIP.md).

Final orchestration Phase 0: [baseline runbook](docs/PHASE_00_BASELINE_RUNBOOK.md)
and [evidence/status](evidence/final/phase-00/report.md). This records the current
offline baseline; final website/voice integration has not been implemented.

Final orchestration Phase 1: [contract 2.0 freeze](docs/PHASE_01_CONTRACT_FREEZE.md)
and [verification](evidence/final/phase-01/report.md). This is an opt-in contract;
the existing runtime continues to use frozen v1 until later integration phases.

## What’s in this package

| Piece | Path |
|---|---|
| Session / token API | `src/foodease_session/` → `foodease-session` |
| Env example | `.env.example` |
| Bring up demo stack | `tools/demo_up.py` |
| 3-seat topology helper | `tools/topology_up.py` |
| Joint checklist pointer | `docs/INTEGRATION_CHECKLIST.md` |

## Quick start

```bash
cd orchestration
uv sync
cp .env.example .env
# Fill LIVEKIT_URL / LIVEKIT_API_KEY / LIVEKIT_API_SECRET
# (or rely on ../voice-agent/.env as fallback)

uv run python tools/demo_up.py          # print full stack commands
uv run foodease-session                 # http://127.0.0.1:8090  ·  /docs
uv run python tools/demo_up.py --check  # healthz + mint probe
```

```bash
uv run pytest -q
uv run python tools/smoke_session.py
uv run python tools/smoke_assist.py     # needs LiveKit if dispatch=true
uv run python tools/topology_up.py
uv run python tools/secret_scan.py

# Integration scenarios (MockApp; joint when Zainab plugs in):
#   cd ../voice-agent && uv run python tools/run_integration.py
```

## API summary

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/healthz` | Liveness |
| `POST` | `/v1/session` | Token mint only (no agent dispatch) |
| `POST` | `/v1/token` | Mint one role |
| `POST` | `/v1/assist/start` | Consent + mic JWT + **CreateAgentDispatch** |
| `POST` | `/v1/assist/end` | Delete dispatch; **cart preserved** |

Docs: [`docs/API.md`](docs/API.md) · [`docs/ASSIST_LIFECYCLE.md`](docs/ASSIST_LIFECYCLE.md) · [`docs/BRINGUP.md`](docs/BRINGUP.md) · [`docs/TOPOLOGY.md`](docs/TOPOLOGY.md)

### Start assistance (Zainab / harness)

```javascript
const s = await fetch("http://127.0.0.1:8090/v1/assist/start", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ consent: true, include_app_token: true }),
}).then((r) => r.json());
await room.connect(s.livekit_url, s.user.token);
// later: POST /v1/assist/end { room, dispatch_id, session_id }
```

## Hardening checklist

- [x] Sibling package (glue out of agent + website)
- [x] `/healthz` without secrets
- [x] Consent matrix for tokens + assist start
- [x] App JWT `foodease.role=app`
- [x] Short TTL + CORS + rate limit
- [x] Assist start/end with cart_preserved
- [x] `demo_up.py` + `.env.example` + OWNERSHIP
- [x] Topology + integration checklist links

## Known limits

- Localhost demo auth (no end-user login)
- `FOODEASE_AGENT_NAME` must match LiveKit Agents worker (`foodease`)
- Set `LIVEKIT_AGENT_DISPATCH=false` to mint-only (no Cloud dispatch)
- Agent dispatch requires worker running; MockApp cart is independent
- Full 3-seat check needs Cloud + `FOODEASE_APP_TRANSPORT=livekit` + MockApp `--livekit`
