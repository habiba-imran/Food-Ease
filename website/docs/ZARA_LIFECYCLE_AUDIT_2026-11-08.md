# Zara refresh, stop and restart audit — 2026-11-08

Refresh now starts a fresh Zara conversation and mode choice while retaining the existing
shopping cart. Stopping assistance ends the caller's session, audio and microphone;
it does not stop, delete or redeploy the shared Cloud worker.

## Findings and fixes

1. **Persisted conversation activation:** The page stored `foodease.assistance-used.v2`
   and restored `hasActivated` after refresh, causing a new conversation to use the
   previous conversation's resume activation. Activation is now document-local. The
   obsolete flag is removed. Fresh activation uses `switch_mode` or chooser `start`,
   never the previous document's `resume`.
2. **Overlapping teardown:** Stop, SDK disconnect and immediate restart could issue
   four concurrent end requests for the same generation. A regression reproduced this.
   All paths now share one in-flight cleanup, retain uncertain cleanup for explicit
   retry, and reuse the confirmed ended result. Replacement waits for cleanup; the
   microphone is stopped immediately, independently of the network result.
3. **Reload recovery feedback:** Recovering an old cleanup identity used to emit manual
   mode. Completed automatic recovery now returns to the fresh welcome state. An
   explicit manual choice during that recovery wins over the automatic welcome state,
   including while waiting for the asynchronous tab lease.
4. **Back/Forward cache:** A restored document can contain the old JavaScript heap and
   conversation UI. A persisted `pageshow` now reloads the document, clearing old
   transcript, mode, draft and capture intent while preserving the cart attachment.
5. **Asset delivery:** Updated module versions and both static/public copies together.

No new shopping mutation, replay, automatic microphone permission, provider/model
change or conversation persistence was introduced. The microphone still starts only
after explicit activation. Wake recognition also remains a fresh opt-in after refresh.
The unresolved-action ledger remains intact for read-only reconciliation; refresh
does not repeat an uncertain cart write or turn an old checkout consent into a new one.

## Edge-case behavior

| Edge case | Expected behavior |
|---|---|
| Refresh during voice, pause or typing | Old generation ends; new welcome; microphone off; cart retained |
| Activate after refresh | New request/generation and fresh introduction |
| Browser Back/Forward cache restore | Reload into a fresh document; no capture resurrection |
| Failed unload/end request | Keep cleanup identity; no replacement until explicit retry confirms cleanup |
| Stop during permission/join/context/readiness | Late tracks and seats close; canceled startup cannot activate |
| Rapid Stop + disconnect + Start | One cleanup request; at most one replacement generation |
| Manual choice while cleanup is running | Remain manual after cleanup; no late capture |
| Temporary RTC reconnection | Existing consent-bound recovery checks fresh context; no duplicate dispatch/write |
| End during reconnect, expiry, agent loss | Local capture ends; late events cannot reactivate it |
| Duplicate tab with the same cart attachment | Browser lease and server admission prevent overlapping assistance |
| Refresh while Hey Zara is enabled | Recognition stays off until explicitly enabled again |

The local cart survives only while its backend shopping session is retained. Existing
backend restart/expiry handling reports the expired attachment and offers a new cart;
it does not claim durable recovery.

## Shared worker and cold starts

Inspected production teardown: `AssistanceService.end` cancels only the bound generation,
deletes its dispatch and room, and never invokes a deployment stop/delete API. Worker
job shutdown closes that job's runtime. The installed LiveKit SDK handles termination
by closing the job process from its pool; it keeps the server/pool available. The
existing production `WorkerOptions` uses `prewarm_fnc` and a nonzero production idle
process pool. There is no need to preserve an old conversation or microphone to keep
the service available, and no worker rebuild is needed for these browser changes.

The authenticated [Cloud status check](lifecycle-audit-evidence/cloud-status.txt) showed agent `CA_gibAwTdK3sjn`, dispatch
`foodease`, version `ckhnpPJ2Lg5h`, **Running**, one replica, `minReplicas: 1`, in
Mumbai (`ap-south`). This is a point-in-time observation, not proof of indefinite
idle uptime or an account-plan entitlement.

LiveKit's current documentation states that production agents stay warm on paid
Ship/Scale plans, while Build/free production agents can scale to zero when idle.
All non-production deployments sleep when idle. Prewarming cannot override Cloud's
platform scaling policy. The account plan was not established from status and no
subscription, billing or replica setting was changed. For guaranteed warm hosting,
confirm a supported paid production plan or use an always-running self-hosted worker.
Do not use synthetic customer sessions or open microphones as keepalive workarounds.

References: [Cloud cold starts](https://docs.livekit.io/deploy/agents/managing-deployments/),
[deployment lifecycle](https://docs.livekit.io/deploy/agents/deployments/),
[prewarming](https://docs.livekit.io/agents/server/options/).

## Verification and rollout

- `node --test tests/*.test.mjs tests/*.test.cjs`: **63 passed**.
- `node tools/browser-test.mjs lifecycle-edge-cases.spec.mjs wake-word.spec.mjs --grep 'refresh|restored Back/Forward|failed unload' --reporter=line`:
  **6 passed**, including all five new lifecycle browser scenarios and wake refresh.
- Existing `voice-entry.spec.mjs` and wake scenarios: **18 passed** in the preceding
  combined run. That run initially had three new refresh-test assertion failures:
  the test expected an empty transcript container, but the fresh page contains static
  mode-choice help. The corrected assertions require zero conversation utterances;
  all three refresh scenarios then passed, including a fresh-generation activation.
  Total unique passing browser scenarios across those runs: **24**.
- `python -m pytest tests/test_app.py -q`: **3 passed**, one existing deprecation warning.
- Cloud authenticated status: **Running**, same existing agent; no deployment mutation.
- Source/public asset hashes match; `git diff --check` passed.

The overlapping-stop regression failed with four end calls before the fix and passed
with one afterward. Both manual-during-recovery races were also reproduced before
their fixes. The final JavaScript suite passed after the last lease-race change.

Browser tests use actual Chromium media tracks and the actual local shopping/agent
runtime with fake RTC, speech recognition and providers. The persisted-pageshow test
simulates the browser restore notification because request routing disables actual
BFCache. No new provider calls or caller-heard latency measurement were made.

These browser changes are local and require publishing the source and redeploying
Vercel. The backend is still awaiting the user's Render hosting, as documented in the
[hosting guide](../../deployment/RENDER_VERCEL_GUIDE.md). The previous provider quota
and ordering-language acceptance failures remain open; this lifecycle audit does not
change their status.
