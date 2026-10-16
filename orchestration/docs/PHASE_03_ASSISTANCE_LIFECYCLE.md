# Final orchestration Phase 3: bound assistance lifecycle

Phase 3 implements preparation, readiness, cancellation and remote cleanup for a
website shopping session. Business actions remain the Phase 2 authority. The v2
conversation/action runtime is Phase 4; connecting the page to LiveKit is Phase 5.
There is no new audible activation or visual UI work in this phase.

## Binding and preparation

The session service checks the website's `/api/v2/app/context` using the caller's
existing HttpOnly `foodease_owner` cookie and `X-FoodEase-Session`. The authority
URL is fixed server configuration, `FOODEASE_WEBSITE_URL`; callers cannot supply
it. Cross-service requests do not follow redirects. No separate cart, shared
browser secret or client-asserted ownership is used.

For browser calls to the session API, use `credentials: "include"`, the shopping
session header, and an explicitly allowed website Origin. Both localhost services
must use the same hostname (`127.0.0.1` versus `localhost` changes cookie scope).
Production must use HTTPS and a deliberately configured same-site deployment;
arbitrary cross-site cookie forwarding is not supported.

`request_id` identifies one user start attempt and must be retained during its
retries, cancellation and reconciliation. Each accepted attempt gets one random
generation, a private room, three distinct server-selected app/user/agent
identities, and a private worker proof. The browser receives only app/user
credentials, public binding and generation. The worker proof travels solely in
server-created dispatch metadata and its worker acknowledgement header.

User JWTs permit microphone publishing; app JWTs permit data but no media
publishing. Both include session/generation/role attributes and prohibit updating
their own metadata. Worker identity/attributes are assigned through the SDK's
job-accept callback. Identity fields and room/dispatch IDs are never client inputs
to the integrated lifecycle API.

Preparation mints credentials but does not dispatch. The website retains its cart
independently of assistance. Repeated start with the same request ID returns the
same generation; a different start is refused while the previous one is alive or
has pending cleanup. Replaying an ended/cancelled attempt cannot start it again.

## Endpoint sequence

All owner routes require the shopping cookie and `X-FoodEase-Session`.

| Route | Body / behavior |
|---|---|
| `POST /v2/assist/start` or `/v2/session` | `{request_id, consent: true}`; preparation only |
| `POST /v2/assist/ready` | `{request_id, generation, context_revision, media_ready, playback_ready, app_ready}`; all readiness booleans must be true |
| `POST /v2/assist/worker-ready` | `{session_id, generation, context_revision, runtime_ready}` plus private `X-FoodEase-Worker-Proof`; no browser ownership assertion substitutes for this proof |
| `GET /v2/assist/status/{request_id}` | Observe lifecycle and separate dispatch/room cleanup outcomes |
| `POST /v2/token` | `{request_id, generation, consent: true}`; refresh only an unexpired, owner-bound generation; identities/room stay the same |
| `POST /v2/assist/end` | `{request_id, generation?}`; no supplied room/dispatch IDs; optional generation supports cancellation overtaking preparation |

Bodies use strict types and reject extra fields. Responses are `no-store`. The
client must check HTTP errors rather than interpreting them as successful state.
Missing/foreign ownership, stale generation and stale context are refused.

The intended browser sequence is permission → prepare → join both seats →
register app handler → publish fresh context → establish playback readiness →
ready → wait for authorized worker acknowledgement. Server readiness independently
checks the actual bound app/user room participants and current authority revision.
Only one dispatch task is admitted. The worker must receive context from the
bound app identity with the matching role/session/generation, and the server must
verify the bound agent participant before allowing the active state.

`IntegratedRoomGate` checks packet sender identity/attributes and canonical v2
envelopes. It rejects foreign sessions, wrong topics/types, wrong roles, anonymous
packets and stale context. Only the bound user may supply controls/text. Manual
selection/end or a bound seat disconnect closes startup. The arbitrary non-agent
destination fallback was removed from the real RTC bridge.

## Cancellation and cleanup

States are `preparing`, `dispatching`, `waiting_worker`, `active`,
`cleanup_pending`, `ended`. Greeting permission is true only for an active,
uncancelled generation. Cancellation marks the generation before awaiting I/O.
A cancellation that arrives before prepare stores a tombstone. A late prepare
cannot resurrect it. An old generation's end cannot stop a newer generation.

