# Phase 1 contract freeze

Final orchestration Phase 1 defines contract **2.0**. It is a major version because
the new revision/correlation requirements and mandatory checkout token/summary
binding are incompatible with frozen v1. Both original v1 directories are retained.

The [canonical contract](../../voice-agent/contract/v2/README.md) contains the
field-by-field website/agent matrix, thirteen operations, event schemas, exact
status meanings, quantity/search/result/byte limits, sender authorization,
idempotency, confirmation, read-only lookup, retention and migration rules.
The [Zainab handoff copy](../../zainab-pack/contract/v2/README.md) is generated from
the same source and checked for drift.

Canonical executable types live in:

```text
voice-agent/src/foodease_agent/contract/v2/models.py
voice-agent/src/foodease_agent/contract/v2/projection.py
```

Generate or verify from voice-agent/:

```powershell
$env:PYTHON_DOTENV_DISABLED = '1'
.\.venv\Scripts\python.exe tools\freeze_contract_v2.py
.\.venv\Scripts\python.exe tools\freeze_contract_v2.py --check
.\.venv\Scripts\python.exe -m pytest tests\test_contract_v2.py tests\test_contract_v1.py -q
```

Tests capture actual FoodEaseDomain operations and validate their explicitly
projected outputs against the same models and JSON Schemas. Synthetic transport
failures and authored lifecycle examples are labeled in MANIFEST.json. No provider
is needed and no application endpoint is activated by generation.

Phase 1 does not switch the current worker/broker/website/adapter to v2. It does
not implement per-session storage, token generation, locks, lookup HTTP/RPC,
LiveKit connection, browser rendering or the spoken mode chooser. Those remain
in their existing later phases. In particular, requiring a token in v2 does not
make the existing website's optional-token v1 endpoint secure retroactively.

The Phase 0 agent architecture/lint/type failures and pending browser walkthrough
remain recorded. Habiba explicitly requested Phase 1 next; this contract-only work
does not relabel the earlier gate or claim a live integration pass. No teammate
approval, release tag or deployment is implied.

Phase 1 evidence: [report](../evidence/final/phase-01/report.md).
