# Final orchestration Phase 5 verification

Date: 17 October 2026. Branch: `codex/phase-5-browser-integration`.

Phase 5 connects the website's bound LiveKit seats to the existing application
authority and actual worker conversation/tool path. It replaces mock assistant
execution/echo with canonical typed/control transport, one action/render lane,
verified page context, captions/status, native audio ownership and visible typed
summary delivery receipts. Existing styles and animations are preserved; only
functional controls, dialog placement, copy and long receipt-ID wrapping changed.

**IMPLEMENTATION GATE: PASS for the scoped offline browser/integration checks.**

**ACTIVATION GATE: not passed or claimed.** The tests use real Chromium and the
real website/worker/SDK logic with fake RTC, assistance lifecycle and streaming
LLM providers. Fake track attachment/stopping is not actual microphone, audible
playback, Cloud signaling, provider speech, autoplay or human listening evidence.
No paid-provider or real Cloud call was made. Phase 6 has not started.

## Final repeatable command

From `orchestration/`:

```powershell
.venv\Scripts\python.exe tools\phase5_verify.py --output evidence\final\phase-05\run-3
```

The [final summary](run-3/summary.json) records commands, package directories and
exit codes, with no unexpected failures and zero frozen v1 drift. Adjacent logs
provide raw results. Provider credentials are removed and dotenv is disabled.
Historical/frozen evidence is preserved around legacy tests.

| Check | Result |
|---|---|
| Chromium browser integration | 10 passed |
| Actual worker/runtime/production adapter/startup/RTC/output regressions | 49 passed |
| JavaScript authority/lifecycle/session transport | 24 passed |
| Website authority and application regressions | 39 passed; one inherited Starlette/httpx warning |
| Orchestration regression suite | 36 passed; one inherited Starlette/httpx warning |
| Scoped worker/output/browser fixture lint and types | Pass; 0 type errors/warnings |
| Website and orchestration lint/types | Pass |
| Browser bundle build | Pass; exact same output hash after rebuild |
| Frozen v2 contract/schema/example/handoff check | Pass |
| Frozen v1 preservation | 92 files checked; zero drift |
| Verification runner lint | Pass |
| Complete agent suite | 313 passed; one inherited mock-boundary failure |
| Complete agent lint | 39 inherited issues |
| Complete agent types | 27 inherited errors, 2 warnings |

The existing agent-wide failure remains
`tests/test_no_mock_leak.py::test_no_mock_imports_outside_adapters`, caused by the
unchanged `integration/scenarios.py` import. The verifier explicitly matches these
baseline failures/counts; it does not label the whole repository clean.

The browser bundle uses livekit-client **2.15.4**, esbuild **0.28.2** and locked npm
dependencies. Tests use Playwright **1.64.1** with Chromium **156.0.8078.4**. The
[reproducibility record](bundle-reproducibility.json) confirms matching SHA-256
before/after build:

```text
3e25d8a45c35836a85882fe742f93afc7db94c71959663a79dc4323998eadece
```

The website was added only to the voice agent's development dependency group so
the locked test environment includes FastAPI/Uvicorn. Existing provider/SDK
versions were retained. No production voice-to-website Python dependency or
additional conversation engine was introduced.

## Browser gate coverage

- **Actual typed order, no microphone:** explicit typed start connects two fake
  RTC seats through the production bridge/controller and real readiness seam.
  "Add two Hot Chicken Wraps" enters the actual SDK agent/LLM/tool/policy/broker,
  executes the real website API and displays two wraps, subtotal PKR 1700, service
  fee PKR 50 and total PKR 1750. Checkout renders the exact summary, its post-render
  receipt authorizes a subsequent typed yes, and one demo receipt clears the cart.
  Reload retrieves the same retained receipt without another submission. A
  getUserMedia trap proves typed assistance did not request microphone access.
- **Injected bound actions:** real browser RPC handlers visibly change menu search,
  ordered result IDs, selected item dialog, cart quantities and checkout review.
  Every operation result is correlated with the original request. Unbound caller
  identity cannot forward an action. The UI uses the same real authority as clicks.
