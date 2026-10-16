# FoodEase integration contract 2.0

**Phase 2 addendum:** The website now enforces this contract through its shared
application authority. Canonical models live in `foodease_contract.models`; the
agent path below remains a compatibility import. Schemas are unchanged. Examples,
MANIFEST and transport metadata below describe the frozen Phase 1 capture and
are hash-pinned by the exporter. Current API conformance and runtime limits are in
[the Phase 2 document](../../../orchestration/docs/PHASE_02_APPLICATION_AUTHORITY.md).
LiveKit transport and the voice worker remain unactivated. The Phase 1 record follows.

Frozen for final orchestration Phase 1 on 17 October 2026. This is the executable
contract for the next integration phases, **not an activated runtime migration**.
The current website, worker, broker and LiveKit adapter still use v1. Original
contract/v1 files and handover copies remain unchanged.

Canonical Python models: `foodease_agent.contract.v2.models`. Typed projections:
`foodease_agent.contract.v2.projection`. JSON Schema is generated from those models
with operation-dependent argument/result conditionals added by the exporter.
Cross-message identity, arithmetic and authorization invariants additionally
require the executable guards below; standard JSON Schema cannot express all of
them. Consumers must not rely on JSON Schema validation alone.

## 1. Version and migration

Version 2.0 is a major change: checkout confirmation tokens/summary identities,
strict argument types and correlated revision-bearing envelopes are mandatory.
It is not a silent minor update of frozen v1's optional-token interface. All
thirteen operation strings and existing thirteen event types are preserved.

Use explicitly versioned RPC/topic names during migration. A v1 peer must not
receive a v2 payload on its old channel. No automatic downgrade or fallback to a
mock cart is allowed. Unrecognized versions fail before domain execution.

Phase 1 provides validation, projection, schemas, examples and correlation
policies only. Phase 2 implements actual per-session authority, confirmation
binding, idempotency/result storage and lookup. Phases 3–5 wire the lifecycle,
worker and browser. The existing v1 website still accepts requests that v2 rejects;
the v2 schemas do not retroactively enforce policy on those existing endpoints.

## 2. Real-implementation field matrix

| Current website/agent field | Canonical 2.0 field | Mapping / authority |
|---|---|---|
| Website cart result `verified_state.lines` | Same `lines` everywhere | Current broker's `cart` lookup must migrate in Phase 4 |
| Agent MockAdapter result `verified_state.cart` | `verified_state.lines` | Only explicit legacy_mock_cart projection; alias forbidden on v2 wire |
| Website cart `line_total` | Required line_total | Keep authoritative value; validate price × quantity, don't drop it |
| Unit price, subtotal, fees, total | Same fields; finite nonnegative PKR, cent precision | App computes; models check arithmetic; no client price override |
| Live tool `vegetarian: true` | `tags: ["vegetarian"]` | normalize_filters; flag absent from canonical wire |
| Live tool `vegetarian: false` | Clear positive vegetarian constraint | Does not mean exclude vegetarian food; contradictory tags reject |
| Website category/max-price stored outside snapshot | Required nullable category/max_price_pkr in snapshot | Projection requires actual domain fields; never infer them from UI/LLM |
| Website filter/search `items` | Bounded items plus result_count | First 25 ordered IDs, true count before truncation |
| Website empty search | `query: ""` | Explicit supported search-clear operation |
| Website `route` | home/menu/item/cart/checkout/confirmation | Categories are filters; category names are not route aliases |
| Website result lacks operation | Required payload.operation | Copy from originating validated request and correlate it |
| Website result lacks event metadata | Required outer envelope | App supplies session/turn/event/reply/revision; never invent business outcome |
| Website get_current_context returns snapshot v1 | Typed snapshot v2 with full filters | Explicit projection of real domain state |
| Website summary_revision and confirmation_token | Required on successful summary; both required on submit | Current raw token is illustrative legacy data, not proven v2 authorization |
| Website demo_order_id/demo/order | Same typed receipt | `demo` must be true; order contains canonical cart summary |

Website projections do not execute actions, modify the domain or rename session
IDs. The fixture exporter creates a separate in-memory website domain using the
real seed, captures outputs, then projects them. Its temporary stripping of the
new submit argument summary_revision is fixture-only compatibility with today's
domain; production v2 must never strip or ignore this binding.

## 3. Envelope: every application event

| Field | Type / rule |
|---|---|
| schema_version | Required literal "2.0", including in context snapshots |
| session_id | Required nonempty ID, at most 128 characters; bound shopping session |
| event_id | Required unique ID, at most 128 characters; transport replay dedup key |
| turn_id | Required nonempty ID for actions/results, speech, typed input and clarification; nullable for unrelated lifecycle/context events |
| timestamp | Required timezone-aware RFC3339 timestamp; not a substitute for ordered revisions |
| context_revision | Required nonnegative strict integer for action requests/results, context and typed input; nullable for other events |
| type | One of the thirteen event strings below; discriminates the payload schema |
| payload | Strict typed object; unknown fields are rejected |
| reply_to | Additional required field only on app.action_result; original request event_id |

