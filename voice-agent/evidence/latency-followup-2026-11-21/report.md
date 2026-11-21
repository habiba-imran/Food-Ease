# Latency follow-up — 2026-11-21

## Logs inspected before changes

Fetched a bounded, redacted deploy-log stream from the existing FoodEase worker.
The latest real audio session is `AJ_qm8PbePzhyyc` / `RM_NMih3dcDDQSB`,
15:15:53–15:18:53 UTC. `cloud-logs.txt` retains the raw worker evidence;
`stage-records.json` contains only extracted timing/state/action metadata.
No transcript, recording or provider configuration was enabled or changed.

- 12 transcription delays: 752.31–789.96 ms; median 770.40 ms.
- End-of-turn delays: 753.09–790.72 ms; median 771.17 ms. These overlap with
  transcription, so they must not be added together.
- Two recorded assistant LLM first-token values: 1302.47 / 1323.62 ms.
- 12 TTS first-byte values: 49.86–61.37 ms; median 57.72 ms.
- 8 registered action-to-result intervals: 0.680–1.868 s. These exclude the
  separate broker pre-read and are not full response or audible latency.
- No failed speech completions. One interrupted completion, whose acoustic
  cause cannot be determined from state-only logs.

The bottleneck targeted is the redundant authority pre-read on cart views,
details and navigation. Provider latency remains present; no subsecond claim.

## Change and safeguards

Use only exact bound session/revision context to submit a *new* read or
navigation request. Read-only results must still match the requesting revision;
a missed manual change synchronizes state and discards the turn without facts.
Navigation/menu actions retain exact server revision admission. Unknown,
missing, newer, foreign, pending or unbound contexts retain the fresh pre-read.
Cart changes and checkout retain all existing pre-reads, result correlation,
confirmation, cancellation ownership and no-retry rules.

A successful correlated get_current_context result already contains the complete
snapshot. Reuse it only for its exact session/revision and when no newer context
has arrived. No time-based cache. No changes to interruption, endpointing,
providers, models, prompts, recording, browser UI or dependencies.

## Verification

- Before implementation: 8 failures / 1 pass in the nine new cases, captured in
  `before-regressions.txt`. Failures demonstrate duplicate RPCs; the stale-context
  rejection behavior itself already existed and is preserved.
- Focused latency/RPC/runtime/output/recovery: **79 passed**.
- Ruff on changed Python and scoped Pyright: passed, 0 errors/warnings.
- Full worker + website Python: **620 passed / 1 inherited failure** in unchanged
  `integration/scenarios.py` (`test_no_mock_imports_outside_adapters`). Raw
  `regressions.txt` retains the failure and existing dependency warning.
- Audit utility JavaScript syntax check passed; no browser runtime assets changed.
- Before deployment, the actual hosted old worker completed all three Urdu
  requests without errors. Speaking-status delays were 4.516 s (cart), 5.285 s
  (navigation), 5.564 s (details). Cart/details each issued a separate context
  pre-read; navigation also required a post-result fallback context read.
  Raw measurements are in `before/hosted-questions.json`.
- Source commit `ac79408` was pushed to origin/main. Code-only deployment preserved
  all Cloud settings and staged 92 files / 1,013,017 bytes. Final worker version
  **M4pgWsdf2rU9** is **Running in ap-south**, deployed at
  **2026-11-21 15:30:36 UTC** (`final-worker-status.json`, `cloud-deploy.txt`).
- After deployment, all three requests completed with zero page errors, failed
  captions or unsuccessful actions. The same hosted website served `zara-30`.
  No browser runtime update was required for this worker-only change.

### Real hosted comparison

| Request | Before speaking status | After speaking status | Before / after authority RPCs |
| --- | ---: | ---: | --- |
| Cart contents | 4.516 s | 4.877 s | context + get_cart / get_cart |
| Open cart | 5.285 s | 3.700 s | context + navigate + context / navigate + context |
| Cola details | 5.564 s | 6.069 s | context + get_item_details / get_item_details |

Each request was run once per version with real providers; every run is retained
in `before/` and `after/`. `comparison.json` is derived from those raw files.
Navigation improved in this sample; cart and details were slower despite removal
of the extra pre-read. The cart action itself varied from 1.733 s to 3.052 s;
details from 1.418 s to 1.751 s. These action spans include browser HTTP and view
synchronization, not only Python execution or LLM inference. The post-navigation
fresh context fallback remains when the data event has not arrived, preserving
freshness at the cost of that legitimate read.

**Conclusion:** the redundant pre-read is removed from each measured request,
but a uniform user-perceived latency improvement is not established by this
small, variable sample. Transcription, provider generation, and website/action
network time remain. No physical voice latency or new p50/p95 claim is made.

The hosted audit uses a synthetic silent microphone and recognized Urdu requests
through the existing handoff lane. It exercises real website/RTC/worker/providers
but bypasses speech recognition. Request-to-speaking-status and caption timings
are not physical microphone/caller-heard audio measurements. A small sample is
not a p50/p95 benchmark. All unfavorable results are retained.

## Sources

- [LiveKit per-turn metrics](https://docs.livekit.io/testing/observability/data/).
- Installed LiveKit Agents 1.8.4 stream adapter and existing contract authority
  revision rules; CLI agent logs/deploy/status help checked in this session.
