# Final orchestration Phase 4: live conversation and actions

Phase 4 attaches the v2 conversation runtime to the existing bound worker startup.
It retains LiveKit's streaming STT → Gemini → Cartesia path. The integrated agent
and text-driven tests use the same turn, control, broker and confirmation policy.
The legacy standalone v1 harness remains separate and unchanged.

Browser SDK/page wiring is Phase 5. The opening mode-choice conversation is Phase 6.
There are no UI, CSS, animation, payment or database changes in this phase.

## Runtime and startup

`FOODEASE_APP_TRANSPORT=website` now selects `create_integrated_runtime` from the
actual worker entrypoint. The factory verifies application context, forces
preemptive generation off and prepares the configured streaming session. Session
start/output still waits for Phase 3's authenticated worker-ready acknowledgement.
The acknowledgement must match schema, shopping session, generation, request and
participant binding. Missing runtime/context or revoked readiness fails closed.

Room I/O links only the bound user identity. Native unversioned text input is
disabled; authenticated `app.text_input` goes through the same committed-turn
path as speech. The initial mode is unset: no tools or idle prompts are enabled
until explicit `app.control` mode selection (`voice` or `typed`, or `start` with
that explicit mode). Phase 6 will add the opening voice-choice flow.

The gate validates sender role, identity, session, generation and topic/type. It
notifies the runtime of fresh context, canonical controls/text and bound-seat
disconnect. Event/turn replay identities are retained within finite budgets;
exhausting the budget closes assistance rather than silently accepting replays.
Pre-start controls/text are retained in a bounded queue. End/manual and disconnect
revoke the local lane immediately. Spoken mode changes publish `agent.control`
to the bound browser seats for Phase 5 to reflect and coordinate remote teardown.

## Context, tools and turn admission

The SDK agent registers exactly thirteen tools. Every tool uses the same broker
and shared v2 argument/result validation. Filters normalize vegetarian into tags,
preserve omitted filters and support explicit clearing. Results contain bounded
verified facts: real result counts/items, descriptions/ingredient availability,
cart quantities/fees/totals and demo receipts. App confirmation tokens stay inside
the runtime and never enter tool facts or the LLM context.

Each LLM step receives bounded current application data, preferences and current
reference-list state, explicitly labelled as untrusted data. New context updates
orientation and filters, clears obsolete lists/repeat text and interrupts obsolete
guidance. Only context associated with a pending or verified own action can
advance that action's turn. References use an actual current presented list;
ambiguous "other", tied cheapest choices and stale references request clarification.

A user message ID identifies an immutable turn lane and authorization epoch;
the returned SDK speech handle is bound to it. Commit occurs at the SDK's completed
user-turn hook, which calls public `generate_reply` and raises `StopResponse` to
prevent a second automatic reply. New speech uncommits the old lane. New input,
manual context, mode changes and explicit discard revoke old lanes. Admission
checks identity, source, commit/discard, interruption, mode and expected revision,
including immediately before entering the submission transport. Preemptive
generation cannot be enabled by an environment override for this runtime.

The output stream keeps tool chunks and conversational sentences streaming. It
sanitizes internal speech artifacts and checks common English outcome claims
against current correlated results. This is an additional guard, not a general
natural-language fact verifier or evidence of live conversational quality.

## Action ownership and reconciliation

The broker registers a pending action **before** scheduling submission. It owns
the task and awaits it through `asyncio.shield`; speech/tool cancellation, manual
selection and disconnect cannot cancel a submission already entered. A revocation
before the owned task enters the transport is a known local rejection and sends
nothing. A late terminal outcome is retained without speaking under a newer turn.

Each action uses a fresh ID and expected authoritative revision. A lost, invalid
or unknown response triggers read-only lookup of that original action, never a
second submission. Unresolved outcomes retain their records and block further
actions. Three finite read-only follow-ups may reconcile a later terminal result;
otherwise uncertainty remains explicit. Shutdown drains owned submission tasks
for up to 16 seconds, retains unresolved ownership and stops local media. Read-only
follow-ups can be cancelled at shutdown; submission tasks cannot. These are
process-local guarantees, not durability across worker/process termination.

## Checkout and delivery

The authoritative summary supplies a cart revision and app-issued token. The
runtime binds them to the exact summary/hash, current cart, fresh summary identity
and a delivered prompt. The model cannot supply `confirmed`, a token or revision
to the submit tool. Only a new committed exact affirmative can authorize it.
Consent is consumed before submission; corrections, unrelated answers, stop,
mode changes and cart changes invalidate it. A later casual yes cannot revive it.

For voice, the exact verified cart/fees/total and demo-order question are queued
as a separate interruptible `session.say`. A tool does not await its own queued
speech, which would deadlock SDK scheduling. Delivery requires its public speech
completion callback, no interruption/error, an enabled attached audio sink and
the same active turn/cart. Partial, failed, queued or absent audio cannot confirm.
Actual browser playback still needs Phase 5 and live acceptance evidence.

For typed checkout the worker calls the bound app-seat RPC
`foodease.present_summary.v2`. Phase 5 must render the exact text and return a
post-render receipt. Its request fields are:

```text
schema_version: "2.0"
session_id, turn_id, summary_id: strings
summary_revision: nonnegative integer (the cart summary revision)
summary_hash: string
text: the exact verified summary and confirmation question
```

The response echoes every field except `text`, plus strict boolean `delivered: true`.
Wrong/missing identifiers, wrong types, extra fields, timeouts or absent RPCs do
not prove delivery. This is an additive presentation RPC, not a fourteenth business
operation or a change to frozen v2 events. The existing thirteen operations and
thirteen event types remain unchanged.

## Controls and idle prompts

Stop interrupts speech without cancelling actions. Pause/resume and mute/unmute
change the live output lane; manual disables local media and admission. Repeat
uses the last completed current-page reply. Back and undo execute actual website
operations through the broker. Speed uses the provider's public `update_options`
only when supported; failures are stated truthfully. Volume directs the user to
device controls because this runtime has no validated remote volume API.

The running session owns a finite idle scheduler. It emits at most two tips and
then remains quiet. User/assistant speaking state, text/control/manual context,
pending actions, pause-tips, mode selection and disconnect govern scheduling.
There are no tips before selection, in manual/typed mode, during speech or while
an action outcome is pending. Tips never mutate the application.

## Verification and limits

Run `orchestration/.venv/Scripts/python.exe orchestration/tools/phase4_verify.py`
from the repository root, or `.venv/Scripts/python.exe tools/phase4_verify.py`
from `orchestration/`. It disables dotenv/provider credentials, uses local fake
providers/media, preserves frozen v1 and historical evidence, and records the
full suite's pre-existing failures separately. See the Phase 4 evidence report.

SDK use was checked against installed `livekit-agents 1.8.4`, `livekit-api 1.2.1`
and `livekit 1.1.20`, including local public source and official documentation:
[turn handling](https://docs.livekit.io/agents/logic/turns/),
[tools](https://docs.livekit.io/agents/logic/tools/),
[audio](https://docs.livekit.io/agents/multimodality/audio/) and
[Python reference](https://docs.livekit.io/reference/python/livekit/agents/index.html).

The implementation gate uses real SDK tools/callbacks, an actual SDK session
with a local streaming LLM, the production v2 adapter with fake RTC and the real
website SessionStore/domain. It establishes no Cloud, real microphone, provider
speech, browser rendering, audible quality, latency or deployment evidence.
