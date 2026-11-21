# Zara response latency improvements — 21 November 2026

The user reports at least 2–3 seconds before a response. This is a user observation,
not an instrumented baseline. No provider, voice, speech-recognition model, VAD
silence threshold, interruption threshold or speculative execution setting changed.

## Changes

1. Common shopping/navigation tools expose an optional `finish_turn` flag. The model
   interprets whether the current call is the final step of the user's request.
   When true, code delivers the already verified, localized tool result using the
   existing speech/caption pipeline and ends the generation. This removes the second
   LLM request normally used only to reword that result. Intermediate steps retain
   the default false flag, allowing comparisons and combined requests to continue.
   Checkout/clear reviews retain their separate exact delivery/confirmation receipt;
   the fast path does not repeat their question or bypass later user confirmation.
2. After an action, the production RPC adapter can reuse the bound browser's validated
   context when its session and revision exactly match the correlated result. The
   browser already renders and publishes that state before acknowledging the action.
   If the publication is missing, older or newer, it fetches fresh state as before.
   The pre-action refresh, server stock/revision checks, turn authorization, result
   correlation, pending ownership and read-only recovery are retained.

No production phrase parser, extra cart, dependency, speculative cart write or mutation
retry was introduced. The model decides meaning and final-step status; code controls
state, validation, confirmed effects and speech delivery.

## Verification and evidence limits

`tests/test_response_latency.py` uses the actual installed LiveKit AgentSession and
function-tool execution, with a scripted streaming model and real SessionStore:

- Ordinary cart read: **2 model requests** for the continuation path, **1** for the
  final verified-response path. Both return the actual cart.
- Bound/published cart action: **2 application RPCs**, compared with the previous **3**.
  One pre-action context read and one mutation remain.
- Missing publication: **3 RPCs**, including the safe fallback read; one mutation only.
- Stock failure is explained in Urdu. The faster path does not announce an addition.
- Clear-cart review is delivered once and still waits for consent.
- Discarded turns cannot produce a late direct success reply.
- Unknown/pending outcomes are explained without success or a mutation retry.

The model must select the final-step flag to skip its continuation. Structural tests
establish the eliminated requests, not how often the production model selects that flag.
Provider TTFT, Urdu transcription, network transit and TTS still contribute latency.
These tests are not a measurement of caller-heard response time, and no subsecond or
percentage end-to-end improvement is claimed. Existing SDK stage metrics remain available.

Validation:

- Full worker regression: **530 passed, one inherited failure** in the unchanged
  `integration/scenarios.py` mock import boundary. This full run included the first
  five new latency cases; the later unknown-outcome case was verified separately.
- Focused latency cases: **6 passed** (5.56 seconds); scoped lint/type checks pass.
- Urdu desktop/mobile browser tests using the direct-response flag: **3 passed**.
- Changed production/test lint and type checks: passed with zero type errors/warnings.
- Earlier shared-cart implementation verification remains documented in
  [the Urdu integration report](../../../website/docs/ZARA_INTERACTIVE_URDU_2026-11-21.md).

## Activation/publication

The user authorized `git add .` and pushing the combined working tree to `origin main`,
including the prior Urdu website action work. `origin/main` matched local HEAD before
staging. No Cloud worker deployment is performed by the Git push itself. Restart or
redeploy the updated worker for the latency changes to affect hosted conversations;
use a matched backend/browser/worker version for the preceding clear-cart extension.
