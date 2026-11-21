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
- Two non-tool assistant LLM first-token values: 1302.47 / 1323.62 ms.
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
- The code-only rollout and repeated deployed measurements follow below.

The hosted audit uses a synthetic silent microphone and recognized Urdu requests
through the existing handoff lane. It exercises real website/RTC/worker/providers
but bypasses speech recognition. Request-to-speaking-status and caption timings
are not physical microphone/caller-heard audio measurements. A small sample is
not a p50/p95 benchmark. All unfavorable results are retained.

## Sources

- [LiveKit per-turn metrics](https://docs.livekit.io/testing/observability/data/).
- Installed LiveKit Agents 1.8.4 stream adapter and existing contract authority
  revision rules; CLI agent logs/deploy/status help checked in this session.
