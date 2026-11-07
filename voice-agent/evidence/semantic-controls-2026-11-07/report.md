# Semantic conversation controls — 2026-11-07

The active integrated assistant no longer chooses conversation effects by matching
fixed English/Urdu phrases. Ending assistance, ordering-mode choice, pause/resume,
repeat and page/list requests share the existing model interpretation path.
The model invokes `conversation_control` with a supported effect. Its bounded
effect enum is an execution API, not a vocabulary users must speak.

The previous runtime `control_name` router, `semantic_command` phrase matcher and
Urdu control phrase dictionaries were removed. Conservative reference validation
was separated into `reference_language.py`. Catalog display translations remain
presentation data. A regression extends the real test catalog with a new category
and product, then filters/adds that product without changing voice keyword rules.
The legacy standalone English harness retains its earlier matcher; it is not the
integrated website assistant's input path.

The runtime validates session/speech ownership, active committed turn, epoch,
revision, mode and duplicate execution before applying a local control. Controls
cannot place an order. Thirteen website operations and frozen wire schemas remain
unchanged, with one additional local model tool. Onboarding and pause/mute expose
only the local tool, and code rejects shopping through those states. Onboarding
context contains only language and ordering modes, avoiding unnecessary catalog
tokens. A completed control blocks later application calls in that turn.

The system policy distinguishes ending the session from declining an item/extras
or finishing one menu category, and asks for clarification when scope is unclear.
No special ending phrase is required by the code. After applying a control, the
SDK's `StopResponse` suppresses a duplicate model acknowledgment/continuation.
Onboarding clarification now asks the user's preference instead of asking them
to repeat a particular command word.

Direct UI controls remain deterministic. Speech activity/input still interrupts
old output immediately; interpreting a spoken control and completing its effect
now depends on model availability. A pending accepted cart write is reconciled,
not cancelled or repeated merely because assistance ended. Exact checkout consent
after a completely delivered current summary remains code-owned. No credentials,
voice provider choices, business data or deployment configuration were changed.

## Verification

From `voice-agent/`:

```text
.venv/Scripts/python.exe -m pytest -q --tb=short
441 passed, 1 failed in 30.07s

.venv/Scripts/python.exe -m pytest tests/test_semantic_controls.py tests/test_integrated_menu_queries.py tests/test_urdu_assistant.py -q --tb=short
55 passed in 10.90s

.venv/Scripts/python.exe -m pytest tests/test_integrated_opening.py tests/test_urdu_assistant.py -q --tb=short
39 passed in 11.01s
```

The final focused run verifies the subsequent onboarding-prompt wording change.
Changed Python files and tests pass `ruff check` and scoped `pyright` (zero errors
and warnings). `git diff --check` passes with existing LF/CRLF notices.

The only full-suite failure is the previously documented
`test_no_mock_imports_outside_adapters`, which reports the unchanged
`integration/scenarios.py` import. Early failures in the old integrated tests
expected lexical controls to execute before the model. Those tests now supply an
explicit scripted model-tool decision while preserving their state/effect checks.

The new tests cover English, Urdu and Roman Urdu input reaching the model,
negation/item-decline input causing no automatic close, stale/foreign tool
rejection, restricted onboarding/pause/mute, replay and post-control write guards,
ending while a cart write is pending, a new catalog item/category and actual SDK
invocation of the control tool. The native SDK test closes the session with one
scripted model step, no website operation and no follow-up generation.

These are offline execution/routing tests with scripted model decisions. They
do not establish real-model synonym/negation accuracy or audible stop latency.
No paid provider call, live microphone test, process restart, push or deployment
was performed. Restart the integrated worker and start a fresh session to load
this implementation. Existing provider capacity/rate limits still apply.

SDK behavior was checked against the installed 1.8.4 implementation and current
official [function tools](https://docs.livekit.io/agents/logic/tools/definition/),
[StopResponse](https://docs.livekit.io/reference/python/livekit/agents/llm/), and
[generation tool restriction](https://docs.livekit.io/reference/python/livekit/agents/voice/)
documentation before use. No dependency was added.
