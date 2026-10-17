# Final orchestration Phase 9 evidence

Date: 2026-10-18. Branch: `codex/phase-9-delivery`.
Base HEAD: `ca7bc59ad6a66baa73f0cb70c89e169911bdd335`.
Earlier uncommitted Phase 4–8 changes are preserved. No commit, push, public
deployment, UI redesign, dependency upgrade or frozen-contract change was requested.

**IMPLEMENTATION GATE: passed under the offline conditions below.**
**ACTIVATION / FINAL LIVE ACCEPTANCE GATE: pending; no live observations supplied.**

## Delivered behavior

The [final runbook](../../../docs/FINAL_RUNBOOK.md) is the canonical delivery path.
`demo_up.py` prints valid PowerShell or owns the real website/session/worker stack.
Manual mode starts only the actual website and unconfigured session service, strips
provider credentials and disables dotenv/dispatch. Live mode selects the named
integrated worker, explicit website transport and distinct configurable ports;
it requires `--allow-live`. There is no MockApp or harness in that launch path.

Startup refuses occupied ports without killing their owners. Private stdin requests
graceful shutdown of exact owned child handles, including on Windows; session
cleanup runs while the website and worker still exist. A forced fallback explicitly
fails the launch and leaves remote cleanup unverified. Pipe readiness polling
avoids holding Python/CRT stdin locks during native imports, on both Python 3.11
and 3.12. The configurable per-service startup deadline defaults to 180 seconds
(maximum 600), and SDK job initialization gets 60 seconds for cold VAD loading.
Worker package configuration loads before SDK
CLI authentication and agent-name resolution, and its health port is configurable.
The helper's health checks neither create a session nor dispatch an agent.

The integrated runtime passes `record=False` and `session_host=False` to the public
SDK start API. This overrides the Cloud recording default and disables an unused
RemoteSession control surface. The browser continues through FoodEase's bound
semantic transport and thirteen operations. Correlation logs include session,
generation, turn/action and dispatch identifiers with explicit evidence provenance;
they omit action arguments, tool results, credentials and transcripts. Safe defaults
keep recording, development endpoints and the legacy/mock final path off.

The runbook covers locked installation, manual/live launch, costs and permissions,
shutdown/recovery, bounded process-local retention, support limits, secret placement,
and the optional HTTPS/same-site proxy boundary. Ownership and package READMEs point
to it. Public deployment and visual polish remain separate work.

`final_acceptance.py` prepares the unchanged **21 O + 22 W + 20 T** requirements as
63 not-run observations. It requires device, accessibility, dependency-failure and
listener evidence, checks local artifact references and validates measured audible
samples. It retains failed ordinary turns in the completion denominator, separates
warm/cold percentiles, rejects invalid clocks/times and keeps blank evidence pending.
Its input is operator-attested evidence, not an independent certificate. It never
calls a provider, fabricates ratings or automatically retires a waiver.

## Verification

From the repository root:

```powershell
.\orchestration\.venv\Scripts\python.exe orchestration/tools/phase9_verify.py --output orchestration/evidence/final/phase-09/run-local
```

The verifier strips provider keys and disables dotenv/provider model downloads.
It preserves frozen/historical artifacts. Real website HTTP, domain authority,
worker runtime and Chromium DOM/media lifecycle are exercised. RTC, lifecycle,
LLM and provider faults use local substitutes. Chromium capture is synthetic and
playback media is generated; neither is physical microphone/provider audibility.

The [final validation summary](final-validation.json) combines unchanged production-code
[run 4 results](run-4/summary.json) with the
[final full browser rerun](browser-final.json) and
[strengthened receipt/reload check](browser-receipt-recovery-final.json). It observed:

| Check | Observed result |
| --- | --- |
| Focused integrated worker / SDK tests | 102 passed |
| Safety / dialogue / speech regressions | 108 passed |
| Scoped runtime lint / types | Passed / 0 errors |
| Website Python tests / lint / shared types | 39 passed / passed / 0 errors |
| Orchestration tests / lint / types | 56 passed / passed / 0 errors |
| JavaScript tests | 44 passed |
| Chromium integration tests | 40 passed |
| Stronger lost-response receipt/reload assertions | 3 consecutive targeted runs passed |
| Bundle build / browser fixture types / delivery tools | Passed |
| Printed final commands / installed worker CLI help | Passed without credentials |
| Actual owned manual HTTP launch / graceful shutdown | Passed; ports released |
| Frozen v2 contract | Passed |
| Legacy v1 preservation | 92 files checked; zero drift |
| Empty final acceptance evaluation | Exit 2, correctly pending |

The manual smoke creates an owner-bound shopping session over actual HTTP, adds
one Hot Chicken Wrap and verifies quantity one / PKR 900 total. It then confirms
shutdown releases its temporary website/session ports. No worker or provider runs.
Browser delivery regressions complete manual checkout with keyboard activation,
exit typed assistance from inside checkout and isolate two shopper contexts.

The broad agent baseline remains **367 passed, one inherited failure** in
`tests/test_no_mock_leak.py::test_no_mock_imports_outside_adapters`, caused by the
legacy `integration/scenarios.py` mock import. Full Ruff retains **39 inherited
issues**; full pyright retains **27 errors / 2 warnings**. Repository-wide checks
are not clean; the verifier records these separately from scoped checks.

