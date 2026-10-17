# Final orchestration Phase 8: recovery

Scope: final orchestration Phase 8 only, on `codex/phase-8-recovery`.
Earlier Phase 4–7 uncommitted work is retained. No new shopping operations,
contract changes, UI redesign, dependency upgrades, deployment or Phase 9 work.

## Provider failures

The production runtime subscribes to the installed SDK's `error` event. Exhausted
STT/TTS failures synchronously invalidate the old turn, references and checkout
consent, interrupt output and disable both audio directions. They switch to silent
typing, preserving the healthy LLM and website lane. The SDK error is marked
recoverable to retain that lane; the failed speech pipeline is not reopened in
the same generation. The browser stops/unpublishes capture and detaches playback.
LLM/unknown fatal failures end assistance and leave manual website controls.
Transient errors remain with the SDK's bounded provider retry policy. There is
no application mutation retry. Error messages contain no provider exception text.
Unexpected SDK session closure also tells the browser to stop.

Tests include local subclasses of the actual SDK STT/TTS/LLM interfaces raising
connection errors. SDK forwarding, runtime degradation and a subsequent real SDK
text reply are exercised. Browser STT/TTS tests inject typed SDK error events;
the model test raises inside a local streaming provider. None is a vendor outage.

## Reconnection and modes

Either browser seat entering reconnect disables capture, detaches audio, clears
reviewed summaries and blocks new RPC mutations/text requests. A 15-second deadline
ends locally if recovery cannot finish. Both seats must return before recovery
starts. Only read-only lookups and page reads are allowed through the barrier.
Original pending IDs are looked up; fresh website state is rendered/published.
The worker fetches its own session-bound snapshot and clears confirmation,
references, cached details and old turn authority even if the revision is unchanged.

A resume acknowledgment carries the initiating control's unique turn ID, within
the existing v2 envelope. Only that acknowledgment releases the browser barrier.
Late acknowledgments, old room events and audio subscriptions cannot restore an
ended session. Existing paused mode stays paused. A chooser without a voice/manual
decision ends on connection loss; it cannot silently become voice mode. Silent
typing stays silent; voice restores only its existing live tracks and prior consent.
Worker-room reconnects independently revoke admission and fetch fresh state before
continuing. Failed refresh stays paused. Already submitted business tasks remain owned.

## Outcome recovery

| Observation | Meaning and behavior |
| --- | --- |
| Local revocation before transport starts | Known not submitted; no website mutation |
| `found` with correlated terminal result | Retain original outcome/receipt; render fresh state; never submit again |
| `pending` | Authority is processing the original request; keep ownership |
| `not_seen` | Not registered at lookup time; a delayed request could still arrive; keep ownership |
| `expired` | Outcome is no longer retained; completion cannot be verified; keep ownership |
| Lookup/network failure | Unknown; keep ownership, no automatic retry |

The tool's unresolved result stays `timeout_unknown`, with a separate recovery
state and user-safe explanation. No nonterminal lookup is converted into a
business failure. A committed add or demo order with a lost reply is recovered
once by original identity. Manual changes during a delayed result remain current;
old results do not roll them back or authorize speech under a newer turn.

The website retains minimal pending envelopes and assistance request/generation
IDs in session storage. Arguments, checkout tokens, room credentials and provider
keys are not persisted there. Reload reattaches shopping and reconciles cleanup
without capture or dispatch. New assistance waits for positive cleanup and another
user gesture. A browser-native Web Lock prevents a duplicated tab from taking the
same assistance owner; server-side generation admission remains the fallback.

Shopping retention remains process-local: 30-minute idle / 2-hour absolute limits,
at most 128 sessions and 256 actions per session. Confirmation tokens expire after
5 minutes. Assistance records are also process-local and bounded. Restart outside
retention is explicitly unrecoverable: no invented receipt, replacement mutation,
or claim that an unknown old dispatch was cleaned up. Unconfirmed cleanup blocks
replacement and is reported as pending.

## Background, credentials and shutdown

Backgrounding/pagehide ends local assistance immediately. Returning to the page
never reopens capture. Retained cleanup identity allows a reload to finish teardown.
Lifecycle status is checked every 15 seconds while active; failures stop assistance.
At the issued credential lifetime the client ends locally and asks for a new user
gesture. It deliberately does not reconnect using an expired token or create a
replacement worker automatically. The installed browser SDK manages its own active
connection token updates; no private SDK token mutation API is used here.

Shutdown interrupts speech, disables audio and drains owned submission tasks.
Read-only reconciliation may stop, but a business write is not canceled or replayed.
Actual receipt/status remains with the website while its retention is valid.

## Verification and remaining live gate

Run from the repository root:

```powershell
.\orchestration\.venv\Scripts\python.exe orchestration/tools/phase8_verify.py --output orchestration/evidence/final/phase-08/run-2
```

See [evidence](../evidence/final/phase-08/report.md) for counts, failure matrix,
inherited failures and exact raw logs. The runner disables dotenv, strips provider
keys and preserves legacy contract/evidence artifacts.

**Implementation checks are local/offline. Live activation is not verified.**
The bounded runtime observations record actual SDK event arrivals and false
interruption `resumed` values, without text/audio. They are not audible-stop
latency measurements. There are zero live vendor-outage samples, zero measured
audible barge-ins and zero human-rated false interruptions from this phase.
Use the [live checklist](../evidence/final/phase-08/live-checklist.md) and blank
measurement sheet before claiming that part of the Phase 8 gate. Phase 7's real
model/listener gate also remains open. Phase 9 is the one planned phase remaining;
it has not been implemented here.

SDK references checked against installed Python agents 1.8.4 / browser 2.15.4:
[error and interruption events](https://docs.livekit.io/reference/agents/events/),
[browser room events](https://docs.livekit.io/reference/client-sdk-js/enums/RoomEvent.html).
Current online JS docs describe a newer version; installed public source was checked
before using the event names. No unsupported token-update API was assumed.
