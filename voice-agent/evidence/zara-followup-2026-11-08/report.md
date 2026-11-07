# Zara follow-up verification — 2026-11-08

Implementation details, changed files, provider/browser documentation and operating
instructions: [behavior review](../../../website/docs/ZARA_REVIEW_2026-11-08.md).

## Executed checks

Commands run from the indicated package folder using its existing installed environment.
No dependency installation or paid-provider request was made.

| Check | Command / scope | Result |
|---|---|---|
| Urdu, semantic controls, safety, dialogue, speech | worker `.venv/Scripts/python.exe -m pytest tests/test_zara_followup.py tests/test_urdu_assistant.py tests/test_semantic_controls.py tests/test_phase4_acceptance.py tests/test_phase6_dialogue.py tests/test_phase6_speech.py -q` | **129 passed** |
| Full worker suite | worker `.venv/Scripts/python.exe -m pytest -q` | **466 passed, 1 inherited failure** |
| Website authority/template suite | website `../voice-agent/.venv/Scripts/python.exe -m pytest -q` | **41 passed**, one Starlette/httpx deprecation warning |
| JavaScript lifecycle/state/wake tests | website `npm test` | **59 passed** |
| Current browser voice/wake acceptance | website `npm run test:browser -- wake-word.spec.mjs voice-entry.spec.mjs` | **18 passed** in 57.8 seconds |
| Final lock-release follow-up | website `npm run test:browser -- wake-word.spec.mjs` | **6 passed** in 19.3 seconds |
| Changed Python lint | worker ruff on changed runtime/test files; website fixture/template-test lint | **passed** |
| Changed Python types | pyright on eight changed worker runtime/test files | **0 errors, 0 warnings** |
| Browser build | website `npm run build` | **passed** |
| JavaScript syntax | node `--check` on app, wake module and changed browser specs | **passed** |
| Patch whitespace | `git diff --check` | **passed** |
| Visual inspection | browser-generated 375px mobile voice-controls screenshot | Inspected; controls fit the dialog, close/focus is visible, no horizontal clipping |

The inherited full-worker failure is
`tests/test_no_mock_leak.py::test_no_mock_imports_outside_adapters`: unchanged
`src/foodease_agent/integration/scenarios.py` imports `adapters.mock`. This was already
documented in STATUS before this work. No new worker failures remain in the final run.

## Findings during verification

- Initial new regressions failed before implementation (missing wake module, Roman Urdu
  references/affirmations, formatting and casual outcome guards); final focused checks pass.
- The shipped catalog now marks every product available. One old combined-action test
  inferred stock from an ID containing `soldout`. That test and the new Urdu regression
  now explicitly simulate stock loss in the real test authority, preserving the negative
  assertion rather than changing catalog availability.
- A duplicated panel status region was caught and removed. The wake status is announced
  by the existing panel live region; the manual welcome has its own live status.
- Speaking feedback depended on a debug status element absent from the current template.
  State now lives in JavaScript and the existing browser speaking-status check passes.
- Updated the deterministic browser model fixture for current semantic control calls.
  This fixture remains offline-only and supplies no evidence of real-model interpretation.
- Native recognition/lock startup is asynchronous. Tests now wait for actual listening;
  activation waits for both native end and asynchronous lease release. The latter also
  has a dedicated delayed-release unit regression.
- Some sandboxed focused/server processes stalled; they were stopped and relevant
  checks rerun outside the sandbox. No network/provider validation is implied.
- An attempted expanded run encountered legacy `conversation/opening/recovery` browser
  setup that targets the removed `#assistant` navigation and former `data-assist-*`
  controls. It was stopped. Those old specs are **not claimed to pass**. The 18 current
  acceptance tests use the existing welcome and floating voice controls.
- Earlier current-browser iterations exposed assertion/fixture timing and status issues;
  they are superseded by the final 18-case passing run, not counted as passes themselves.

## Requested conversation scenario coverage

These are code/tool/browser checks, not real-model language or physical-audio acceptance.

| # | Scenario | Evidence / practical limit |
|---|---|---|
| 1 | Initial Urdu welcome | Urdu runtime tests assert Urdu-only welcome; browser checks gesture-gated entry |
| 2 | Manual mode | Urdu control test disables input; current browser verifies cleanup with zero orders |
| 3 | Voice mode | Urdu runtime/factory wiring plus real browser chooser/direct activation |
| 4 | Wake word | Wake module tests and six current browser cases; recognizer is fake in tests |
| 5 | All categories | Urdu control reads actual website category targets |
| 6 | Food under 700 | Real authority burger filter test checks every returned price is strictly below 700 |
| 7 | Drinks under 500 | Real authority category/budget test checks returned prices |
| 8 | Multiple products | Urdu real cart test adds mango and cola sequentially; browser wake command adds two wraps |
| 9 | Remove/update | Urdu real cart test sets/removes cola; Roman correction sets last real item quantity |
| 10 | Correct totals | Verified cart test reconciles quantities, fee and total; browser cart follows manual edits |
| 11 | “Doosra wala” | Delivered order, Roman references, sorted-list memory and stale-reference regressions |
| 12 | Mixed Urdu/English | Input reaches semantic model path; code validates Roman references. Real-model accuracy pending |
| 13 | Interruptions/corrections | Existing SDK/runtime ownership tests plus semantic stop, quantity correction and cancellation tests |
| 14 | Unclear speech | Mode clarification and model-path checks; real STT/noisy audio still pending |
| 15 | Confirm before ordering | Urdu delivered summary + exact consent test rejects correction and permits explicit yes |
| 16 | Unavailable item | Simulated stock loss is rejected by actual website authority; cart stays empty |
| 17 | Duplicate actions | Worker repeated-mutation guard; wake latch; browser repeated wake writes cart once |
| 18 | Self activation | Native recognition ends before voice playback; late result ignored. Physical acoustic test pending |
| 19 | Permission/autoplay | Native permission/error unit tests plus actual browser error/cleanup/fallback checks |
| 20 | Accessibility | Native pressed-state controls, keyboard Enter activation, focus restoration and mobile browser checks; human screen-reader acceptance pending |

## Remaining acceptance and configuration

Restart the existing worker/local launcher to load the policy and Urdu resource changes.
No private environment changes are required. Wake listening needs a supporting browser,
permission, Urdu recognition support and HTTPS/localhost; it may use a browser-owned remote
speech service and is re-enabled explicitly after each conversation. Manual/typing remain
available without that feature.

No live STT/LLM/TTS conversation, fluent Urdu listening panel, physical screen-reader/device
walkthrough, wake false-positive measurement or audible latency measurement was performed.
The retained Cartesia voice's Pakistani accent/naturalness is unverified. Demo checkout
remains simulated. No restart, push, deployment or real order/payment was performed.
