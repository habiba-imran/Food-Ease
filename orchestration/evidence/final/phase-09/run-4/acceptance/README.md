# Operator evidence

No checks have been run. Use FINAL_RUNBOOK.md.
Keep original failed attempts; do not substitute SDK/server time for audible timing.
Evidence paths stay inside this folder. No tokens, raw audio or personal data.
Ratings: listeners [{id, naturalness, helpfulness, evidence}]. Scores are 1..5.
Samples: [{sample_id, kind, warmth, clock_id, source, onset_ms, playback_ms, completed, genuine, evidence}]. kind=greeting/response/interruption; warmth=warm/cold; source=audible_observation. Each timing pair uses one common clock. A failed completion may leave playback_ms null. Never omit failed attempts.
Evaluation checks operator attestations; it cannot independently certify their truth.