Action ID is payload.action_id, distinct from event_id/turn_id. App-result
context_revision is the committed app revision associated with that result; an
idempotent replay returns the original outcome and revision, not a fabricated new
event. A fresh reconnect context is sent separately.

`assert_correlated(request, result)` requires equal session_id, turn_id, action_id
and operation, and result.reply_to = request.event_id. A result from another
action/session cannot authorize success speech. `get_current_context` results
also require the nested snapshot's session/revision to match the result envelope.
Context events require their payload session/revision to match the envelope.

## 4. Exact thirteen operations

Arguments are objects, never selectors, JavaScript or natural-language product
guesses. Stable item IDs match `^[a-z][a-z0-9_\-]{1,63}$`. Quantity is a strict
integer 1–99: numeric strings, booleans and fractional numbers reject.

| Operation | Arguments, defaults and constraints | Successful verified_state |
|---|---|---|
| navigate | target: nonempty semantic ID ≤64 chars | {route} using canonical route enum |
| search_menu | query: string 0–200 chars; empty clears | {items: VisibleItem[≤25], result_count: integer ≥len(items)} |
| filter_menu | tags: unique strings ≤16, default []; category: item-shaped ID or null, default null; max_price_pkr: Money or null, default null | Same items/count result; operation replaces filter set; search remains separate |
| select_item | item_id | VisibleItem |
| get_item_details | item_id | VisibleItem + description ≤2000 chars, ingredients string[] or null, ingredients_available boolean |
| get_cart | {} | CartSummary |
| cart.add_item | item_id; quantity default 1 | CartSummary |
| cart.set_quantity | item_id; quantity required, absolute | CartSummary |
| cart.remove_item | item_id | CartSummary |
| checkout.get_summary | {} | CartSummary + summary_revision; outer payload also requires confirmation_token |
| checkout.submit_demo_order | confirmed: strict true; confirmation_token: nonempty ID; summary_revision: nonnegative strict integer | {demo_order_id, demo: true, order: CartSummary} |
| undo_last_reversible_action | {} | CartSummary; no undo of a submitted order |
| get_current_context | {} | {snapshot: ContextSnapshot} |

VisibleItem: item_id, name (1–200 chars), price, currency="PKR", descriptors (≤16
strings), available boolean. ItemDetails ingredients_available must agree with
whether ingredients is null. Missing ingredient facts are not an empty confident
claim. App availability/catalog authorization is a domain check, not inferred
from an ID regex.

CartSummary requires lines (≤32), currency="PKR", subtotal, fees (≤16), total.
Each line requires item_id/name/quantity/unit_price/line_total. Each fee requires
code/label/amount. All Money values are finite nonnegative numbers with cent
precision; price × quantity equals line_total, subtotal equals sum(lines), and
total equals subtotal + sum(fees). Duplicate cart item IDs reject. No hidden
fallback totals or empty-cart speech from a missing alias.

## 5. Context and revision policy

ContextSnapshot requires schema_version/session_id/revision/route/focus_item_id,
valid_actions (≤13 operation strings), valid_navigation_targets (≤64 semantic IDs),
filter_tags (≤16), category/max_price_pkr/search_query (nullable), visible_items
(≤25 ordered rows), cart, checkout_available/action_pending booleans and language
(1–35 chars). Nullable values are explicit; omitted filter state is not guessed.

App revision increases after a meaningful state change. `assert_revision` allows
an older request revision only for get_item_details/get_cart/get_current_context,
which read current state and return its current revision. Future revisions always
reject. Every other operation, including checkout.get_summary (it changes review
state), requires expected == current. Missing revision fails envelope validation.

The app executes revision check + operation + result retention atomically in
Phase 2. Context publication alone does not make a stale request safe. Clients
ignore lower-revision context, and invalidate contextual references on meaningful
manual selection/page changes. The same session/revision must identify one state;
equal revision with different state is a protocol error.

For a new successful action: commit state/revision/result together, return that
result and publish the associated context. Network arrival order is not assumed.
Consumers correlate outcomes by action ID while rendering only the newest
context. An old result may acknowledge its real effect but cannot overwrite a
newer UI snapshot. After reconnect, request current context rather than relying
on a one-time broadcast or replaying uncertain mutations.

## 6. Result statuses and errors

