# Final orchestration requirements map

Baseline: `23e2b64`; Phase 0 only. Phase numbers refer to the final orchestration
plan, not the earlier independent agent/website plans. A mapping is traceability,
not a completion claim. Existing test names identify component evidence; final
browser/live evidence remains pending unless explicitly recorded in report.md.

## Website requirements

| ID | Requirement | Existing source / evidence | Implementation phase | Final verification |
|---|---|---|---|---|
| WEB-01 | Optional non-assumptive mode choice | Website assistance controls; mock-only start | 3, 6 | O-01–04, O-16 |
| WEB-02 | Mode continuity | Domain cart; local assistance flags | 2, 5, 6 | O-17–18 |
| WEB-03 | Orientation and discoverability | Template headings, app context | 4, 5, 7 | O-05, O-21 |
| WEB-04 | Manual shopping | Website domain and test_domain.py | 0 baseline; 2, 5 fixes | Manual browser order; O-06–07 |
| WEB-05 | Interaction feedback and polish | Existing controls/status/rendering | 5 functional feedback; visual polish separate | O-06, O-16, O-21 |
| WEB-06 | Accessibility foundation | Template labels/live regions; CSS focus | 5, 6, 9 | Human keyboard/screen-reader O-21 |
| WEB-07 | Orientation and error prevention | Checkout dialog and domain token | 2, 4, 5 | O-05, O-11–13 |
| WEB-08 | HCI design evidence | Website docs/PHASE_14_HANDOVER_DOCUMENTATION.md | Zainab design track; 9 integration evidence | Human rationale and mode-flow review |
| WEB-09 | Authoritative data | catalog.py, domain.py, catalog seed | 1, 2 | O-04, O-14, O-19 |
| WEB-10 | Shared operation layer | /api/app/action and domain dispatcher | 1, 2, 5 | All 13 operations against real domain |
| WEB-11 | Shared event envelope | Agent contract/models.py; website flattened HTTP input | 1, 3, 5 | Schema/correlation/session-negative tests |
| WEB-12 | Incoming agent events | Local mock panel | 4, 5 | O-06, O-08, O-16 |
| WEB-13 | Outgoing app events | /api/app/context; refreshContext | 1, 4, 5 | O-08, O-17–18 |
| WEB-14 | 13 semantic actions | domain.ALL_OPERATIONS; agent tools incomplete | 1, 2, 4, 5 | Operation coverage and visible effects |
| WEB-15 | Results/confirmation/safety | Domain action log, revision/token helpers | 1, 2, 4, 8 | O-11–15 |
| WEB-16 | Example exchange | Both specs and contract examples | 1 | Real request/result/context schema fixture |
| WEB-17 | Assistance panel | Mock transcript, typed/control elements | 4, 5, 6 | O-03, O-16–17, O-21 |
| WEB-18 | Synchronized navigation | Context route/focus; separate JS view state | 2, 4, 5 | O-05–08, O-21 |
| WEB-19 | Connection and consent | Existing session API; no browser bridge | 3, 5, 6 | O-01–03, O-16–18 |
| WEB-20 | Persistence choice | In-memory domain; no database needed | 2, 8, 9 | Session/reload/restart retention tests |
| WEB-21 | Privacy and truthful checkout | Demo receipt; server pricing | 2, 3, 4, 8 | O-11–15, O-19 |
| WEB-22 | Reliability and responsive access | Existing website tests; human checks outstanding | 5, 8, 9 | O-14–21; human device/access checks |

## Voice requirements

| ID | Requirement | Existing source / evidence | Implementation phase | Final verification |
|---|---|---|---|---|
| VA-01 | Activation and proactive welcome | worker.py, greeting.py, test_phase5_voice.py | 3, 4, 6 | O-01–04; audible welcome after readiness |
| VA-02 | Limited contextual silence prompts | idle.py unit tests; no live polling loop | 4, 6, 7 | Silence/typing/manual cancels; bounded tips |
| VA-03 | Barge-in and turn taking | session.py, interruption.py component tests | 4, 8, 9 | O-07, O-11, O-18, O-20; live stop latency |
| VA-04 | Natural speech/dialogue | Policy v2, speech_text, deterministic dialogue suite | 4, 7, 9 | Real-model campaign and human listening |
| VA-05 | Context and orientation | reference.py, engine.py; live subscription gap | 1, 4, 5, 7 | O-05, O-08–09 |
| VA-06 | Grounded safe domain actions | Broker, text engine, partial live tools | 1, 2, 4, 7 | O-04–15; all 13 tools |
| VA-07 | Exposed lifecycle states | product_state.py and EventBus components | 3, 4, 5, 6 | Actual status transition and error tests |
| VA-08 | Speech/text parity | Aligned transcript option, shaping; mock panel | 1, 4, 5 | Partial replacement, interrupted captions, O-17 |
| VA-09 | Context subscription | LiveKitRpcAdapter cache; ContextSnapshot | 1, 3, 4, 5 | Monotonic/session/sender and fresh snapshot tests |
| VA-10 | Traceable deduplicated envelope | Contract schemas, EventBus | 1, 2, 3, 5 | Schema, correlation, duplicate/conflict tests |
| VA-11 | Agent events | events.py; worker mirroring not wired | 1, 4, 5 | Browser consumes actual worker events |
| VA-12 | App events | inbound.py; detached adapter callbacks | 1, 4, 5 | Real context/control/text delivery |
| VA-13 | Fixed semantic vocabulary | enums.py, models.py, partial agent tool set | 1, 2, 4 | 13 tool allowlist and invalid operation rejection |
| VA-14 | Confirmation/interruption boundary | confirmation.py, reconnect.py; text tests | 1, 2, 4, 8 | O-11–15, O-18 |
| VA-15 | Optional accessible assistance | Mock mode switches; no live mic teardown | 3, 5, 6, 9 | O-01, O-03, O-16–17, O-21 |
| VA-16 | Truth/privacy/security | Server config, allowlist, no-record default | 2, 3, 4, 9 | No secrets/recording; injection/session isolation |
| VA-17 | Failure and recovery | recovery.py, fault tests; live wiring gap | 3, 4, 8 | O-15–18, O-20 |

