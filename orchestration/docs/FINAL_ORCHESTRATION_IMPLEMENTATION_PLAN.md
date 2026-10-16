# FoodEase final orchestration implementation plan

Prepared for Habiba and Zainab on 17 October 2026.

Status: analysis and implementation plan only. No application implementation is included.
Code baseline: `main`, `23e2b64` (`Add website and update project code`).

## 1. Final outcome and boundaries

Opening FoodEase presents a clear choice of manual or assisted ordering. Once the user has enabled spoken interaction and browser permissions allow it, the assistant asks: “Hi! How would you like to order today—by voice, or browse yourself?”

- “Manual”, “I will do it myself”, and equivalent clear choices stop assistant audio, tips and microphone capture. The existing shopping session remains usable.
- “Voice” continues a natural conversation grounded in the current page, catalog, selected item and cart.
- The user can ask where they are, hear relevant page information, search/filter, open an item, add/edit/remove items, review the cart and explicitly confirm one simulated order.
- Voice commands produce the same visible results as the corresponding manual controls. Manual actions remain usable during assistance and immediately update agent context.
- Typed input uses the same conversation and action policy without impersonating a speech transcript.
- Switching modes, stopping speech, connection loss and provider failure preserve the true shopping outcome.
- Conversational quality includes flexible phrasing, mixed initiative, corrections, contextual follow-ups, natural pacing and interruption handling. It must be evaluated in the live worker, not inferred from scripted text tests.

Scope is functional orchestration and the minimum website behavior needed to connect it. No visual redesign, styling campaign, animations, AR expansion, new restaurant backend, real payments, accounts or database project. Necessary event listeners, mode controls, captions and state-driven rendering are integration work even though some changes belong in website JavaScript/templates.

“Read the page” means explain current semantic application context and explicitly requested details. “Click a button by voice” means invoke its registered semantic operation and render its verified outcome. Do not add arbitrary selector execution, coordinate clicking or unrestricted generated JavaScript. Optional decorative controls are outside the core voice vocabulary.

## 2. Opening flow: browser constraint and product decision

A fresh visit cannot reliably autoplay speech, and hearing a spoken answer requires explicit microphone permission. The existing specifications also require consent before listening. Browser permission previously granted is distinct from a product preference to start assistance.

Recommended flow:

1. Show the ordering-mode question immediately as accessible text; manual shopping is immediately available.
2. Offer a clearly labeled user gesture to enable the spoken welcome and microphone for answering it. Reuse the existing assistance surface; only minimum functional control/copy changes are needed.
3. Establish the session, attach audio, obtain permission and confirm playback readiness. Ask the short voice/manual question once; do not additionally play the old shopping greeting.
4. A clear manual response performs full assistance shutdown. A voice response activates shopping tools and continues with one useful invitation.
5. Silence or an ambiguous answer never activates shopping or submits an order. Offer at most one short clarification, then stay quiet with manual/typed controls available.
6. A direct manual selection needs no microphone, cloud connection or dispatch. A direct voice selection may bypass the spoken choice and begin assistance after consent.
7. Return to assistance uses a brief resume based on the preserved shopping session. It must not silently reopen the microphone after an explicit manual choice.

An already opted-in returning visit may attempt the spoken welcome where browser policy permits, with an activation fallback. A zero-interaction first-visit spoken conversation is not a portable acceptance condition.