| Status | Required meaning |
|---|---|
| success | Typed operation-specific verified_state, no error_code; action actually completed |
| failed | Known failure, nonnull error_code, no verified_state; no speculative success |
| rejected | App refused input/authorization/availability; no verified_state |
| stale_context | error_code=stale_context; expected revision invalid; no mutation |
| requires_confirmation | error_code=confirmation_required; no submission |
| timeout_unknown | error_code=timeout; outcome unresolved; no success/failure assertion or automatic mutation replay |

error_message is optional user-safe text ≤500 chars. The allowed error codes are
unknown_operation, invalid_arguments, missing_action_id, stale_context,
not_available, out_of_stock, confirmation_required, confirmation_expired, timeout,
rejected, internal, rate_limited, idempotency_conflict, session_mismatch,
unauthorized_sender, payload_too_large and unsupported_version.

Only a successful checkout.get_summary carries confirmation_token. Invalid wire
requests/unknown operations are rejected before a typed shopping request exists;
return a safe protocol error, not a made-up successful ActionResult for an unknown
operation. Transport exceptions and user-safe errors are distinct from provider
exception details; do not echo raw payloads, tokens or stacks.

## 7. Confirmation and idempotency

An opaque app-issued token must bind session, current cart/summary revision,
itemized prices/fees and the intended demo submission. A typed `confirmed=true`
flag alone is insufficient. Phase 2 must validate that binding server-side and
consume it once, while preserving the original result for duplicate requests.
The current domain's predictable optional token is not accepted as proof that
this is already enforced. Token generation/storage are not implemented in Phase 1.

summary_revision is the app-issued identity of the reviewed cart, distinct from
the outer full-context revision. Cart changes invalidate the summary/token;
harmless orientation changes cannot silently change what was approved. The live
agent must additionally bind explicit user consent to the summary actually
delivered; an interrupted/unheard summary and “yes, but change it” do not consent.

Action identity: (session_id, action_id). request_fingerprint hashes canonical
operation/arguments/session; it excludes transport event IDs, timestamps and
expected revision. Same ID + same intent returns the original stored result;
same ID + different fingerprint rejects idempotency_conflict without another
effect. Check a retained duplicate before applying current-revision rejection.
Concurrent duplicates must be serialized, not executed twice. Interrupting speech
never deletes a committed action or implies business rollback.

## 8. Read-only action lookup

Reserved app-seat RPC: `foodease.action_status.v2`. Proposed HTTP equivalent:
`GET /api/v2/app/actions/{action_id}`. Neither exists in the runtime yet.
This is a transport reconciliation capability, not a fourteenth LLM shopping tool.

LookupRequest requires schema_version/session_id/event_id/timezone-aware timestamp
and action_id. LookupResponse requires schema_version/session_id/event_id,
reply_to (lookup request event_id), timestamp, action_id and state. Only state
found carries result, the original full app.action_result envelope. Its session
and action must match the lookup response. `assert_lookup_correlated` verifies
outer request/response session, reply identity and action.

| Lookup state | Meaning / safe consequence |
|---|---|
| not_seen | No record in this still-valid session epoch; not proof that a delayed request can never execute |
| pending | Request accepted/queued/executing, no terminal outcome retained yet |
| found | Return original correlated result, including original receipt if cart is now empty |
| expired | Session/result retention no longer available; never reinterpret as “order failed” |

Project defaults: idle session TTL 30 minutes, absolute TTL 2 hours. Retain action
fingerprints/results/receipts for the full session; do not silently evict results
while retaining executable session authority. Bound capacity at admission and
refuse new work if full. Expired/unknown session owners fail authorization and
cannot enumerate other users' results. Process restart with in-memory state ends
the old session epoch; it cannot honestly answer not_seen for lost history.

Lookup is read-only: no cart mutation, new action ID/submission, revision bump or
confirmation. A timeout triggers reconciliation, never an automatic second
mutation—even a not_seen lookup may race a delayed original request.
An unresolved timeout_unknown is not an authoritative found outcome; report
pending until the application knows what happened.

## 9. Transport, direction and sender authorization

Every message, including lookup, must fit the complete compact UTF-8 JSON budget
of **14,336 bytes (14 KiB)**, a project cap below the documented 15 KiB RPC limit.
The budget counts encoded bytes, not characters or payload-only size. Validate
before send and after receive; never silently truncate cart/receipt/confirmation.
If a response exceeds the budget, retain its actual outcome for lookup and report
the transport limitation honestly. Large retrieval may need a protected HTTP path
later; this contract does not invent a successful truncated result.

