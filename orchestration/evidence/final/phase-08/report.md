# Final orchestration Phase 8 evidence

Date: 2026-10-17. Branch: `codex/phase-8-recovery`.
Base HEAD: `ca7bc59ad6a66baa73f0cb70c89e169911bdd335`.
Earlier uncommitted Phase 4–7 work is preserved. No commit/push, UI redesign,
dependency upgrade, schema/contract change, vendor call or Phase 9 implementation.

**IMPLEMENTATION GATE: passed under the offline conditions below.**
**LIVE PROVIDER / AUDIBLE INTERRUPTION GATE: open; not evaluated.**

## Changes

The production runtime handles SDK provider errors, preserves silent typing after
exhausted speech-provider failures, and leaves manual controls after model failure.
Recovery revokes old turns, references and checkout authorization, reconciles
original action IDs and fetches fresh session state even at the same revision.
Browser reconnect waits for both seats and a correlated worker resume acknowledgment.
It blocks new mutations/input and detaches audio until recovery; paused/undecided
modes do not silently become active voice. Old receipts cannot unpause a later pause.

Uncertain outcomes retain ownership and distinguish processing, not-yet-registered
and expired records. Found nonterminal results cannot clear pending ownership.
Already committed add/order effects and receipts are recovered once; neither an
interruption nor a lost response resubmits a mutation. Manual edits stay authoritative
through delayed results. Shutdown drains owned submissions without late speech.

The browser persists cleanup request/generation IDs without credentials or checkout
tokens, reconciles them on reload, and uses a Web Lock to guard duplicate tabs.
Mode switching awaits lock release. Background/pagehide, seat loss, status failure
and credential expiry stop capture/output locally and require a new gesture.
The issued token lifetime is a conservative end deadline, not a private SDK token
refresh or automatic replacement dispatch. State outside process-local retention
is explicitly unavailable; no receipt or cleanup success is invented.

See [behavior and retention limits](../../../docs/PHASE_08_RECOVERY.md).

## Verification

From the repository root:

```powershell
.\orchestration\.venv\Scripts\python.exe orchestration/tools/phase8_verify.py --output orchestration/evidence/final/phase-08/run-2
```

The verifier strips provider keys, disables dotenv and preserves legacy contracts
and historical evidence. SDK/package versions remain unchanged. Local test provider
subclasses raise errors through actual SDK STT/TTS/LLM interfaces; no global
production fault flag was added. The website authority, HTTP requests, SDK session,
worker tools and DOM renderer are real. RTC/lifecycle/model replies are local fakes.
Chromium media capture uses a native synthetic device; playback tests use generated
media. These do not establish Cloud, vendor, physical microphone or audible timing.

| Check | Final observed result |
| --- | --- |
| Focused worker / SDK / recovery tests | 99 passed |
| Safety, dialogue, legacy fault wording and speech | 108 passed |
| Scoped runtime lint / types | Passed / 0 errors |
| Website Python tests / lint / types | 39 passed / passed / 0 errors |
| Orchestration tests / lint / types | 36 passed / passed / 0 errors |
| JavaScript authority, lifecycle, replay and recovery tests | 44 passed |
| Chromium integration, opening, conversation and recovery | 37 passed |
| SDK bundle build | Passed |
| Browser fixture types / verifier lint | 0 errors / passed |
| Frozen v2 contract check | Passed |
| Legacy v1 preservation | 92 files checked; zero drift |

[Final machine summary](run-2/summary.json): **zero unexpected failures**; all
scoped checks passed. No historical evidence needed restoration in this run.

The broader agent baseline is **364 passed, 1 inherited failure**:
`test_no_mock_leak.py::test_no_mock_imports_outside_adapters`, from the existing
legacy `integration/scenarios.py` mock import. Full Ruff retains **39 inherited
issues**; full pyright retains **27 errors / 2 warnings**. These are recorded by
baseline checks; the repository-wide checks are not described as clean.

The [first full run](run-1/summary.json) intentionally remains as failed evidence.
Its reused Phase 7 campaign-prepare command rejected the Phase 8 output path; that
unrelated preparation command was removed from the recovery verifier. The browser
run also found an immediate mode-switch lock-release race and a reload expectation
that did not allow completed retained cleanup to enter manual mode. Lock release
is now awaited; the reload test still requires inactive state and explicit capture
consent. Both targeted browser regressions passed before the final full run.
Additional tests reject stale resume receipts, hold new audio during recovery,
expire the reconnect deadline, preserve paused/chooser modes and reject nonterminal
found outcomes. Historical failure logs were not overwritten.

## Failure matrix

| Dependency / scenario | Evidence and verified local behavior |
| --- | --- |
| STT | Actual SDK recognizer interface throws; SDK forwards error; silent typing continues. Browser typed-error injection stops native tracks. |
| TTS | Actual SDK chunked synthesis throws; SDK forwards error; healthy model/text reply continues without TTS warning recursion. |
| LLM | Actual SDK local streaming provider throws with no retries; runtime ends; browser manual add still works. |
| Room / reconnect | Both-seat barrier, fresh context, same-generation resume receipt, no new media/dispatch, paused/chooser preservation, timeout and old-event rejection. |
| HTTP / context | Lost real website responses reconcile by original ID; failed fresh-context reads keep worker paused. |
| RPC timeout / response loss | Production RPC adapter plus real SessionStore; original action lookup recovers committed add without another submission. Checkout response loss retains original receipt. |
| Dispatch | Existing real AssistanceService with fake Cloud: lost create response, pending cleanup, canceled HTTP caller and expiry; no second dispatch or invented teardown. |
| App / agent participant loss | Exact bound app-seat loss revokes worker; browser bound-agent loss ends capture; foreign participants do not revoke it. |
| Expired credentials | Issued-lifetime and status failures stop active resources; startup expiry never activates; browser injected HTTP 410 stops acquired media before joining. |
| Manual change / interruption | Manual quantity wins over delayed committed add; speech/end does not cancel or repeat the write; false-interruption observation cannot recommit old tools. |
| Reload / retention | Cart/receipt survives within retention without auto-capture; pending/expired outcomes keep identity and do not replay checkout; actual new-SessionStore restart tests show lost authority. |
| Background / shutdown / duplicates | Background/pagehide ends locally; late old events cannot revive it; owned writes drain; duplicate Web Lock admission is refused until release. |

The added browser recovery suite covers 10 cases. Its events and outages are
injected locally; native track lifecycle is real. Existing browser coverage includes
same-cart checkout consent, exact rendered summaries, stale context, typed audio,
manual edits and confirmed receipt reload. JavaScript tests exercise lock ownership,
credential/reconnect deadlines, stale acknowledgments and pending outcome states.
Worker tests include actual public SDK forwarding plus late-effect reconciliation.

## Live gate and remaining work

**0 vendor outage samples, 0 audible barge-in measurements, 0 human false-interruption
judgments** were produced. Runtime event observations are bounded metadata only;
their timestamps are not audible-stop latency. No p50/p95 or human score is invented.
The [live checklist](live-checklist.md) and [blank measurements CSV](live-measurements.csv)
make the unperformed checks reviewable. Phase 7's real-model / three-listener quality
gate also remains open.

Only **Phase 9 — joint live acceptance and reproducible delivery** remains in the
implementation plan. It is not started. Outstanding Phase 7/8 live checks remain
required validation; passing the offline implementation gate does not waive them.
