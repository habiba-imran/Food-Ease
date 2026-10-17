# Final orchestration Phase 7 evidence

Date: 2026-10-17. Branch: `codex/phase-7-grounded-conversation`.
Base HEAD: `ca7bc59ad6a66baa73f0cb70c89e169911bdd335`.
Earlier uncommitted Phase 4–6 work is preserved. No commit/push, UI redesign,
contract/schema change, provider call or next-phase implementation was performed.

**IMPLEMENTATION GATE: passed under the offline conditions below.**
**LIVE MODEL / LISTENING QUALITY GATE: open; not evaluated.**

## Implemented and verified

The actual integrated worker has a bounded semantic page, verified item details,
grounded page/cart reading, semantic button commands, completed-output item
references and next/previous windows. Manual changes invalidate stale references.
Overlapping product names and pronunciation variants retain actual presentation
order. Returned rows alone do not establish a presented list.

Filter refinement preserves existing preferences and can clear individual
constraints. Its arguments are merged against fresh serialized state, including
overlapping tool invocations. Multi-step turns retain current revisions, stop
mutations after a failed/ambiguous step and reject duplicate normalized writes.
The existing thirteen operations, owned uncertain outcomes and checkout consent
are retained. The real streaming-model path is used for broader shopping dialogue,
recommendations and comparisons; no scripted planner was installed in production.

Actual prompt/tool descriptions now ask for concise progressive guidance, one
useful follow-up, comparisons based on verified details, honest unknown ingredients
and restrained speech. Existing speech shaping runs at sentence boundaries before
TTS/transcription branching. Fractional digits preserve amounts such as 350.05;
captions and TTS follow the same shaped words. Supported speech controls invoke
real SDK options; unsupported settings do not receive a false acknowledgment.

## Commands and results

From the repository root:

```powershell
.\voice-agent\.venv\Scripts\python.exe orchestration/tools/phase7_verify.py --output orchestration/evidence/final/phase-07/run-2
```

[Final summary](run-2/summary.json): **zero unexpected failures**, 92 legacy v1
files checked, zero drift. Frozen v2 check passed. Historical dialogue/evidence
trees were included in preservation. Provider keys were stripped and dotenv
disabled; SDK/browser bundle versions were not upgraded.

| Check | Actual result |
| --- | --- |
| Focused worker, SDK, opening, page/reference, action and campaign checks | 81 passed |
| Prompt safety, legacy dialogue/fault phrasing and speech checks | 108 passed |
| Scoped worker lint / types | Passed / 0 errors |
| Campaign tooling types / lint | 0 errors / passed |
| Website Python tests / lint / types | 39 passed / passed / 0 errors |
| Orchestration Python tests / lint / types | 36 passed / passed / 0 errors |
| JavaScript tests | 29 passed |
| Real-browser/local-fake integration tests | 27 passed |
| Browser bundle build / fixture types | Passed / 0 errors |
| Frozen contracts | Passed |

Browser command: `node tools/browser-test.mjs` from `website/`.
The five added cases verify actual DOM/captions and authoritative state for page
reading, presented ordinal selection and Add to cart, stale references after a
manual change, next/previous windows, budget/tag refinement, dependent search/add
and correction by set_quantity. The earlier 22 browser cases remain passing,
including checkout consent, exactly one receipt, media shutdown and mode continuity.

The browser, website HTTP authority, worker, SDK agent/session and tool wiring are
real. RTC/lifecycle/model are local fakes. Native Chromium capture uses a synthetic
device, and media tests use generated playback. These are not provider/STT/TTS,
physical-device, latency or human naturalness measurements. The campaign driver
also has an explicit local-model fixture test with the real website HTTP authority;
its temporary outputs are test fixtures, not real-model evidence.

## Real-model and human gate

The [prepared manifest](campaign-prepared/manifest.json) records **41 cases, 50
planned turns, 0 actual model turns and 0 human listeners**. Cases are in
[cases.json](campaign-prepared/cases.json); the
[rating sheet](campaign-prepared/listening-ratings.csv) contains blank ratings.
The source and guarded runner are `orchestration/tools/phase7_cases.py` and
`orchestration/tools/phase7_campaign.py`.

No Google API key was loaded in this process. The runner requires an existing
environment key, explicit provider-cost opt-in, model and thinking level; it never
loads `.env`. Google HTTP retries and SDK retries are disabled and requests/output
tokens bounded. Its future headless summary receipt is labeled text-only and
cannot pass a browser/audio delivery gate. No paid calls were attempted here.

The acceptance work still required is at least 40 varied actual model turns,
review of tool arguments/accuracy, unnecessary clarification on unambiguous
requests, false success, duplicates and critical factual/consent errors; then at
least three listeners rating sampled live provider/browser replies. Record sample
size and actual medians for naturalness, relevance, brevity and comfort (suggested
minimum 4/5). None of those quality metrics has been fabricated or substituted
with scripted DS metrics. Legacy DS-01–25 families are regression evidence only;
onboarding/site cases extend them, while actual provider fault campaigns remain
Phase 8. The English/PKR core has no new bilingual quality claim.

## Inherited failures and review fixes

Complete agent pytest: **346 passed; one inherited failure**, the unchanged
`test_no_mock_leak.py::test_no_mock_imports_outside_adapters` import in legacy
`integration/scenarios.py`. Full lint retains **39 inherited issues**; full
pyright retains **27 errors and 2 warnings**. The final runner matches those exact
baselines separately from scoped success.

Initial tests caught overlapping-name matching and were fixed to consider later
standalone occurrences. Type checks caught deferred argument/adapter annotations
and the campaign helper import path; those are corrected. The combined browser
case initially clicked an invisible empty-state control; it now uses the visible
Show all filter. The headless campaign fixture exposed trailing transcript
whitespace, now normalized in the trace. Run 1 records intermediate failures;
Run 2 has no unexpected failures. No frozen/historical output was relabeled as
new live evidence.

The SDK may warn about unset audio in fake RTC fixtures; Windows Proactor resets
may occur when fixture HTTP requests are aborted. Passing fixture tests do not
resolve live provider/device behavior.

## Remaining work

**Two planned implementation/delivery phases remain:** Phase 8 reliability and
interruption/uncertain-outcome recovery, then Phase 9 joint live acceptance,
performance/accessibility/device testing and reproducible handoff. Phase 7's
model/listener gate and earlier live activation checks remain open as well.
Phase counts are not an effort percentage. UI polish/animations remain Zainab's
separate track. See the [handoff](../../../docs/PHASE_07_GROUNDED_CONVERSATION.md).