Browser references checked during this analysis: [MDN autoplay](https://developer.mozilla.org/en-US/docs/Web/Media/Guides/Autoplay), [MDN getUserMedia](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia). These support the browser constraint; the mode flow above is the proposed product behavior.

## 3. Current implementation: what exists and what is missing

These findings come from source inspection. Passing helper tests does not establish that the live worker wires those helpers together.

| Area | Existing implementation | Remaining work / concrete gap | Main source |
|---|---|---|---|
| Manual application | FastAPI website, seed catalog, 13 semantic operations, cart totals, demo checkout, revision counter, action-result cache | One process-wide domain instance and fixed `foodease-local-session`; no shopper/session association | `website/src/foodease_website/app.py`, `domain.py` |
| Catalog | Website loads the 28-item frozen seed, PKR and 50 PKR fee | Live operation must use this domain exclusively; worker still defaults to its own MockAdapter | `catalog.py`; agent `adapters/dev_wiring.py` |
| Browser assistance | Mock status/transcript panel, typed form, mock action buttons | No LiveKit connection or session-service calls; typed text is displayed but not delivered to agent | `website/static/js/app.js:1063`, `:1119` |
| Browser/application consistency | Manual handlers call application actions; cart refresh uses backend data | Menu filtering also runs independently in JavaScript. Remote route/selection updates do not drive a unified renderer. Header anchors and dialog closures do not consistently publish semantic location | `app.js:268`, `:678`; `templates/index.html` |
| Shared contract | Strict Pydantic models, schemas, enums, transport defaults, mirrored handoff copy | Website cart lines contain `line_total`, forbidden by agent `CartLine`; website action results use `lines`, while agent broker/engine speech reads `cart` | agent `contract/models.py`, `broker.py`, `engine.py`; website `domain.py` |
| Filtering | Website accepts tags/category/max price | Live agent tool emits `category` and `vegetarian`; strict `FilterMenuArgs` accepts tags/max price. Valid voice filtering can fail before dispatch | agent `agent.py:182`, `contract/models.py:47` |
| Revision safety | Website checks supplied older revisions | `ActionRequestPayload` has no context revision; broker does not send its snapshot revision. Missing revision bypasses website stale checks. Future revisions are also accepted | agent `broker.py`, `contract/models.py:191`; website `_is_stale` |
| Context transport | `foodease.context`, RPC adapter and cached snapshots exist | Adapter accepts out-of-order context into cache; initial publication may be missed; getter returns cache without a freshness barrier. Worker does not subscribe context into greeting/conversation state | agent `adapters/livekit_rpc.py`, `worker.py`, `agent.py` |
| Live voice worker | Deepgram, Gemini, Cartesia, LiveKit session, interruptible greeting, committed-turn helper | Ten registered tools, not all thirteen: checkout summary, checkout submission and undo are absent. Tested ConversationEngine confirmation/reference/recovery behavior is not wired into this path | agent `worker.py`, `agent.py`, `session.py` |
| Facts delivered to LLM | Broker generates a short tool guidance string | For several reads/searches the live tool returns generic success rather than structured verified details. The LLM does not receive sufficient authoritative item/result data through that return path | agent `_execute_op`, broker `_speak_guidance` |
| Control/idle behavior | Control matcher, idle scheduler, preferences, interruption and reconnect helpers | Live controls mostly update flags then suppress the LLM. Repeat/back/undo/manual/end do not execute their full intended runtime behavior. No live idle polling loop or comprehensive lifecycle callbacks are wired | agent `agent.py`, `idle.py`, `controls.py` |
| Transcript/status | EventBus, InboundHandler, native aligned-transcript configuration, inspector harness | Worker does not connect EventBus/status/transcript mirroring to the room. Existing harness appends partials and finals; it is not a finished transcript implementation | agent `events.py`, `inbound.py`, `worker.py`, `harness/app.js` |
| Confirmation | Text engine has code confirmation machine; website issues a summary token and invalidates it on cart mutation | Live voice lacks the same gate. Website accepts a missing token after a summary exists. Text engine marks a summary delivered before actual speech playback; “yes…” prefix matching is too broad for corrections | agent `confirmation.py`, `engine.py`; website `_submit_demo_order` |
| In-flight actions | Idempotency cache, no-blind-retry policy, timeout status and reconciliation helper | Live agent registers an action as pending only after broker completion; cancellation during RPC needs explicit ownership. No session-scoped operation-status lookup/receipt retention for reconciliation | agent `_execute_op`, `interruption.py`; website `action_log` |
| Session service | Short-lived role tokens, CORS/rate limit, consent-gated dispatch/start/end | Start is not idempotent, accepts caller room/identity, creates new session IDs; no shopping-session binding. End soft-fails deletion then forgets registry while reporting ended | `orchestration/src/foodease_session/{app,models,assist,mint}.py` |
| Participant association | App role attribute; three-seat topology documented | Agent resolver falls back to a non-agent participant. Sender identity/session is not enforced on incoming context/control packets. Dual browser seats and single audio output need explicit handling | agent `adapters/livekit_room.py`; orchestration `docs/TOPOLOGY.md` |
| Launch/evidence | Helpers, MockApp conformance tests, IR-01–05 integration scenarios | Helpers still launch MockApp/harness rather than website; both harness and website use port 8080. Integration scenarios and conformance fixture instantiate MockAdapter rather than the actual website | orchestration `tools/`; agent `integration/scenarios.py`, `tests/adapter_conformance/` |

Additional domain cases to cover during integration: malformed JSON/argument types currently lack consistent typed rejection; search does not always clear stale item focus; `back` simply goes home; filter/context do not fully describe category/budget; rapid requests and action-cache conflicts need serialized semantics; several browser handlers can show success text after a rejected operation. These are functional correctness work, not visual polish.

### Verification performed for this analysis

- Selected offline agent tests: **79 passed** (`test_contract_v1`, `test_mock_cart`, `test_phase4_engine`, `test_phase5_voice`, `test_phase7`, `test_livekit_room`). These cover components and simulated room transport.
- Orchestration tests: **19 passed**, one Starlette/httpx deprecation warning.
- Subsequent Python launches failed with `No Python at ...\uv\python\cpython-3.12-windows-x86_64-none\python.exe` from both existing virtual environments. Their `pyvenv.cfg` references that path. Initial pass output is retained as observed; environment repeatability is not established.
- Website has no local `.venv` in this checkout. Its tests and the proposed cross-package compatibility probe were **not run successfully** during this analysis. The mismatch findings above are source-derived.
- No browser, microphone, provider, LiveKit Cloud or audible end-to-end test was run. Existing live-audio/latency/usability waivers remain limitations, not passes.

## 4. Target architecture and runtime ownership

```text
Browser website
  existing controls + semantic renderer + assistance controller
  user seat: microphone, typed input, ONE agent-audio playback path
  app seat: RPC handler + authoritative context publisher; no microphone
       |                          |
       | HTTP operations          | LiveKit RPC / context
       v                          v
Website application          LiveKit room <--> FoodEase voice worker
  per-shopping-session          ^                conversation + policy
  catalog/cart/order truth      |                speech + tool requests
       |                        |
       +--- session association +--- orchestration service
                                     tokens, readiness, dispatch, teardown
```

- Preserve the existing three logical seats. For the first implementation, the same browser hosts separate app/user LiveKit connections. Only the user seat publishes microphone audio and plays agent audio; the app seat is data-only at application level.
- Use the website backend as the shopping authority. It validates every manual and agent action through one operation service; no business rules in the orchestration package.
- Prefer a same-origin website bridge/proxy to the session service. Keep LiveKit/provider secrets server-side and session-service mutation endpoints private to the demo boundary. Do not add a full login product.
- Recommended initial session behavior: isolated shopping session per tab, retained across reload for the documented demo lifetime; mode changes reuse it. Define owner authorization and attachment explicitly, not a user-editable global ID. New tabs are independent unless a deliberate shared-session feature is introduced later.
- Associate shopping session, assistance generation, room, participant identities and dispatch server-side. A new voice attempt must not create a new cart.
- A per-session action processor serializes mutations and commits state/revision/result together. Cache identity includes session, action ID and canonical request fingerprint.
- Initial/reconnect snapshots are requested through a handshake, not assumed to arrive through a one-time broadcast. Accept context only for the bound session/app sender and monotonic revision.
- Keep all thirteen shopping operations. Lifecycle/control and action-status lookup are transport concerns, not arbitrary new LLM shopping tools.
- Treat the current frozen v1 as the baseline. Any breaking revision/token/shape changes require one explicit versioned contract update and regenerated handoff schemas; do not silently rewrite the frozen copy.

## 5. Phased implementation

Each phase produces a short report under `orchestration/evidence/final/phase-NN/` with commands, results, failures/skips and redacted traces. Implement only one phase at a time. Do not label a mocked test as a live pass.

### Phase 0 — Reproducible baseline and integration inventory

Goal: make checks repeatable before interpreting failures as application defects.

Work:

- Repair/recreate package environments using an available supported Python; preserve source and secrets. Install the website development environment and establish dependency locks where needed.
- Inventory actual installed LiveKit Python/JS versions and verify relevant APIs against those versions. Reuse architecture, not unverified harness snippets.
- Capture baseline agent/orchestration/website tests, lint, agent typecheck and JavaScript syntax results. Record pre-existing failures separately.
- Add a requirements map covering WEB-01–22, VA-01–17, W01–22, T01–20 and this plan's final acceptance scenarios.

Verification / gate:

- Fresh shells can invoke all three interpreters; documented setup and checks repeat successfully.
- Website boots independently with no provider connection and can complete a manual demo order.
- No paid/live provider probe is included in this baseline.

### Phase 1 — Freeze one executable integration contract

Depends on Phase 0.

Work:

- Publish a field-by-field request/result/context matrix using real website payloads, not illustrative mock records.
- Resolve `lines` versus `cart`, extra `line_total`, tags/category/vegetarian mapping, complete filter state, result details, route names and demo receipt shape. Prefer one canonical representation with explicit adapters only where needed for compatibility.
- Carry session, turn, action, event and expected context revision end to end. Specify exact equality/stale policy, read exceptions and result/update ordering.
- Specify all thirteen tool inputs, status/error enums, quantity/search limits, bounded results, payload byte limits for the installed transport and idempotency conflict behavior.
- Specify typed/control direction, event topic, sender authorization, transcript utterance identity and phase semantics. Existing `foodease.text_input` app RPC does not currently deliver input to the worker; choose and implement one worker-facing path later.
- Make current-summary confirmation enforceable in the application, including token/session/cart-version binding. Document and version the change from optional-token v1 where required.
- Define a session-scoped, read-only action-result lookup for timeout reconciliation, available to the broker without replaying a mutation. Include retention/expired/unknown behavior.

Verification / gate:

- Contract fixtures from the real domain validate empty and nonempty carts, every operation and every result status against the same generated schemas used by the agent.
- Add negative fixtures for forbidden fields, mismatched action/session IDs, malformed arguments and unsupported versions.
- A cross-package test demonstrates the current mismatch failures, then passes with the agreed contract. Regeneration detects drift between canonical and handoff copies.

### Phase 2 — Session-scoped application authority and action safety

Depends on Phase 1.

Work:

- Replace the singleton shopping domain with bounded per-session state and explicit server-side ownership/attachment checks. Preserve it across assistance stop/restart and page reload within the documented lifetime.
- Use the same validated operation handler for manual HTTP and agent RPC forwarding. Validate request bodies and types before entering domain code; never trust client prices.
- Serialize actions per session; commit state, revision and result atomically. Reject reuse of an action ID with different arguments instead of silently returning an unrelated result.
- Enforce expected revision for consequential operations and reject future as well as stale versions; define navigation versus cart revisions so harmless orientation changes do not silently corrupt confirmation.
- Bind a one-use confirmation token to a specific cart/summary and session. Invalidate it on material cart changes; keep an authoritative demo receipt after cart clearing.
- Implement status lookup and bounded action-result retention. Explicitly define process-restart/session-expiry behavior; do not promise durable outcomes from in-memory state.
- Fix only integration-relevant domain inconsistencies: stale selection after search/filter/navigation, truthful back navigation, filters in context and supported recovery states.

Verification / gate:

- Actual website API tests cover all thirteen operations, invalid IDs/types, unavailable items, totals and fee calculation.
- Two independent sessions never share cart, context, token, receipt or action cache.
- Concurrent manual/agent requests have deterministic ordering; duplicate requests execute once; conflicting duplicate IDs reject.
- Checkout without a current token, with an expired/cross-session token, or after a cart edit is refused. One confirmed submission creates one receipt.
- Read-only result lookup identifies committed, rejected, pending/unknown and expired actions without changing state.

### Phase 3 — Assistance lifecycle, role binding and readiness

Depends on Phases 1–2.

Work:

- Bind existing session/token/assist endpoints to the website shopping session; keep one active assistance generation and one intended worker per session.
- Make repeated start requests idempotent and define cancellation when manual/end is selected while permission, join or dispatch is pending.
- Separate preparation from activation: acquire permitted media and connect/register the app seat, establish context/readiness, then allow the dispatched worker to greet. Use a bounded handshake so a failed start cannot leave an orphan worker or microphone.
- Restrict app selection to the authorized app identity/role; verify incoming context/control/text sender and session. Remove the arbitrary non-agent destination fallback in the integrated mode.
- Define idle/absolute expiry, token refresh/rejoin and disconnect cleanup. Server dispatch cleanup and client microphone/audio cleanup are independently observable.
- Distinguish successful dispatch deletion from transient failure. Retry/reconcile teardown safely instead of forgetting a failed deletion and claiming completion.
- Integrated launch must explicitly select live website transport and fail clearly if the app seat is absent; never silently fall back to MockAdapter.

Verification / gate:

- Fake dispatch/room tests cover double start/end, cancellation at every startup boundary, permission rejection, missing app seat, worker unavailability, expiry and failed cleanup.
- A session cannot attach to or end another session's room through supplied identifiers.
- Room startup produces the intended app/user/agent identities with one dispatch; readiness timeout leaves manual ordering intact.
- No greeting before consent/playback readiness; no active microphone after local end, even if server cleanup needs reconciliation.

### Phase 4 — Complete the live worker's conversation/action runtime

Depends on Phases 1–3.

Work:

- Keep LiveKit's streaming speech/LLM path. Extract/reuse the tested deterministic policy components as a shared runtime used by the live agent and text tests. Do not replace natural conversation with RulePlanner/DialogueSuitePlanner or run two competing conversation engines.
- Register all thirteen tools, normalize filters correctly and return bounded structured verified facts to the model. Every tool passes through the same broker, revision and confirmation checks.
- Subscribe fresh context into live orientation/reference state, greeting readiness and preferences. Inject current bounded context into the live reasoning path; a Python cache alone is insufficient.
- Implement manual/voice/typing intent handling outside the LLM where clear; enforce tool authorization by active mode. Implement stop, pause, resume, repeat, back, undo and supported speed/volume behavior end to end. Unavailable controls get a truthful response.
- Wire commit/uncommit/discard lifecycle with turn identities. Keep preemptive generation off until discarded-turn tests prove no effects.
- Register pending mutations before submission and retain task/result ownership through speech cancellation, disconnect and mode changes. Never translate stopping speech into a guessed rollback.
- Connect checkout confirmation to the exact summary, cart version and actually delivered speech/text. Interrupted or unheard confirmation prompts cannot authorize submission. Handle “yes, but change it…” as a correction, not consent.
- Wire finite idle scheduling to real speech, manual actions, typing, pause tips and disconnect events. No tips in manual mode, during user speech, or before mode selection.

Verification / gate:

- Worker-level tests invoke the actual live agent tools and lifecycle callbacks with fake providers and the real website domain adapter, not just detached helper objects.
- All thirteen operations are reachable. Filter/details/search results contain actual factual data; nonempty cart speech reports the website total and quantities.
- Stop/manual/repeat/back/undo are tested with a fake session/audio handle and recorded action effects.
- Discarded/stale/late turns cannot submit mutations; checkout summary interruption and a later casual “yes” submit nothing.
- Manual context changes invalidate stale references and prevent obsolete speech from continuing as current guidance.

### Phase 5 — Browser bridge and synchronized application rendering

Depends on Phases 1–4; this is the first complete typed integration checkpoint.

Work:

- Add a small browser LiveKit bridge and assistance controller, with a pinned dependency and reproducible delivery. Reuse the existing panel and controls.
- Connect app and user seats with the bound credentials. Register `foodease.action`, forward to the existing authoritative application service and return a correlated result.
- Publish fresh context after manual and agent changes; request/publish a snapshot on attach/reconnect. Sequence action completion, rendering and context publication explicitly; deduplicate loops.
- Route keyboard/click, remote agent and typed requests through shared operations and a single renderer. Reflect authoritative filters, bounded results, selection, route/dialog, cart, checkout and receipt.
- Reconcile existing display-only filtering with backend results, including budget boundary, availability, search clearing and result counts. Include semantic anchor/dialog navigation in context updates.
- Implement worker-facing typed/control transport from Phase 1. Handle native agent audio/status/transcripts and chosen envelope mirroring once, avoiding duplicate streams/audio.
- Replace interim transcript text by utterance/turn identity; mark interrupted assistant output from actual delivery events. Keep focus stable during streaming text.
- Prevent success announcements after rejected/unknown actions. Preserve useful existing rendering, CSS and animations as they are.

Verification / gate:

- Browser tests with fake LiveKit and the actual website API prove that an injected agent action visibly changes the menu/item/cart/checkout, and that a manual edit changes worker-visible context.
- A typed natural-language order works through the actual worker interpretation path without a microphone; a local fake still proves wiring before paid/live testing.
- Out-of-order context/results cannot overwrite a newer view. Browser matches authoritative visible IDs, selection and totals after each action.
- No transcript duplication, duplicate audio playback or focus jumps on partial updates. Browser API failures show accurate recoverable states.

### Phase 6 — Opening mode choice and complete mode continuity

Depends on Phases 3–5.

Work:

- Implement the opening flow in section 2 using existing surfaces and minimum functional controls.
- Add a small explicit state machine: manual, awaiting spoken-choice consent, connecting, choosing mode, voice active, typed active, paused, reconnecting and ended/error.
- Recognize clear natural choices such as “manual please”, “I'll order myself”, “use voice”, “talk me through it”; handle ambiguous choices conservatively.
- While choosing a mode, allow only mode/help/exit behavior. Do not activate shopping mutations because an ambiguous onboarding answer resembles an order.
- Manual choice cancels queued speech/tips, stops/unpublishes microphone tracks, disables voice tool execution and ends dispatch/room resources. Pending committed shopping actions remain tracked to their true outcome.
- Restore the same route/cart on resumption and use a short welcome-back message. Typed mode has no microphone requirement; audio output is an explicit preference.

Verification / gate:

- Automated flow matrix covers fresh visitor, returning opted-in visitor, autoplay blocked, permission allowed/denied/pending, no microphone, silence, ambiguous choice, direct manual and direct voice.
- Test manual choice during greeting, mode-choice prompt, connection setup and an in-flight cart operation. Confirm silence, no new action and preserved verified cart.
- Real browser tests confirm microphone tracks actually end and audio playback stops; a status label alone cannot pass this gate.
- Voice → manual → voice and voice → typing → manual preserve the shopping session and do not duplicate dispatch/greeting/orders.

### Phase 7 — Conversational quality and page-grounded assistance

Depends on Phases 4–6.

Work:

- Give the live assistant concise semantic page context: location, selected item, available actions, current filters/results, factual details and cart. Support “read this page”, “where am I?”, “what can I do here?”, “open the second one” and “press add to cart” through that model.
- Support natural multi-turn shopping: preference/budget refinement, grounded recommendations/comparisons, short lists with next/previous, corrections and combined requests executed step by step against fresh state.
- Maintain the identity/order of items actually presented to the user. Clarify after a manual page change instead of guessing “that one”.
- Reuse speech shaping/pronunciation where compatible with streaming, preserving numbers and caption parity. Avoid buffering entire replies just for polish.
- Improve actual prompts/tool descriptions only after factual and policy wiring works. Keep replies brief by default, one useful follow-up, no forced upselling, fake fillers, invented ingredients or a claim to be human.
- Wire speech preferences to real playback/TTS support; never acknowledge an adjustment that did not happen. English/PKR is the core demo; bilingual behavior requires its own later STT/TTS evaluation.

Verification / gate:

- Extend DS-01–25 with onboarding and actual website cases; run deterministic safety tests after every prompt change.
- Run a separately labeled real-model campaign with varied paraphrases and unseen food/quantity/budget combinations. Scripted planner results do not count as model/conversation evidence.
- Record tool accuracy, clarification on unambiguous requests, false success/duplicates and human ratings for naturalness, relevance, brevity and comfort.
- Suggested quality gate: at least 40 varied real-model turns; at least 3 listeners rate sampled live replies, median at least 4/5 for naturalness/helpfulness, no critical factual or consent error. Report sample size and failures; this is a project gate, not a vendor claim.
- Page-reading and button-command tests assert both spoken answer/action and resulting visible application state. Unsupported controls are explained honestly.

### Phase 8 — Interruption, outage and uncertain-outcome recovery

Depends on Phases 4–7.

Work:

- Exercise real provider errors and bridge faults through the live runtime, not only global synthetic fault flags. Preserve typed/manual mode where the remaining dependencies allow it; an LLM outage may leave manual as the only working mode.
- Reconnect using a fresh session-bound snapshot; clear stale references/confirmation, resume only if current user mode permits and never replay unknown mutations.
- Reconcile timed-out actions by action ID/receipt. Distinguish timeout before execution, committed action with lost response and still unknown/expired outcome.
- Handle app-seat loss, background tab, token expiry, duplicate connections, browser reload and shutdown. Reattach microphone only with the correct consent/mode; prevent old room events from reviving ended assistance.
- Measure actual barge-in and false interruption behavior; reconcile already committed cart/checkout effects after speech stops.

Verification / gate:

- Failure matrix covers STT, LLM, TTS, room, HTTP, RPC timeout, dispatch, app participant loss and expired credentials.
- Response-loss tests prove an already committed add/order happens once and is recovered by identity. An unknown outcome is never reported as failed/successful without evidence.
- A manual edit during delayed speech/result remains authoritative. Ending assistance cannot produce late unsolicited speech or a second mutation.
- Test reload within supported retention and service restart outside it; accurately report unrecoverable state without inventing a receipt or replaying checkout.

### Phase 9 — Joint live acceptance and reproducible delivery

Depends on all previous phases.

Work:

- Update bring-up helpers to launch website, session service and live worker. Remove MockApp/harness from the final path and resolve port conflicts. Use valid PowerShell commands and documented required flags.
- Document local launch and, if a shareable demo is required, HTTPS origin, reverse proxy, secret placement, allowed origins and provider connectivity. Deploying a public demo is a separate explicit action, not implied by this planning task.
- Keep safe demo defaults, bounded session/result retention, minimal redacted logs and no recording by default. Logs correlate session/turn/action/dispatch and label synthetic versus live evidence.
- Run joint W/T acceptance, human keyboard/screen-reader mode switching, live conversational checks and measured audio performance. Retire earlier waivers only when new evidence exists.
- Deliver one runbook, updated ownership/contract references, support matrix and known limitations.

Verification / final gate:

- Clean environment launch following only the runbook opens the actual website and establishes the three intended seats.
- Pass the final scenario matrix below in the actual browser/LiveKit/website path with no MockAdapter.
- Measure at least 30 ordinary live turns and 10 genuine interruptions. Report warm/cold p50/p95 separately; don't substitute server generation time for audible playback.
- Use SPEC §7 targets: warm greeting p50 ≤0.8s/p95 ≤1.5s; cold join-to-audio p50 ≤2s/p95 ≤4s; response TTFA p50 ≤1.2s/p95 ≤2.5s; barge-in stop p95 ≤350ms; scripted-turn completion ≥95%. Capture browser/device/network/account conditions and permission delays separately. A missed target remains open or explicitly accepted with evidence, not relabeled passed.
- At minimum test current Chrome/Edge desktop and one phone browser for permission/playback/ordering. Do not claim broader device support than tested.
- Human keyboard and screen-reader walkthrough confirms mode choice, focus after voice navigation, cart updates, captions and checkout without competing announcement spam.

## 6. Final acceptance scenario matrix

All scenarios run against the actual website authority; final audio claims additionally require real browser/provider playback.

| ID | Scenario | Required observable outcome |
|---|---|---|
| O-01 | Open website; choose manual directly | Manual order works; no mic capture, dispatch or unsolicited audio |
| O-02 | Enable spoken welcome; say nothing initially | One prompt asking voice/manual after readiness, without needing “hello” |
| O-03 | Say “manual please” / “I'll do it myself” | Playback/tips stop, tracks end, dispatch cleanup reconciles, shopping remains intact |
| O-04 | Say “voice”; ask for spicy food under 1,000 | Correct real filters, matching visible items and grounded concise reply |
| O-05 | “Where am I?” / “Read this page” | Current route/selection/results/actions, no fabricated page or exhaustive irrelevant dump |
| O-06 | “Open the second one”; “press add to cart” | Exact presented item opens/adds through semantic operations; verified total spoken |
| O-07 | “Add two”; interrupt with “actually make it one” | Final quantity one with matching UI and no duplicated add |
| O-08 | Change page/filter/item manually during reply | Obsolete guidance stops; current context wins; stale references clarify |
| O-09 | Ask details/recommendations/comparison with unknown ingredients | Uses verified facts and states missing information plainly |
| O-10 | “Repeat”, “slower”, “back”, “undo”, “stop” | Each supported control performs its real behavior; no unrelated mutation |
| O-11 | Request checkout; silence, casual yes, correction or interrupted summary | No submission without explicit current-summary authorization |
| O-12 | Confirm fully delivered current summary | Exactly one demo receipt, actual total and truthful simulated-order acknowledgment |
| O-13 | Edit cart after summary or use token from another session | Confirmation invalidated/refused; fresh review required |
| O-14 | Duplicate action/start request; simultaneous manual/voice edits | One effect/dispatch; deterministic result; no overwritten newer state |
| O-15 | Commit order then drop response | Retrieve original outcome by ID; no new order/retry or invented failure |
| O-16 | Mic denied, autoplay blocked, provider unavailable | Accurate state, actionable recovery, usable existing manual cart |
| O-17 | Voice → typed → manual → voice | Same shopping session; correct microphone/audio state; brief resume |
| O-18 | Disconnect/reconnect/reload/end during work | Latest supported state restored, no stale replay or late unsolicited speech |
| O-19 | Two shoppers / tabs with distinct sessions | No shared cart, context, transcript, token or receipt leakage |
| O-20 | Natural varied phrasing, noise and hesitations | Comfortable dialogue; uncertainty clarified; measured failures retained |
| O-21 | Keyboard/screen reader with assistant active | Core order and mode exit accessible; no focus trap or announcement flood |

## 7. Verification commands and evidence rules

After Phase 0 repairs/setup, the baseline commands are:

```powershell
# From voice-agent/
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pyright

# From orchestration/
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check src tests tools

# From website/
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check src tests
node --check static/js/app.js
```

Add a repeatable browser/integration test command and worker-real-domain conformance command as part of implementation. Existing `tools/run_integration.py` is MockAdapter-only and must not be reused unchanged as the final acceptance result. Store new reports separately from the existing handover evidence.

Each report states: baseline commit and changes, package versions, exact commands, automated results, browser/device, real versus simulated transport/provider, failures/skips, action/context traces and observed limitations. Never include tokens, secret values or unsolicited recordings.

Maintain two explicit outcomes:

- **Implementation gate:** contract, domain, session, worker, browser and fault tests pass with the actual website domain. This establishes implemented behavior under the tested conditions.
- **Live acceptance gate:** real browser microphone/audio, LiveKit/provider behavior, conversational quality, accessibility and performance scenarios pass with recorded observations. Offline tests do not close this gate.

## 8. Completion definition

The final orchestration is complete when the actual website supports the permission-aware opening voice/manual choice, conversational page-grounded ordering, visible semantic actions, one authoritative cart, safe demo checkout, reliable mode switching and honest outage/timeout recovery; all applicable phase gates and final scenarios have evidence.

Visual polish and animation work remain Zainab's separate track. The central integration cannot be declared complete merely because tokens mint, participants join, or tests against MockAdapter pass.