## Independent website acceptance

| ID | Scenario | Existing source / evidence | Implementation phase | Final verification |
|---|---|---|---|---|
| W01 | Independent manual website | test_app.py; Phase 0 browser check | 0, 9 | No worker/session service; complete demo order |
| W02 | Manual mode without mic/autoplay | Mock start is opt-in; Phase 0 browser check | 6, 9 | O-01 |
| W03 | Keyboard-only order | Website record requires human observation | 9 | O-21; human recording/notes |
| W04 | Vegetarian/budget filters and clear | test_domain.py; JS filter divergence | 1, 2, 5 | O-04; UI IDs/count equal context |
| W05 | Item details and quantity two | Domain add tests; browser item dialog | 0 baseline; 2, 5 | Actual item/quantity/price visible |
| W06 | Reduce/remove cart line | Domain set/remove; browser handlers | 0 baseline; 2, 5 | Verified quantity/total and truthful feedback |
| W07 | Invalid/empty/unavailable refusal | Domain guards and tests | 2, 5 | Structured rejection; no false success |
| W08 | Confirm one demo order | test_domain.py; Phase 0 browser check | 0 baseline; 2, 4, 5 | O-12–13 |
| W09 | Manual changes update context | Domain revision; no LiveKit publishing yet | 4, 5 | O-08 |
| W10 | Inject filter/select | Mock harness; real website operation endpoint | 1, 5 | Visible menu/selection plus correlated result |
| W11 | Add then absolute quantity one | test_domain.py | 1, 2, 4, 5 | O-07 |
| W12 | Duplicate action id | test_domain.py; action_log | 2, 8 | O-14–15 |
| W13 | Stale revision/invalid item | test_domain.py; wire revision missing | 1, 2, 5 | Stale/future/invalid request tests |
| W14 | Current-summary confirmation | Domain invalidation; token optional today | 1, 2, 4 | O-11–13 |
| W15 | Unknown submit outcome | Website acceptance record partial | 1, 2, 8 | O-15 |
| W16 | Lifecycle status display | Local setAgentStatus | 3, 4, 5, 6 | Actual room/provider lifecycle |
| W17 | Transcript replacement/interruption | Website acceptance record partial | 1, 4, 5, 8 | Per-turn replacement and heard text |
| W18 | Typed request envelope | Local transcript trace only | 1, 4, 5 | O-17; worker interprets text without mic |
| W19 | Manual edit while agent responds | Shared domain; no live synchronization | 4, 5, 8 | O-08 |
| W20 | Disconnect/mic denied fallback | Mock controls; no real mic | 3, 6, 8 | O-16–18 |
| W21 | Manual/assisted/manual continuity | Local assistance flags preserve domain | 2, 3, 6 | O-17 |
| W22 | Zoom/screen reader/status | Website record: manual observation pending | 5, 9 | O-21; human test, not inferred conformance |

## Independent agent acceptance

Existing T evidence is primarily MockAdapter/text-component coverage. Historical
live-audio waivers in agent decisions.md remain in effect; this map does not turn
them into passes.

