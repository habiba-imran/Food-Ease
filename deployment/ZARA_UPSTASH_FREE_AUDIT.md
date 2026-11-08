# Zara / Upstash Redis Free audit — 2026-11-09

**Verdict: native TCP protocol compatibility is documented; the strict failure-safe
accounting guarantee is not verified.** Upstash's command documentation supports this
WATCH/CAS pattern, but its general consistency contract does not establish that
independent worker sessions always observe one authoritative history through replica
failures and partitions. Do not treat the existing setup guide, a passing preflight,
or the local mock tests as a production certification of Upstash Free.

No account, database, paid feature, Cloud secret, deployment, cart operation, model
provider or alternative coordinator was created or changed during this audit. The
existing Redis architecture remains in place. Local checks found no configured
`GROQ_CAPACITY_REDIS_URL`, so no actual Upstash endpoint or Free subscription was tested.

## What the current implementation requires

Each `RedisStore.transact` obtains a dedicated pipeline connection, watches a
model-specific key, reads its JSON ledger and Redis server time, computes a new
state in Python, then commits one `SET ... EX 172800` using `MULTI/EXEC`. A null EXEC
reply causes a fresh WATCH/read/compute attempt, bounded by 32 attempts and a
1.5-second overall deadline. A reservation is returned only after a successful
commit acknowledgment. Credentials and conversation/cart data are not stored.

| Component | Audit finding |
| --- | --- |
| Native TCP | Supported by Upstash; use its TLS Redis URL, not the REST endpoint. |
| WATCH | Explicitly documented as TCP-only. Another client's intervening modification must abort the watched transaction. |
| MULTI / EXEC | Upstash documents atomic execution under the keys' write locks at EXEC time. The client follows the documented optimistic transaction pattern. |
| Connection ownership | redis-py pins one connection for the WATCH/read/EXEC sequence. Separate workers have independent clients, but share the same ledger key. |
| TLS | `rediss://` is required in Cloud; locked redis-py 6.4.0 defaults to certificate and hostname verification. URL query overrides could disable these checks; the patch now rejects those overrides. Upstash says TLS is always enabled. |
| Conflict retries | Genuine null-EXEC conflicts are retried. redis-py can also wrap a connection failure in WatchError; that ambiguous outcome now stops admission rather than being retried as a known conflict. |
| Deployment overlap | Old/replacement client instances share the same key and reservations. Closing one client does not delete state. Keep model, namespace and organization labels stable across versions. |
| Database errors | Timeouts, connection loss, command-quota errors, OOM and malformed state block provider requests. No Cloud fallback to per-process memory or SQLite is introduced. |
| Preflight | Previously one temporary roundtrip. Now two independent clients, a deliberately invalidated WATCH transaction, positive-control fresh commits, cross-client reads, and competing quota reservations. Only temporary probe keys are modified. |