The service owns the dispatch task even if an HTTP caller is cancelled. It never
blindly repeats an uncertain create. Cleanup lists dispatches in the recorded
private room, matches trusted generation metadata, deletes the identified
dispatch and deletes the room to disconnect its seats. Positive discovery can
reconcile a lost creation response. An empty list cannot prove that an unknown
create will never finish, so unresolved creation stays `cleanup_pending` and
blocks replacement. Transient deletion failures also retain the record; later
end calls or the periodic sweep retry reconciliation. A specific SDK `not_found`
response is treated as absence; arbitrary errors are not.

The browser lifecycle controller is an exported, dependency-injected module at
`website/static/js/assistance-controller.mjs`. It stops local tracks and closes
audio before waiting for server end. Local stopped state and remote cleanup
pending state are separately observable. Late permission/join results are disposed
and cannot set a newer generation's UI state. SDK seat disconnect should be
connected through its `onDisconnected` port. This module is tested with fake
media/SDK handles; the existing page does not import it until Phase 5 wiring.

## Limits, refresh and launch

Defaults: 30-second startup handshake, 30-minute idle lifetime, two-hour absolute
generation lifetime, five-second remote operation timeout, 512 retained generation
records, and a one-second sweep interval between sweeps. Remote calls and cleanup
can extend the wall-clock time of a sweep. Status observation does not renew
assistance lifetime. Refresh requires fresh consent and authority verification,
renews idle activity, and cannot extend the absolute lifetime. Tokens are capped
to the remaining absolute lifetime; fewer than 60 seconds remaining requires a
new session instead of an invalid short-lived mint.

Disconnect ends the generation. After cleanup, an explicit new start establishes
new identities/room; there is no silent reconnect to a mock or replay of business
actions. The later browser bridge may use proactive refresh while still connected;
it must not use refresh to revive an ended generation. The service's periodic
sweep checks active ownership and required seats and tears down missing/expired
generations. Shutdown attempts recorded cleanup too.

This is single-process, in-memory coordination, like Phase 2. Process death loses
the registry and cannot guarantee cleanup of Cloud resources; do not claim durable
reconciliation or singleton coordination across restarts/multiple instances.
Before a real deployment/restart, old Cloud resources need independent inspection
and cleanup. Production durability is not established by the fake tests.

The old `/v1/*` endpoints return 410 by default. The isolated old harness can opt
in with `FOODEASE_LEGACY_DEV_API=true`; even then it cannot mint or control the
reserved `foodease-v2-*` rooms. Its historical unbound lifecycle is not an
alternative integrated entry point.

From `orchestration/`, print the exact PowerShell launch commands:

```powershell
.venv\Scripts\python.exe tools\demo_up.py --integrated
```

Integrated workers require `FOODEASE_APP_TRANSPORT=website` and the matching
`FOODEASE_SESSION_API`. Unknown transport values fail. Integrated dispatch metadata
is strict 2.0 and cannot be consumed in mock/livekit-v1 mode. The worker attaches
its gated runtime through `run_integrated_job(..., runtime_factory=...)`.

**Phase boundary:** no v1 adapter is substituted. Until Phase 4 supplies the v2
runtime factory, the worker reports `runtime_ready: false` and shuts down; the
server records `integrated_runtime_unavailable` and cleans up. The browser LiveKit
dependency, page wiring, all 13 voice tools and conversational behavior are not
implemented here. Fake runtimes test the positive lifecycle path; they are not
evidence that a real voice order works.

## Verification

```powershell
cd orchestration
.venv\Scripts\python.exe tools\phase3_verify.py
```

This runs lifecycle/ownership/fault tests, actual worker callback tests with fake
runtimes, JavaScript media cancellation tests, Phase 2 regression, contract freeze,
lint/types and the full legacy agent suite. The HTTP rehearsal starts two real
localhost servers with fake LiveKit rooms/dispatch and the real website authority;
it preserves a nonempty cart while failed cleanup reconciles. It never reads
`.env`, starts a real worker, opens a microphone or calls Cloud/providers.

See [verification report](../evidence/final/phase-03/report.md). Original frozen v1
artifacts and old acceptance evidence are preserved byte-for-byte. Existing agent
baseline failures are reported separately. Phase 4 has not started.

SDK evidence: installed `livekit-api 1.2.1`, `livekit-agents 1.8.4`, `livekit 1.1.20`.
The installed dispatch deletion API takes `(dispatch_id, room_name)`; the previous
wrapper passed a request object. This was verified against installed source and
the [official Python dispatch API](https://docs.livekit.io/reference/python/livekit/api/agent_dispatch_service.html).
Room cleanup uses the [official RoomService API](https://docs.livekit.io/reference/python/livekit/api/room_service.html).
