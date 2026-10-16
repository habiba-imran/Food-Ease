# Final orchestration Phase 3 verification

Date: 17 October 2026. Branch: `phase-3-assistance-lifecycle`.

Phase 3 adds shopping-bound assistance generations, staged readiness, owned
dispatch/cancellation, verified room roles and retained cleanup reconciliation.
The implementation does not use a second shopping cart. The old unbound API is
disabled by default and cannot access integrated rooms even when explicitly
enabled for legacy development.

**IMPLEMENTATION GATE: PASS for the scoped checks below.** This is a lifecycle
implementation gate using fake room/dispatch/runtime/media handles and the real
shopping authority. It is not a complete live voice-ordering gate.

**ACTIVATION GATE: not passed or claimed.** Phase 4 must attach the v2 conversation
runtime; Phase 5 must connect the browser page/SDK. The actual integrated worker
currently reports unavailable and shuts down when the Phase 4 runtime is absent.
No v1 adapter or mock cart substitutes for that missing runtime.

## Commands and results

Initial test-first service check failed with the expected missing lifecycle module.
The repeatable final command from `orchestration/` is:

```powershell
.venv\Scripts\python.exe tools\phase3_verify.py
```

The [run summary](run-1/summary.json) records commands, package directories and
exit codes. Each check has an adjacent raw `.log` file.

Final review strengthened the typed-input wrong-sender/foreign-session assertions
in the existing worker gate test. The same eight startup tests passed again; see
`run-1/worker-input-postreview.log`. No implementation changed after the full run.

| Check | Result |
|---|---|
| Orchestration suite | 36 passed; one existing Starlette/httpx deprecation warning |
| Website Phase 2 regression suite | 38 passed; one existing Starlette/httpx warning |
| Actual worker startup callbacks and existing RTC bridge tests | 11 passed |
| JavaScript media/lifecycle plus existing session transport tests | 18 passed |
| Orchestration and website lint | Pass |
| Changed worker bridge/startup/shared-contract lint | Pass |
| Orchestration types | 0 errors, 0 warnings |
| Worker startup/types for changed paths | 0 errors, 0 warnings |
| Website/shared-contract types | 0 errors, 0 warnings |
| Frozen v2 contract/schema/handoff check | Pass |
| Phase 3 verifier/rehearsal/launch tool lint | Pass |
| JavaScript controller syntax | Pass |
| Two localhost HTTP services with real website authority, fake LiveKit | Pass |
| Frozen v1 preservation against Phase 1 hashes | 92 files unchanged |

The HTTP [rehearsal trace](run-1/http-smoke.json) deliberately labels LiveKit and
worker readiness as fake. It establishes real HTTP cookie/session attachment,
one prepared generation, no dispatch before readiness, one dispatch after it,
waiting/active lifecycle transitions, failed deletion retained as cleanup_pending,
replacement refused while cleanup is pending, and successful reconciliation.
The actual website cart is PKR 900 before and after end. Tokens/private worker
proofs are not written into this trace. Both disposable servers are stopped.

## Gate coverage

- Repeated start and end are idempotent for one attempt; a second start cannot
  replace a live or unresolved generation. Cancellation before preparation leaves
  a tombstone. Cancellation during dispatch and HTTP caller cancellation retain
  task/result ownership and clean up the eventual dispatch.
- Permission rejection and manual/end selection during permission, preparation,
  seat join, app registration, context publication, playback, dispatch readiness
  and status polling cannot make the cancelled controller active. Late media/seats
  are disposed. Late completion from an old attempt cannot overwrite a newer
  active generation's status.
- Tests use the real Phase 2 SessionStore to authorize lifecycle requests and
  preserve a nonempty cart. Another owner cannot end the generation. Supplied
  room/dispatch/identity fields, wrong generation, wrong roles, stale revision
  and foreign Origins are refused. Tokens use server-selected identities,
  session/generation/role attributes and restricted publish/metadata grants.
- Missing app seat, worker unavailability, bad worker proof, missing Phase 4
  runtime, bound seat disconnect, shopping expiry and idle/absolute expiry cannot
  grant greeting permission. A fake runtime can start only after the actual
  worker startup function has obtained authorized readiness.
- The integrated room gate validates v2 sender identity, role, session,
  generation and topic/type; stale context cannot replace newer context.
  The real RTC bridge no longer selects arbitrary non-agent participants.
  An integrated launch selects `website`; unknown modes and missing integration
  context fail clearly rather than producing a MockAdapter.
- Create-response loss is reconciled by trusted dispatch metadata without a
  second create. Unresolved create outcomes and transient deletion failures
  stay observable and block replacement. Dispatch deletion and room deletion
  are distinct fields; success is not fabricated after a soft failure.
- Local track stop/audio close precede server end. Fake server cleanup failure
  leaves local handles stopped while reporting remote cleanup pending. Token
  refresh preserves identities/room and cannot revive an ended generation.

## Repository-wide regression

The full agent suite is rerun, including the unchanged v1/v2 contract suites:

| Check | Result |
|---|---|
| Full agent pytest | 275 passed, 1 existing failure: `test_no_mock_imports_outside_adapters`, from the pre-existing import in `integration/scenarios.py` |
| Full agent lint | 39 existing issues |
| Full agent pyright | 27 existing errors, 2 warnings |

Focused changed-code checks are clean. These broader failures are retained,
not fixed, waived or labeled as new Phase 3 successes. The verifier restores
legacy evidence and frozen v1 files in `finally`. No old acceptance report,
recording, prompt, specification or read-only original phase plan was changed.
All existing Phase 0–2 dirty work is preserved. No commit/push/deployment occurred.

## Limits and phase boundary

No real Cloud dispatch, provider, worker process, browser rendering, microphone,
speaker, WebRTC session or human listening test ran. Node tests simulate SDK/media
handles. The two HTTP servers use the actual website and lifecycle API with a fake
LiveKit implementation. These cannot establish physical microphone release,
audible greeting timing or real provider cleanup behavior.

Coordination is single-process and in memory. Defaults are 30-second startup,
30-minute idle, two-hour absolute lifetime, five-second remote-operation timeout
and 512 retained generation records. Status polling does not renew assistance.
Sweep duration can exceed its one-second scheduling interval during remote I/O.
Process death can lose dispatch records; multi-instance/restart durability and
automatic cleanup of unknown Cloud resources are not guaranteed. Inspect/clean
old resources before a real integrated restart/deployment. `cart_preserved`
means assistance does not clear shopping state; it does not promise that an
expired or restarted website can recover it.

No new browser SDK dependency or page connection was added. The standalone
lifecycle controller is ready for Phase 5 integration. The worker runtime factory
is intentionally absent until Phase 4; current integrated startup therefore ends
with `integrated_runtime_unavailable` rather than greeting from the v1 mock path.
This is the explicit phase boundary, not evidence of a working voice order.

See [lifecycle API, launch and limits](../../../docs/PHASE_03_ASSISTANCE_LIFECYCLE.md)
and ADR-0015. SDK behavior was checked against installed LiveKit API 1.2.1 / Agents
1.8.4 / RTC 1.1.20 and the official
[dispatch](https://docs.livekit.io/reference/python/livekit/api/agent_dispatch_service.html)
and [room](https://docs.livekit.io/reference/python/livekit/api/room_service.html)
references. Phase 4 has not started.
