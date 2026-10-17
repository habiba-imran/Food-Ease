# Final orchestration Phase 6 verification

Date: 2026-10-17. Scope: opening mode choice and mode continuity only.
Branch: `codex/phase-6-opening-modes`. Earlier uncommitted Phase 4/5 work is retained.
No commit, push, provider call or Phase 7 work is part of this change.

## Behavior implemented

- Text ordering question immediately; explicit spoken-welcome consent; direct
  manual, voice and typed paths. Returning visitors use an activation fallback,
  never automatic capture, with brief same-session resume copy.
- Deterministic natural mode choices before model admission. Ambiguous/mixed
  choices, negatives, silence and food requests during onboarding cannot execute
  shopping tools. One clarification, then quiet. One opening per generation.
- Explicit browser lifecycle/mode states, local pause/resume, reconnect status and
  immediate manual/end revocation. Stop/unpublish capture; pause/detach audio;
  retain submitted business outcomes. Recheck queued RPC admission before submit.
- Preserve route/cart across voice/manual/voice and voice/typing/manual. Existing
  mode controls stay reachable in item/checkout dialogs; typed input relocates on
  mode changes. Typed output is silent by default, with a separate audio preference
  that never enables capture.

## Automated evidence

Full offline run:

```powershell
.\voice-agent\.venv\Scripts\python.exe orchestration/tools/phase6_verify.py --output orchestration/evidence/final/phase-06/run-3
```

[Full summary](run-3/summary.json): `unexpected_failures: []`.

| Check | Result |
| --- | --- |
| Focused actual worker/SDK, opening, output, RTC/startup tests | 60 passed |
| Scoped worker lint / types | Passed / 0 errors |
| Website Python tests / lint / types | 39 passed / passed / 0 errors |
| Orchestration Python tests / lint / types | 36 passed / passed / 0 errors |
| JavaScript tests | 29 passed |
| Full-run browser integration | 21 passed |
| Final browser integration after dialog/admission review | 22 passed |
| SDK bundle build, browser fixture types, verifier lint | Passed |
| Frozen v2 contract check | Passed |
| Frozen v1 SHA-256 comparison | 92 checked; zero drift |

After the final browser-only continuity changes, the affected JavaScript and full
browser suites were rerun from `website/`:

```powershell
node --test tests/*.test.cjs tests/*.test.mjs
node tools/browser-test.mjs
```

[Final browser summary](browser-final/summary.json) records exit code zero for both
suites: **29 JavaScript checks and 22 browser tests passed**.
[JavaScript log](browser-final/javascript-tests.log) and
[browser log](browser-final/browser-integration.log) contain the final result.
The Python worker and authority sources did not change after their full-run gate.

The matrix covers fresh/manual with zero dispatch, direct voice and typed, returning
activation fallback, permission allowed/denied/missing/pending, cancellation of a
late permission result, autoplay rejection before readiness, chooser ambiguity and
silence, clear voice/manual phrases, pause/resume in the chooser, in-flight committed
cart outcome after manual, generation/order deduplication, preserved cart/session,
explicit typed audio, and mode switching inside the unchanged checkout route.
Existing Phase 5 browser scenarios also remain in the final suite.

The real browser media test calls native `getUserMedia` with Chromium's synthetic
microphone and asserts actual `MediaStreamTrack` identity and `readyState=ended`.
A real HTML audio element plays a Web Audio generated stream before manual choice;
afterward it must be paused with `srcObject=null`, removed from the DOM, and capture
must be ended and unpublished. Neither a state label nor a fake `stop()` counter
can pass that test. Typed-mode tests trap all capture attempts.

## Inherited repository failures and limits

The complete agent suite has **324 passed and one inherited failure**:
`tests/test_no_mock_leak.py::test_no_mock_imports_outside_adapters`, from the
unchanged legacy `integration/scenarios.py` mock import. Full lint retains 39
inherited issues; full pyright retains 27 errors and 2 warnings. Scoped Phase 6
checks pass. These are matched against the earlier baseline, not hidden as passes.

Run 1 recorded the synchronous mode-admission regression and initial new-test lint
issues. Those were fixed. Native capture initially returned NotSupported in the
headless shell; media tests now use full Chromium. A draft in-flight test blocked
startup context reads as well as its intended mutation; its route is now restricted
to `cart.add_item`. Run 2 passed all 21 browser cases but retained a test-only B010
lint issue; the monkeypatch fixture fixed it. Run 3 has no unexpected failures.
The final browser rerun covers the subsequent dialog/admission changes.

Windows Proactor connection-reset tracebacks can appear when browser fixtures
abort requests. Fake RTC has no attached worker media sink, so SDK warnings about
enabling unset audio are expected in this offline fixture. Neither is evidence of
live provider or physical audio behavior.

**IMPLEMENTATION GATE:** Automated local implementation verification is recorded
above. Provider keys are stripped and dotenv disabled; no paid providers were used.
Historical contracts/evidence are preserved. The pinned browser bundle SHA-256 is
`3e25d8a45c35836a85882fe742f93afc7db94c71959663a79dc4323998eadece`.

**ACTIVATION GATE:** Unverified. RTC/lifecycle/streaming model are local fakes, while
the browser, website authority and worker/SDK logic are real. Native synthetic
capture/generated playback prove browser media lifecycle only. Physical microphone,
Cloud signaling/dispatch, actual STT phrase recognition, provider TTS welcome/audio,
autoplay on target devices and human listening quality still require live evidence.
No human scores or zero-interaction spoken welcome are claimed. Process-local
session limits and later recovery/quality phases remain as previously documented.

See [Phase 6 handoff](../../../docs/PHASE_06_OPENING_MODES.md). Phase 7 has not started.
