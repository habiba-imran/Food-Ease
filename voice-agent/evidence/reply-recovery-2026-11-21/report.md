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
  Gemini 3+ retains explicit thinking levels. Model/provider selection is preserved.
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
- A bounded hosted question audit exercises the actual website, RTC, Cloud worker,
  provider and tools. It supplies a synthetic silent microphone and recognized
  requests through the existing wake-handoff lane; no production debug hook is
  added. Its status/caption timings are not a physical microphone/STT/audio test.

## Verification before publication

- Five regressions failed before implementation, including actual installed
  plugin `chat()` setup rather than only factory construction, and error captions.
- Focused Gemini/caption/interruption/latency suite: 34 passed.
- Worker + website Python: **606 passed / 1 inherited failure** in
  `test_no_mock_imports_outside_adapters`, flagging unchanged `integration/scenarios.py`.
  An intermediate run caught contract regeneration and shutdown-observation issues;
  both were fixed before this final run.
- JavaScript: **72 passed**. Browser build passed.
- Browser: **4 passed** (Urdu/Roman Urdu cart use at desktop/mobile, missing audio
  delivery guard, distinct failed/interrupted captions).
- Changed Python Ruff and scoped Pyright passed; shared v2 schemas regenerated.

## Production verification

Deployment and real question-answer results will be appended after rollout.

## Sources consulted

- [LiveKit Gemini thinking configuration](https://docs.livekit.io/agents/models/llm/gemini/#thinking)
- [Google thinking budget support](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/thinking)
- Installed LiveKit Google plugin 1.8.4 chat setup and speech-handle outcome APIs.
