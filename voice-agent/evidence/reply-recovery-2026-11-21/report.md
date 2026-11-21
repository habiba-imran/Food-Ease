# Production reply failure, interruption labels and latency

The requested logs-first inspection found repeated production failures in
Gemini 2.5 Flash chat setup: `thinking_level` is unsupported for that model.
Previously, a connection/greeting check did not exercise this path. The same
session logged transcription delays of approximately 0.76–0.94 s; these are
component timings, not full caller-heard response latency. No further acoustic
cause is inferred from the user's pasted transcript.

## Changes

- Gemini 2.5 Flash/Flash-Lite now use the supported `thinking_budget=0` to avoid
  unnecessary reasoning latency. Gemini 2.5 Pro uses its supported minimum 128;
  Gemini 3+ retains explicit thinking levels. Provider selection is preserved; production now uses the available Gemini 3.5 Flash-Lite model with minimal thinking after a real API check found Gemini 2.5 Flash unavailable for this account.
  This supersedes the older blanket thinking-level requirement for Gemini 2.5.
- A provider exception terminates its caption as `failed`, not `interrupted`.
  Genuine interruptions retain their original phase and actual partial text.
  The shared v2 enum, generated schemas/handoff copies, browser renderer and
  matching public assets are updated. Failures display an Urdu failure label and
  a nonfatal error status, revoke the owning turn and never retry a mutation.
- The tested 350 ms sustained-speech gate remains in detector and SDK interruption
  handling. Raw detections do not bypass it. Existing AEC/warmup, silence/endpoint
  thresholds and action/review safety remain in place. Crashed generations must
  not be misdiagnosed as evidence requiring more aggressive interruption tuning.
- Bounded runtime observations now log state-only speech-finish/failure and user
  activity metadata. Existing per-message provider timing logs remain in use.
  No transcript/audio recording or secret settings are enabled or changed.
- A fresh `get_current_context` action already contains the authority's complete
  snapshot. The browser now reuses that exact correlated session/revision receipt
  instead of fetching it again. Missing, foreign, mismatched or older snapshots
  retain the fresh-read path. Mutating actions and uncertain outcomes are unchanged.
  Four regressions cover both reuse and fallback; entry assets are `zara-30`.
- A bounded hosted question audit exercises the actual website, RTC, Cloud worker,
  provider and tools. It supplies a synthetic silent microphone and recognized
  requests through the existing wake-handoff lane; no production debug hook is
  added. Its status/caption timings are not a physical microphone/STT/audio test.

## Verification before publication

- Five regressions failed before implementation, including actual installed
  plugin `chat()` setup rather than only factory construction, and error captions.
- Focused Gemini/caption/interruption/latency suite: 34 passed.
- Initial worker + website Python: **606 passed / 1 inherited failure** in
  `test_no_mock_imports_outside_adapters`, flagging unchanged `integration/scenarios.py`.
  An intermediate run caught contract regeneration and shutdown-observation issues;
  both were fixed before this final run.
- JavaScript: **76 passed** after context reuse. Browser build passed.
- Replacement-model/deployment guards: **5 passed** after the model selection update.
- Browser: **4 passed** (Urdu/Roman Urdu cart use at desktop/mobile, missing audio
  delivery guard, distinct failed/interrupted captions).
- Changed Python Ruff and scoped Pyright passed; shared v2 schemas regenerated.

## Additional measured tool-path optimization

The first browser-only optimization passed both real questions but timings varied:
2.713 s for category speaking status and 5.423 s for prices in that run. The two
price RPCs consumed 1.103 s and 1.295 s. This unfavorable run is retained; no
statistical improvement is claimed from the browser-only change.

For **filter_menu/search_menu only**, the broker can now use the already-bound,
validated context at the exact requesting turn revision. It still submits a new
authority action whose exact revision is enforced server-side; this does not
serve cached prices or authorize cart/checkout changes. A missed newer manual
revision is rejected, with no retry. Missing/foreign/newer/pending/unbound context
keeps the separate read. Cart, quantity, checkout and clear retain full pre-reads.
The ordinary menu path goes from two authority RPCs to one. Actual results still
render and publish before speech, and post-result context validation remains.

New tests cover one-RPC filtering, a deliberately unpublished manual change,
missing-context fallback and strict binding/revision/pending guards. Focused
runtime/RPC/latency/interruption: 63 passed before adding two fallback cases.
Final full Python: **611 passed / the same 1 inherited failure**. Scoped lint/types
pass. This source change is active in the final worker rollout recorded below.

## Production verification

- Code pushed as `00c0961`, then deployed with `deploy --code-only` to existing
  worker `CA_gibAwTdK3sjn`. Version **THgPWfNyTXZ7**, Running in `ap-south`, was
  deployed at 2026-11-21 14:40:37 UTC (92 staged files, 1,010,330 bytes).
- Real question testing then exposed a second provider failure: Google returned
  404 because Gemini 2.5 Flash is no longer available to new users on this account.
  This could not be found by constructor/no-network tests. Both failures are retained.
- Google model metadata and one native SDK Urdu request verified
  `gemini-3.5-flash-lite` with `thinking_level=minimal`. Only `LLM_MODEL` and
  `LLM_THINKING_LEVEL` were updated in Cloud; credentials and all other settings
  were preserved. The deployment helper defaults now use the available model.
- On `zara-29`, the actual hosted worker answered both category and burger-price
  questions. The price reply used successful `get_current_context` and `filter_menu`
  application actions and quoted all five actual burger prices. Neither reply
  failed or was interrupted. Browser request-to-speaking-status was 1.748 s and
  4.433 s respectively. Caption completion includes the entire spoken reply and
  must not be read as initial-response latency. These recognized-text tests bypass
  microphone/STT; neither their timings nor local scripted VAD tests establish
  caller-heard full speech latency or physical room echo performance.
- Corresponding agent logs show 1.156 s LLM first-token and 64 ms TTS first-byte
  on the category turn. These fields are stage metrics, not audible latency.
- Intermediate audits are retained: attempt 1 had test instrumentation failure,
  attempt 2 captured the real model 404, and attempt 3 successfully answered
  categories but hit an overly strict test-only RPC assertion (category facts were
  already in verified context). The corrected audit completed both turns.
- Final source commit `b689ce8` deployed code-only as **wHsS5nC83K3V**, Running in
  `ap-south`, at **2026-11-21 15:08:43 UTC**. Cloud model settings were preserved.
  The hosted website served `zara-30`. `final-worker-status.json` records the rollout.
- The final hosted audit completed both Urdu requests with **zero errors, failures
  or interrupted replies**. Category request-to-speaking-status was **2.117 s**.
  The burger request took **3.356 s** to speaking status and quoted all five menu
  items with actual prices; it issued **one successful filter_menu RPC (1.416 s)**,
  with no separate context RPC. Caption completion was 14.214 s / 17.680 s and
  includes the entire response; it is not time to first response.
- `hosted-questions.json` records the final run. The slower browser-only result is
  retained in `browser-only-context-result.json`. These two-question samples show
  successful real-provider operation and removal of the redundant round trip,
  not a p50/p95 performance benchmark. Physical microphone/STT, caller-heard
  latency and quiet-room false-interruption rates remain unmeasured.

## Sources consulted

- [LiveKit Gemini thinking configuration](https://docs.livekit.io/agents/models/llm/gemini/#thinking)
- [Google thinking budget support](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/thinking)
- Installed LiveKit Google plugin 1.8.4 chat setup and speech-handle outcome APIs.

- [Available Flash-Lite model and tool support](https://aistudio.google.com/docs/models/gemini-3.5-flash-lite)