Sources: [Upstash WATCH](https://upstash.com/docs/redis/commands/transactions/watch),
[transaction locking](https://upstash.com/docs/redis/features/key-locking),
[native protocol compatibility](https://upstash.com/docs/redis/overall/compatibility),
and [TLS](https://upstash.com/docs/redis/features/security). The REST restriction on
WATCH is not a blocker for this native-TCP client.

## The precise consistency gap

[Upstash's consistency contract](https://upstash.com/docs/redis/features/consistency)
describes eventual consistency across replicas and causal guarantees within one TCP
session. It also says strong-consistency mode was deprecated. The dedicated WATCH
documentation gives the ordinary conflict-abort contract, which supports normal
optimistic transactions; the general contract does not clearly establish a
linearizable WATCH/read/EXEC history across independent sessions during failover,
or rule out rollback of acknowledged reservation data after a partition.

This is a **qualification gap**, not a claim that an Upstash Free concurrency bug
was observed. The actual endpoint has not been tested. Single-region selection,
TLS, a persistent TCP session, MULTI/EXEC, or a successful finite stress test cannot
by themselves establish an undocumented failure guarantee. Paid-plan selection
would not establish that guarantee either.

Why this matters for this ledger:

1. Worker A commits a reservation and starts a Groq request.
2. A server failover/rollback exposes the earlier ledger state to worker B.
3. B can pass WATCH/GET/MULTI/EXEC against that earlier state and reserve the same
   apparent headroom. There need not be an intervening write to invalidate B's WATCH.
4. TLS and a healthy connection cannot reveal A's lost acknowledged reservation.

An executable fault-model counterexample simulates that rollback and demonstrates
over-admission. It does not assert that Upstash actually performed it. The existing
client protocol cannot safely repair invisible lost history. A replacement using
Lua alone would also need a documented authoritative history/durability guarantee;
we did not silently make that architectural change or declare the issue solved.

Before qualifying Upstash for the strict requirement, obtain provider confirmation
covering **the Free plan's native endpoint**:

> Does WATCH → GET → MULTI/SET → EXEC on one key provide linearizable CAS across
> independent TCP sessions, including reconnects and primary failover? Can a
> successfully acknowledged EXEC reservation ever disappear or revert after replica
> promotion or a partition? Does the Free plan have the same guarantees? Please
> identify the documented guarantee rather than only command compatibility.

This question is supplied for the user; no email or support message was sent.

## Minimal local fixes, without changing architecture

- Retain orphaned pending budgets through their in-flight deadline **and a complete
  following quota window**, including the daily window. Previously an orphan could
  become available immediately when its pending deadline expired.
- Credit actual usage only when a response completes cleanly. A parsed usage record
  from an interrupted stream no longer releases predicted capacity. Native SSE
  `[DONE]` is recognized as completion because LiveKit need not consume physical EOF.
- Treat network-origin WatchError as an unknown transaction outcome. A failed or
  unacknowledged admission cannot trigger a Groq request; any durable charge remains.
- Reject Redis URL options that disable TLS certificate/hostname verification.
- Replace the one-client preflight with explicit conflict and reservation checks.
  Its output now explicitly states that it does not certify failover durability or
  global consistency.

Primary-first Groq selection, approved organization pools, token prediction, all
cart mutation guards, Urdu recovery, native LiveKit streaming, STT and TTS are kept.
No database migration, new dependency, service purchase or Cloud rollout is included.

## Staying within the actual $0 plan

The [official pricing page](https://upstash.com/pricing/redis) lists one Free database,
500,000 commands/month, 10 GB monthly bandwidth and approximately 250 MB storage
(the same page's comparison table also says 256 MB). Verify the console allocation;
do not rely on the larger inconsistent number. Stay explicitly on **Free**, not a
pay-as-you-go subscription with an assumed free allowance. The pricing FAQ says
entering a credit card upgrades the database to pay-as-you-go. No billing settings
were changed by this task.

Each successful ledger transaction normally sends six Redis commands: WATCH, GET,
TIME, MULTI, SET, EXEC. A normal successful LLM HTTP request performs three ledger
transactions: admission, response headers, and completion. That is **18 command
invocations before retries/connection setup**, not one per spoken turn. Tool-followup
LLM calls add their own transactions. Approximately 27,777 such LLM requests would
consume 500K commands if every one of those commands is counted; this is a planning
estimate, not a measured account bill or an allowance guarantee.

The entire JSON ledger is transferred on each transaction. Bandwidth can bind before
command count, and multiple apps sharing the Free database consume the same allocation.
Contention, quota refusals and preflights add traffic. Monitor the Free console's
command, bandwidth and storage usage. Keep eviction disabled. If the database refuses
commands at a limit, Zara blocks model admission and uses the existing graceful
recovery; it does not switch to an uncoordinated local ledger or purchase capacity.
An actually deleted/rolled-back ledger is a distinct correctness hazard as described
above, not an ordinary detectable network failure.

Custom ACLs are documented as paid-only; they are **not required or recommended as
a prerequisite** for this Free setup. Use the generated database password, TLS and
a dedicated database. No paid IP/network/availability feature is assumed.

## Genuinely free alternatives, proposed only

**Managed coordination alternative:** Cloudflare Workers Free with a SQLite-backed
Durable Object for each model's ledger. Its attached storage is documented as
transactional and strongly consistent. All LiveKit workers would call the same
authenticated HTTPS coordinator; Groq credentials, cart actions and audio stay in
the current worker. This is a proposal, not an implemented migration.

The [Free limits](https://developers.cloudflare.com/durable-objects/platform/pricing/)
include 100,000 requests/day, 13,000 GB-s/day, 5 million rows read/day, 100,000 rows
written/day and 5 GB total stored data. Free operations fail when limits are exceeded;
the proposed client must fail closed on those failures. It must use SQLite-backed
objects on the Workers **Free** plan; it must not enable a paid plan, paid KV-backed
objects or any automatic purchase. See the
[storage guarantee](https://developers.cloudflare.com/durable-objects/api/sqlite-storage-api/).
This would replace the Redis transport, so it requires an explicit architecture
choice before implementation. No Cloudflare resources were provisioned.

**If Redis itself is mandatory:** a single Redis/Valkey primary with durable storage
on an already-owned, always-on machine has no additional hosting subscription. Use
TLS, `noeviction` and fsynced AOF, and expose it securely to LiveKit. It retains the
current protocol but depends on that machine's power, network and disk; there is
no promise of zero electricity cost or managed uptime. Do not run independent
per-worker Redis instances. No machine or public endpoint was configured here.

Redis Cloud's 30 MB Free plan is **not presented as a drop-in durable solution**:
its [official persistence documentation](https://redis.io/docs/latest/operate/rc/databases/configuration/data-persistence/)
says Free plans disable persistence. Another free logo alone does not resolve this
ledger's failure requirements.

## Verification and remaining work

See [local test evidence](../voice-agent/evidence/upstash-free-2026-11-09/report.md)
for executed commands/results. Tests cover forced conflicts, overlapping workers,
commit-ack loss, cancellation, orphan aging, broken streams, database refusals,
TLS overrides and preflight rejection of an endpoint that ignores WATCH.

The original Cloud deployment and its secrets were left untouched. No actual
Upstash failover, cross-region load, Groq quota exhaustion, real audio test or billing
operation was performed. Upstash qualification or selection of the free alternative
is the remaining decision; no accuracy requirement has been waived.