- **Manual synchronization:** clicked cart edits publish the authoritative quantity
  and revision to the worker-visible context channel. Menu cards exactly match the
  snapshot's bounded visible IDs. Availability filtering, the inclusive budget,
  clearing search/filters, category/route/dialog state and totals share rendering.
- **Unknown outcomes:** loss of a reply after a real authoritative commit reconciles
  the original action once, with one submission. A request whose outcome is unknown
  remains owned across reload, blocks resubmission, then reconciles the later
  terminal result of that delayed original request. Pending storage contains no
  checkout token. Rejected sold-out actions do not produce a success announcement.
  A verified mutation whose view delivery fails also remains owned until recovery
  renders it, with no second submission; a dedicated regression verifies this boundary.
- **Ordering/reconnect:** stale mutations cannot alter a newer view or cart. A
  reconnect callback fetches and republishes current context. The model unit test
  also feeds regressive context directly and proves it cannot repaint newer state.
  Manual queue admission uses the latest revision; explicit same-ID diagnostic
  replay retains the original envelope and rejects changed arguments.
- **Captions/focus/audio:** interim and final caption updates share one DOM row;
  a late partial cannot overwrite its terminal text. The input remains focused.
  Worker interruption captions use the SDK handle's actual partial chat items.
  Native caption events are not displayed again. Typed mode attaches no remote
  audio; fake voice mode attaches one element per track SID and End immediately
  detaches it and stops fake media. This is ownership evidence, not audibility.
- **Readiness and cancellation:** existing lifecycle tests still cover consent,
  denied/pending permission, late seats/media, startup cancellation and failed
  remote cleanup. Browser admission waits for lifecycle activation rather than an
  early SDK listening event. End and audio failure close the local lane before
  remote cleanup; pending business results remain independently owned.

The browser fixture substitutes RTC transport, lifecycle endpoints and the LLM;
its actual worker startup, role-bound gate, SDK session/agent/tools, policy/broker
and real application authority are exercised. Only SDK RoomIO attachment is
substituted because there are no WebRTC tracks in the local fake room. These
substitutions are explicit in `website/tests/browser_server.py`; its test routes
are never imported by the production website.

The [receipt screenshot](browser/typed-receipt.png) was captured from the actual
headless browser and visually inspected. It shows fictional demo state only.
The existing dark dialog shell now contains readable captions/form; a long receipt
identifier wraps. This is not a visual redesign or live provider screenshot.

## Test-first and repair record

The first `application.test.mjs` run failed with the expected missing
`application.mjs` module before implementation. Early browser iterations exposed
and corrected the fixture's SDK dictionary-string parsing, the canonical publisher's
timestamp serialization and an actual early-listening/activation race. A modal
focus trap also required placing the existing typed controls inside the active
dialog. The final production path has one renderer and one caption transport.

The old Playwright shell-owned server teardown stalled on Windows once; that exact
disposable process was stopped. The replacement runner directly owns the Python
process, refuses an occupied port and terminates it in `finally` on pass/failure.
Intentional aborted transport tests may print a Windows connection-reset callback;
fake voice tests log that there is no real audio sink. Neither is live-media proof.

[Run 1](run-1/summary.json) retained one new website test-line lint failure while
all browser/logic checks passed. Formatting fixed it. Run 2 passed every scoped
check. A semantic Home-link adjustment was checked separately by the focused
[browser post-review log](run-2/browser-home-postreview.log). Final review then
added ownership through failed view delivery and its dedicated regression.
Run 3 passed the resulting 24 JavaScript tests, all 10 browser cases and every
other scoped check. Existing CSS, frozen contracts and historical handover
evidence were preserved.

## Remaining boundary

See [browser/runtime handoff](../../../docs/PHASE_05_BROWSER_INTEGRATION.md) for
launch, exact channels and limits. The page now has the real integration path,
but Cloud/provider/browser audio must still be tested directly with a configured
consented session. The initial spoken choice (“manual or voice?”), complete mode
continuity and its permission/autoplay matrix remain Phase 6. Later conversational
quality and human listening acceptance remain unverified.