| ID | Scenario | Existing source / evidence | Implementation phase | Final verification |
|---|---|---|---|---|
| T01 | Welcome without user speech | test_phase5_voice.py; greeting helper | 3, 4, 6 | O-02; actual audible greeting |
| T02 | Silence then finite help | Idle fake-clock tests | 4, 6 | Bounded live prompts; then quiet |
| T03 | Interrupt greeting with burgers | Interruption helper; live evidence pending | 4, 8, 9 | Greeting stops; visible category changes |
| T04 | Natural hesitations | Pending human in historical acceptance | 7, 9 | Real mic pauses/no premature turn |
| T05 | Vegetarian under eight hundred | Scripted planner and MockAdapter | 1, 4, 5, 7 | O-04 with natural speech |
| T06 | Second item reference | reference.py and engine tests | 4, 5, 7 | O-06; correct presented item |
| T07 | Add two then one | Mock cart/engine tests | 2, 4, 5, 8 | O-07 |
| T08 | Failed add is not success | Broker/engine negative tests | 4, 5, 8 | Actual worker rejection and visible state |
| T09 | Orientation after manual navigation | Mock GUI context tests | 4, 5, 7 | O-05, O-08 |
| T10 | Stop/repeat/back/slower | Match/control/helper tests | 4, 7 | O-10; actual playback/control effect |
| T11 | Silence does not confirm | Text confirmation tests | 2, 4 | O-11 |
| T12 | Explicit current checkout | Text engine and MockAdapter | 2, 4, 5 | O-12; one real-domain demo receipt |
| T13 | Cart edit invalidates consent | Confirmation helper and IR-05 | 2, 4, 5, 8 | O-13 |
| T14 | Delayed/unknown result | Mock scenarios and reconnect helper | 1, 2, 4, 8 | O-15 |
| T15 | Denied/muted microphone | Fault flag tests; no real browser mic proof | 3, 5, 6 | O-16–17 |
| T16 | Typed conversational request | Text engine tested; browser forwarding absent | 4, 5 | O-17; actual worker interpretation |
| T17 | Provider outage | Synthetic recovery tests | 4, 8 | O-16; real runtime failure injection |
| T18 | Regional speech/noisy mic | Pending human in historical acceptance | 7, 9 | O-20; retain recognition failures |
| T19 | Browse independently | Text control/preferences tests | 3, 4, 6 | O-03; mic and tips actually stop |
| T20 | Interrupt in-flight mutation | Interruption helper; pending registration gap | 2, 4, 8 | O-07, O-15, O-18 |

## Final joint acceptance

All O scenarios are pending joint integration/live verification in Phase 0. A
manual-only baseline is evidence for W01/W08, not a pass for a voice scenario.

| ID | Scenario | Existing source / evidence | Implementation phase | Final verification |
|---|---|---|---|---|
| O-01 | Direct manual choice | Manual website baseline | 6, 9 | No capture/dispatch/audio; order completes |
| O-02 | Spoken mode prompt | Existing welcome differs | 3, 4, 6, 9 | Audible once after readiness |
| O-03 | Spoken manual exit | Text control helper only | 3, 4, 6, 9 | Audio/tips stop; mic ends; cart preserved |
| O-04 | Voice spicy/budget request | Mock filtering | 1, 4, 5, 7, 9 | Real filtered UI and grounded spoken matches |
| O-05 | Read page/orientation | Context and text planner | 4, 5, 7, 9 | Latest semantic location/actions |
| O-06 | Open second/add by voice | Reference helper | 2, 4, 5, 7, 9 | Presented ID opens/adds visibly |
| O-07 | Correct quantity mid-reply | Mock cart/interruption helpers | 2, 4, 5, 8, 9 | One verified line quantity one |
| O-08 | Manual change during speech | Detached context helpers | 4, 5, 8, 9 | New state wins; obsolete guidance stops |
| O-09 | Grounded details/recommendations | Policy and scripted dialogue | 4, 7, 9 | No fabricated ingredient/price facts |
| O-10 | Universal controls | Matcher and text engine | 4, 7, 9 | Observable actual playback/app behavior |
| O-11 | No incidental checkout consent | Confirmation helper | 1, 2, 4, 9 | Interrupted/corrected/unheard summary cannot submit |
| O-12 | One confirmed demo order | Website domain; mock agent checkout | 2, 4, 5, 9 | One receipt and actual total |
| O-13 | Stale/cross-session summary | Domain token invalidation | 1, 2, 4, 9 | Reject and obtain fresh summary |
| O-14 | Duplicate/concurrent actions/start | Basic result cache and fake dispatch | 2, 3, 5, 8, 9 | Single effect/dispatch and deterministic ordering |
| O-15 | Commit then lose response | No lookup path yet | 1, 2, 4, 8, 9 | Read original outcome; never replay mutation |
| O-16 | Permission/autoplay/provider failure | Synthetic recovery helpers | 3, 5, 6, 8, 9 | Honest status and usable manual cart |
| O-17 | Voice/typed/manual continuity | Local mode flags and text engine | 2, 3, 4, 5, 6, 9 | Same session; correct tracks/audio; brief resume |
| O-18 | Disconnect/reload/end | Reconnect helper only | 2, 3, 4, 5, 8, 9 | Fresh state; no replay or unsolicited late output |
| O-19 | Session isolation | Singleton website currently | 2, 3, 8, 9 | No cross-session state/control leakage |
| O-20 | Natural speech and noise | Scripted dialogue; live waivers | 7, 8, 9 | Real model/listening/recognition evidence |
| O-21 | Accessible ordering and mode exit | Semantics present; human checks pending | 5, 6, 9 | Keyboard and screen reader walkthrough |