The Python RTC 1.1.20 RPC signatures were inspected in Phase 0; the initial JS
reference is livekit-client 2.15.4. Current vendor RPC limits are documented at
[LiveKit RPC payload format](https://docs.livekit.io/transport/data/rpc/). The cap,
channel names and five-second RPC timeout below are project decisions, not
measured network or provider performance. Recheck installed APIs before wiring.

| Channel | Direction / allowed bound publisher | Payload |
|---|---|---|
| foodease.action.v2 RPC | Agent → app; verify RPC caller identity | Full agent.action_request; full app.action_result response |
| foodease.action_status.v2 RPC | Agent → app, same bound session | LookupRequest → LookupResponse |
| foodease.context.v2 reliable data | App → agent/user | app.context_snapshot / app.context_updated |
| foodease.control.v2 reliable data | User → agent | app.control; event/session dedup applies |
| foodease.text_input.v2 reliable data | User → agent | app.text_input, not an app-seat RPC |
| foodease.events.v2 reliable data | Agent → user/app | status, transcripts, clarification, control, errors; action events may be mirrored but must never execute twice |

SessionBinding names distinct user/app/agent participant identities for exactly
one shopping session. `assert_authorized` requires that session and the correct
publisher: app for context/results, user for app.control/text_input, agent for
agent.* and mirrored transcripts. Do not select “first non-agent participant” or
trust a message's claimed role. The session service supplies the binding; actually
authenticating and associating rooms is Phase 3 work. Lookup RPC caller identity
must be checked with the same bound-agent rule.

Agent/status/transcript mirrors are one source for the panel; native streams may
be adapted into them, but the browser must not render both as separate replies.
The app seat has no microphone and no audio playback path. The user seat owns
microphone and one audio output path. Browser controls/typed input do not gain
authority to manufacture an app.action_result.

## 10. Exact event payloads and transcript lifecycle

| Event type | Payload |
|---|---|
| agent.status | state from existing product-state enum; optional detail ≤500 chars |
| transcript.user.partial / transcript.user.final | utterance_id, text ≤2000 chars, source="speech" |
| transcript.assistant | utterance_id, text ≤2000 chars, phase started/updated/completed/interrupted |
| agent.action_request | action_id, operation, validated arguments |
| agent.clarification_required | question 1–500 chars; ≤8 choices with stable id and label |
| agent.control | pause/resume/mute/unmute/end/switch_mode intent; nullable manual/voice/typed mode |
| agent.error | existing user-safe code, message ≤500 chars, fatal boolean |
| app.context_snapshot / app.context_updated | Full ContextSnapshot |
| app.action_result | Correlated typed ActionResult described above |
| app.control | start/pause/resume/mute/unmute/end/explain/switch_mode/pause_tips/resume_tips; nullable mode |
| app.text_input | text 1–2000 chars; separate from speech transcripts |

switch_mode requires mode. Mode controls convey user intent; they do not bypass
consent or browser permission. Speech confidence is not a required field; never
manufacture it.

Display transcript identity is (session_id, turn_id, utterance_id). A final user
transcript replaces that utterance's interim text. Assistant text is the actually
delivered prefix: started can be empty, updates replace the prefix, and completed
or interrupted terminates it. Never append intended but unheard continuation.
Use distinct utterance IDs for multiple assistant messages in a turn. Duplicate
event IDs are ignored; stale updates after terminal phase must not revive text.
The examples with different assistant phases are independent fixtures, not one
contradictory completed-then-interrupted timeline. Lifecycle playback behavior is
verified in the later worker/browser phases.

## 11. Verification and regeneration

From voice-agent/ after locked setup:

```powershell
$env:PYTHON_DOTENV_DISABLED = '1'
.\.venv\Scripts\python.exe tools\freeze_contract_v2.py
.\.venv\Scripts\python.exe tools\freeze_contract_v2.py --check
.\.venv\Scripts\python.exe -m pytest tests\test_contract_v2.py tests\test_contract_v1.py -q
.\.venv\Scripts\python.exe -m ruff check src\foodease_agent\contract\v2 tools\freeze_contract_v2.py tests\test_contract_v2.py
.\.venv\Scripts\python.exe -m pyright src\foodease_agent\contract\v2 tools\freeze_contract_v2.py tests\test_contract_v2.py
```

The generator captures all thirteen successful operations against the actual
website FoodEaseDomain and seed data, not MockAdapter. It also captures real
domain rejected/stale/requires-confirmation results. Only failed/timeout_unknown
examples are synthetic transport fixtures, identified in MANIFEST.json. Tests
reproduce the legacy mismatch before proving explicit v2 projection/validation.

Both trees contain identical schemas, positive/negative examples and this README.
--check is read-only and detects modified, missing or extra generated JSON files.
Normal tests invoke it, making drift a required verification failure. Generated
files are never treated as a working service, live evidence or teammate signoff.

JSON Schema validates shapes and operation/status branches. Consumers also need
the runtime guards for price arithmetic, unique IDs/tags, nested session/revision,
request/result correlation, authorized sender and revision/idempotency policies.
These extra checks are documented and tested, not implied to be standard JSON
Schema features. Mandatory app-side storage/binding remains Phase 2.
