# Lever snapshots (V9.1)

After each 9.3 lever change, append metrics to a new JSONL and add `lever-NN-name.json`:

```json
{
  "name": "lever-01-baseline",
  "jsonl_files": ["evidence/phase-9/campaign/baseline/metrics.jsonl"]
}
```

Re-run `uv run python tools/generate_latency_report.py` to refresh tables.