After run 1, startup review found that an omitted SDK `record` argument can follow
the Cloud job default despite `RECORD_AUDIO=false`. A focused entrypoint regression
failed with missing `record`, then passed after explicitly disabling recording and
RemoteSession hosting. [Run 2](run-2/summary.json) repeated the complete verification
on that recording-policy change. The final validation includes the subsequent
startup fixes and stronger browser assertions: **28 checks, zero unexpected
failures and zero v1 drift**. The [first run](run-1/summary.json) remains preserved. See
[ADR-0021](../../../../voice-agent/docs/decisions.md).

The [third full run](run-3/summary.json) overlapped the startup test-first edits:
its full agent process had loaded the previous 10-second options before the new
60-second regression assertion ran. That failure is retained; subsequent isolated
startup tests and run 4's full agent suite use the final implementation. Run 4
also found an early keyboard-test check accepting hidden `DEMO-0000` receipt text.
That let Enter run before the real receipt was visible. The test now requires a
visible receipt, a real ID and an empty cart, plus visible/focused controls before
keyboard activation. No production UI was changed to address this test failure.
The lost-response/reload receipt regression now also requires the real receipt panel
and rejects the placeholder, so it cannot pass by reading hidden template text.
The failed browser log remains in run 4. The repaired keyboard checkout check
passed five consecutive targeted runs, then the full suite passed all 40 cases;
the stronger receipt/reload assertions passed three further targeted runs. The
final browser logs and return codes are recorded separately rather than overwriting
historical failure evidence. Production code did not change after run 4 began.

## Configured live-stack startup

The [bounded startup observation](live-startup.json) is actual configured-service
evidence, separate from the offline verifier. The final command started all three
real services, observed HTTP 200 health responses, successful Silero runner
initialization and the SDK's actual `registered worker` event for `foodease` on
LiveKit Cloud. The helper then drained the worker and shut down session/website
cleanly, exit 0, without forced termination. It created no room or dispatch and
started no STT/model/TTS conversation or physical microphone capture. This proves
configured worker registration, not three room seats or audible acceptance.

Earlier startup attempts failed and remain documented in that observation. A fixed
60-second deadline, then a longer retry, exposed an actual stdin/native-import
deadlock. A held-open pipe NumPy probe blocked until its input closed; direct import
completed. The final child-process regression exercises stdin buffer inspection
and private graceful stop on both installed interpreter versions. A temporary
nonblocking API worked on Python 3.12 but was unavailable on the website's 3.11;
the final implementation polls Windows PeekNamedPipe before raw reads. That attempt
also exposed the SDK's default 10-second VAD initialization budget. Increasing the
supported budget and fixing the pipe produced the successful registration above.
The earlier forced-stop warning is recorded as a failed observation despite its
then-zero exit code; the launcher now rejects forced cleanup in code and tests.

## Live acceptance still required

Habiba subsequently approved beginning paid-provider live acceptance. The
[approved live attempt](live-acceptance-1/environment.md) relaunched the bounded
actual stack, registered the worker and opened the actual website in Google Chrome.
Computer Use then stopped because its safety check could not confidently determine
the browser URL. Desktop input stopped as required; no workaround bypassed that guard.
The attempt did not start a voice/model conversation or establish three room seats.
Provider approval remains valid; the next attempt needs a usable browser control
path and the required human observations, rather than another cost-approval request.

The [prepared acceptance packet](run-4/acceptance/observations.json) and its
[pending evaluation](run-4/acceptance/evaluation.json) contain **zero actual model turns, zero human
listeners and zero audible measurements**. Device, accessibility and fault rows are
not run. Use a fresh run folder for live observations. No private `.env` content was inspected. Normal configured service startup
loaded configuration privately; only the Cloud worker-registration result above is
claimed. Provider conversation, physical microphone, human screen reader and public
hosting acceptance remain unperformed.

Before final acceptance, Habiba and Zainab must observe the runbook-only launch in
a clean environment, establish the real app/user/agent seats, and run all 63 O/W/T
cases against the actual website/LiveKit/provider path. Required coverage includes
Chrome and Edge desktop, a phone, human keyboard/screen-reader mode switching,
provider/transport failures and clean-up behavior. A healthy HTTP endpoint does not
prove any of these observations.

The outstanding conversation gate requires at least **40 real-model turns** and
**three distinct listeners**, with median naturalness/helpfulness at least 4/5.
Performance requires at least **30 ordinary live attempts** and **10 genuine
interruptions**, failures retained, actual audible common-clock timing and warm/cold
p50/p95 groups. Targets remain warm greeting 800/1500 ms, cold greeting 2000/4000 ms,
normal response 1200/2500 ms, interruption stop p95 350 ms and completion at least 95%.
Permission/network/device/account conditions must accompany those measurements.

Existing Phase 7/8 and historical live waivers remain open until replacement evidence
is reviewed. No implementation phase follows Phase 9 in the approved plan; this
remaining work is live acceptance and fixes justified by its real results.

## Reproduction limits

The current checkout and installed locked environments were tested; a fresh-machine
installation and real three-seat Cloud launch were not. The branch includes earlier
uncommitted phase work, so the base Git SHA alone does not reproduce this delivery.
The [source fingerprint](source-fingerprint.json) records SHA-256 hashes of 135
runtime/delivery text files and package/build locks, including that uncommitted
code. It excludes private configuration, audio, images, documentation, tests and
installed runtimes; it is a content inventory, not a clean-clone acceptance result.
No deployments, credentials, provider quotas or Cloud recordings were changed.
Manual mode and local browser tests leave no running stack. Store only redacted
observations; do not attach tokens, raw audio or personal data.
