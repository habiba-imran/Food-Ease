# Upstash Free audit and local coordination fixes — 2026-11-09

## Result

Native TCP WATCH/MULTI/EXEC support and TLS are documented by Upstash. The local
client follows that documented optimistic pattern; no Free-plan command restriction
was identified. However, strict cross-session/failover reservation correctness is
**not certified**: the general provider contract documents eventual consistency and
does not clearly rule out the lost-history failure model relevant to this ledger.
This is a documentation/qualification gap, not an observed failure of Upstash Free.

No local Redis URL was configured. No real Upstash database, plan, hosted concurrency
test, Groq API call or LiveKit deployment was touched. No paid service or architecture
replacement was introduced. See the
[audit and free alternatives](../../../deployment/ZARA_UPSTASH_FREE_AUDIT.md).

## Reproduced failures before the fixes

The new adversarial test file initially produced **4 failed, 10 passed**:

- An orphan reservation became available immediately after its 180-second pending
  deadline, without preserving a complete subsequent token window.
- An incomplete stream could credit a parsed usage record and release budget early.
- URL query options could turn off TLS certificate/hostname verification.
- The existing preflight used one connection and did not demonstrate conflict abort.

The audit also identified that redis-py 6.4.0 can raise WatchError for a connection
failure while watching, in addition to genuine null-EXEC conflict replies. Treating
both as safe retry conditions could produce additional ghost reservations after an
uncertain commit. The patch stops admission on network-origin WatchError instead.

## Changes

`src/foodease_agent/groq_capacity.py` retains the same ledger schema, key namespace,
native Redis client, WATCH/GET/TIME/MULTI/SET/EXEC flow and Groq selection policy:

1. Charge unsettled/orphaned budgets through `max(at, pending_deadline)` when testing
   minute/day windows. A deadline's expiry does not immediately erase its token charge.
2. Keep unknown/interrupted responses pending; only clean completion can reconcile
   reported usage. Recognize SSE `[DONE]` because the native SDK stops consuming at
   that protocol terminator rather than necessarily requesting physical EOF.
3. Retry actual optimistic conflicts, but stop admission on a network-origin
   WatchError/unknown commit outcome. Do not refund an unacknowledged reservation.
4. Reject TLS verification query overrides rather than relying on secure defaults
   that URL arguments can override.
5. Exercise two independent clients in preflight: forced WATCH invalidation, fresh
   successful transactions, cross-client values, and competing quota reservations.
   Use only a random temporary probe key and clean it up. This is not a proof of
   server behavior during a later failover.

`deployment/cloud.py` now labels the stronger preflight accurately and explicitly
states its limits. The setup guide corrects the earlier suggestion that choosing a
primary endpoint alone establishes strong consistency. It does not require paid
ACLs or introduce a billing upgrade.

No new dependency, prompt, cart/tool implementation, STT/TTS setting, provider,
Cloud secret, deployment or quota-sharing authorization was changed. Conservative
holds may reduce capacity after uncertain failures; they do not grant extra quota.

## Executed verification

Commands ran in `C:\HCI-PROJECT\voice-agent` using its existing `.venv` Python.
Async tests ran with approved elevated execution because Windows sandbox socketpair
restrictions prevent the default event loop from starting. All provider traffic and
Redis failures were mocked; a local mock Redis TCP server exercised redis-py's actual
wire/connection path in the existing capacity tests.

| Command/check | Observed result |
| --- | --- |
| Initial `pytest tests/test_groq_capacity_coordination.py -q` | 4 failed / 10 passed; failures reproduced above |
| Capacity + coordination after initial fixes | 37 passed |
| `pytest tests/test_groq_capacity_coordination.py tests/test_groq_capacity.py tests/test_config.py tests/test_integrated_recovery.py tests/test_cloud_startup.py -q` | 86 passed before adding the final post-response DB-failure test |
| Final `pytest -q` | **514 passed / 1 inherited failure**, 35.44 seconds |
| Scoped Ruff: capacity runtime, both capacity test files, deployment helper | Passed |
| Scoped Pyright: capacity runtime and both capacity test files | 0 errors / 0 warnings |
| `git diff --check` | Passed |
| `python deployment/cloud.py check-capacity` from the repo root | Correctly stopped: local `GROQ_CAPACITY_REDIS_URL` is unset; no endpoint was contacted |

Final captured pytest summary:

```text
FAILED tests/test_no_mock_leak.py::test_no_mock_imports_outside_adapters - As...
1 failed, 514 passed in 35.44s
```

The inherited failure still flags the pre-existing mock import in
`src/foodease_agent/integration/scenarios.py`. That source was not changed. This is
not reported as an entirely passing repository suite.

The **17 new coordination cases** include a forced same-snapshot conflict with a
verified re-read, replacement-worker overlap, database connection/timeout/quota/OOM/
corrupt-state refusals, commit-ack loss, cancellation after commit, network-wrapped
WatchError, orphan aging, interrupted usage, TLS override rejection, a working
two-client preflight and rejection of an endpoint that ignores WATCH, and settlement
failure after a successful provider response without replaying that response.

One of those cases deliberately simulates acknowledged state being rolled back,
then observes over-admission. Its passing assertion documents the remaining
storage-contract limitation; it is **not** a passing safety property or proof of an
actual Upstash defect. Basic TCP/transaction checks cannot detect all future lost
history or certify global linearizability.

## Remaining qualification / decision

The detailed audit cites Upstash's native WATCH, transaction locking, consistency,
TLS and Free pricing contracts. It provides a precise provider-confirmation question
and two genuinely free alternatives: a proposed Cloudflare Workers Free SQLite
Durable Object coordinator, or Redis/Valkey on already-owned always-on hardware
with durable storage and secure TLS access. Neither was implemented. Redis Cloud
Free is not advertised as a durable substitute because its Free plan disables
persistence. Keep the existing LiveKit deployment until the datastore choice and
required consistency guarantee are resolved.
