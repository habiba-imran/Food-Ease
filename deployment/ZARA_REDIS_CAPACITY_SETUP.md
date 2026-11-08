# Zara: shared Redis capacity setup and Cloud rollout

> **2026-11-09 correction:** Do not interpret this original guide as certification
> of Upstash Free's cross-session/failover guarantees. Native TCP supports WATCH,
> but the documented general consistency model needs qualification for this ledger.
> Read the [Upstash Free audit](ZARA_UPSTASH_FREE_AUDIT.md) before provisioning or
> deploying. No paid feature is required by the audit; no alternative architecture
> has been installed.

The code is implemented locally. **Do these steps before deploying it.** The
deployment preflight refuses to replace the current Cloud worker without a working
shared Redis connection. No Redis service or paid plan has been provisioned.

## 1. Create your Redis database

Use a Redis service with native TLS TCP and verified authoritative transaction and
durability guarantees. For the $0-only requirement, consult the audit above rather
than upgrading a plan. A REST-only URL is not compatible with this implementation.

1. Create a dedicated database named, for example, `foodease-zara-capacity`.
2. Choose a primary region close to the existing LiveKit worker in Mumbai (`ap-south`).
3. Enable persistence/durability and disable key eviction (`noeviction`, or the
   provider's equivalent). The ledger is accounting state, not a disposable cache.
4. Use the same verified authoritative endpoint for all workers. A setting named
   primary/single-region is not by itself proof of strong consistency. Do not use
   independent regional replicas for reservations.
5. Enable TLS, retain certificate verification, and copy the **Redis connection URL**.
   It has the shape `rediss://USERNAME:PASSWORD@HOST:PORT/0`. Use the provider-generated
   URL so special characters in credentials are encoded correctly.
6. Permit your computer and LiveKit Cloud to reach that TLS endpoint using the
   provider's supported network controls. Do not disable authentication or TLS.

The Redis user needs `WATCH`, `GET`, `TIME`, `MULTI`, `SET`, `EXEC`, `UNWATCH`, and
`DEL` for the configured namespace, plus connection handshake commands required by
redis-py. A custom ACL is not required; do not buy Upstash's paid ACL feature for
this setup. All replicas and overlapping rolling deployments must use the **same
database, namespace, pool labels and model limits**. Do not flush this database or
change organization labels to reset usage. A lost ledger loses recent accounting;
after restoring an empty store, allow the relevant provider quota windows to pass
or seed verified usage before resuming traffic.

See [Redis connection URLs](https://redis.io/docs/latest/develop/clients/connection-urls/),
[atomic transactions](https://redis.readthedocs.io/en/stable/advanced_features.html#pipelines),
and [eviction policy](https://redis.io/docs/latest/develop/reference/eviction/).

## 2. Configure your private local environment

Edit `C:\HCI-PROJECT\voice-agent\.env` locally. Do not paste the values into chat or
commit this file. Keep the existing LiveKit, STT, TTS and personality settings.

```ini
GROQ_API_KEY=YOUR_PRIMARY_KEY
GROQ_API_KEY_2=YOUR_SECOND_KEY
GROQ_API_KEY_3=YOUR_THIRD_KEY
GROQ_API_KEY_4=YOUR_FOURTH_KEY

GROQ_CAPACITY_REDIS_URL=rediss://USERNAME:PASSWORD@HOST:PORT/0
# Optional: use only if this environment's system DNS fails and this resolver was verified.
# GROQ_CAPACITY_DNS_SERVER=9.9.9.9
GROQ_CAPACITY_NAMESPACE=foodease:groq:v1

# You reported that Groq approved these four separate accounts by email.
# These labels represent those organizations; they are not credentials.
GROQ_CAPACITY_POOLS=account1,account2,account3,account4
GROQ_CAPACITY_INDEPENDENT_APPROVED=true

GROQ_CAPACITY_OUTPUT_TOKENS=1024
GROQ_CAPACITY_SAFETY_FACTOR=1.2
GROQ_CAPACITY_SAFETY_TOKENS=128

# Verify these against all four accounts' actual limits for GROQ_MODEL.
# These are conservative defaults, not a claim about your approved allocation.
# Set the LOWEST applicable account limit, even if another account has more.
GROQ_CAPACITY_TPM=8000
GROQ_CAPACITY_RPM=30
GROQ_CAPACITY_RPD=1000
GROQ_CAPACITY_TPD=200000

# Set these if Groq applies separate input/output per-minute limits.
# Leave 0 only if that separate limit does not apply to these accounts.
GROQ_CAPACITY_ITPM=0
GROQ_CAPACITY_OTPM=0
GROQ_CAPACITY_STALE_SECONDS=60
```

Unused secondary keys can be left blank; missing slots are skipped. If two keys
belong to the same Groq organization, give them the **same pool label**. If independent
usage is no longer approved, remove that configuration and use the default
`shared,shared,shared,shared` with `INDEPENDENT_APPROVED=false`. Duplicate key values
are deduplicated. No key values, transcripts, tool arguments or cart contents are
stored in Redis.

Check each organization's exact limits on the
[Groq Limits page](https://console.groq.com/settings/limits). Groq's response
`remaining-requests` header means **requests per day**, not RPM. Separate rolling
RPM and daily-token guards therefore use the configured limits. The response
TPM/RPD ceilings can lower the configured ceilings; they never increase them.
See [Groq limits](https://console.groq.com/docs/rate-limits) and
[organization/project limits](https://console.groq.com/docs/projects).

## 3. Verify dependencies and Redis, without spending Groq tokens

Open PowerShell:

```powershell
Set-Location C:\HCI-PROJECT\voice-agent
uv sync --locked
Set-Location C:\HCI-PROJECT
.\voice-agent\.venv\Scripts\python.exe .\deployment\cloud.py check-capacity
```

Expected result:

```text
Two-client Redis conflict/reservation checks passed; no Groq request was sent.
This does not certify provider failover durability or global consistency.
```

The check uses two connections and an isolated temporary Redis key to force a
WATCH conflict, verify fresh commits and test competing reservations, then cleans up.
Passing it is a protocol check, not a proof of the provider's failure guarantees.

If system DNS returns SERVFAIL but an independent resolver returns a valid answer,
`GROQ_CAPACITY_DNS_SERVER` can select that resolver **only for Redis**. It accepts
a literal resolver IP, follows DNS TTLs and preserves the configured Redis hostname
for TLS SNI/certificate verification. It does not pin a database IP, change system
DNS, disable certificate checks or disable DNSSEC checking. Remove this optional
setting to return to system DNS. Keep it unset where system DNS works normally.

Preflight permits up to 20 seconds for all sequential/cold-connection checks; an
individual ledger transaction remains bounded at 3 seconds. Socket connect/read
timeouts are 2/1 seconds with no automatic Redis command retry. Failed preflight
now includes a sanitized stage/error class without exposing a connection string.
It does not consume model capacity, alter carts, dispatch a voice session or modify
the current Cloud worker. If it fails, check that you copied a `rediss://` connection
URL rather than an `https://` REST URL, and verify credentials, region and network access.

## 4. Deploy the existing agent

After the preflight passes:

```powershell
Set-Location C:\HCI-PROJECT
.\voice-agent\.venv\Scripts\python.exe .\deployment\cloud.py deploy
.\voice-agent\.venv\Scripts\python.exe .\deployment\cloud.py status
.\voice-agent\.venv\Scripts\python.exe .\deployment\cloud.py logs
```

`deploy` repeats the Redis check before uploading. It reuses agent
`CA_gibAwTdK3sjn`, dispatch name `foodease`, and the monorepo Docker build. It sends
configured provider/capacity values through a temporary secrets file outside the
build context, redacts output, and removes that file afterward. It does not create
a second agent. Do not use `--overwrite`: unrelated Cloud secrets must survive.

The production image preloads the tokenizer vocabulary, so token estimation does
not download a tokenizer during a caller's request. The native Groq connection pool,
LiveKit room and STT/TTS clients survive credential selection.

If setting secrets manually, use LiveKit's dashboard/secure secrets file workflow.
Do not put secret values in shell command arguments. Required new Cloud settings:

| Variable | Required? |
| --- | --- |
| `GROQ_API_KEY` | Yes, existing primary key; also used by Urdu STT |
| `GROQ_API_KEY_2`, `_3`, `_4` | Each secondary key you want available |
| `GROQ_CAPACITY_REDIS_URL` | Yes, shared TLS Redis URL |
| `GROQ_CAPACITY_POOLS` | Required for approved independent account capacity |
| `GROQ_CAPACITY_INDEPENDENT_APPROVED` | `true` only with the applicable Groq approval |
| Other `GROQ_CAPACITY_*` values above | Defaults exist; explicitly set verified limits |

`GROQ_CAPACITY_SQLITE_PATH` is local-development-only and is not uploaded. Keep the
existing provider keys, model/language/voice values, and `FOODEASE_SESSION_API`.
LiveKit injects its own Cloud connection credentials; this script does not upload
local LiveKit API credentials as application secrets.

## 5. Check the first real session

Confirm Cloud reports the new version as Running, then use the actual configured
FoodEase backend and frontend for a short Urdu conversation. Verify a cart addition
once, then read its contents and quantity. Do not deliberately exhaust any account.
Mocked tests establish switching and reservation logic, not live Urdu audio quality
or latency. If a turn is refused, Zara keeps assistance active and says:

> فی الحال جواب دینے میں رکاوٹ ہے۔ آرڈر دوبارہ کہنے سے پہلے اپنی ٹوکری دیکھ لیں۔

Check the cart before requesting a mutation again. Existing confirmation, action IDs
and application authority still govern all cart operations.

## Capacity behavior and limits

- Before every chat HTTP request, estimate the serialized system/history/user/tool
  payload with `o200k_base`, add framing, apply a 20% margin and 128 safety tokens.
  Reserve that input estimate plus an output cap (default 1,024 tokens, including
  reasoning). An explicit caller-supplied output cap is honored instead.
- Select the first organization with adequate rolling token/request capacity and
  response-header headroom. Primary wins whenever it has capacity. A cold/stale
  organization gets at most one observation request in flight.
- Responses update header ceilings and actual usage, including streamed `x_groq.usage`.
  Pending requests remain reserved. Missing usage and interrupted streams retain their
  predicted charge. Out-of-order headers cannot inflate a live remaining ceiling.
- HTTP 429 before streaming can move to the next approved independent pool, once
  per pool. The rejected pool honors `Retry-After` and available reset headers.
  Neither SDK retries partial streams or re-executes a cart action.
- Redis failure blocks new model requests; there is no per-worker fallback in Cloud.
  Local development without Redis uses SQLite shared only on that machine.
- No separate quota-check HTTP call is made to Groq before each request. Capacity is
  a conservative prediction from configured limits, the shared ledger and the latest
  response headers. Unknown external usage, tokenizer differences and provider-side
  changes can still produce 429s. Route all uses of these model quotas through the
  same ledger, or reduce the configured limits to reserve external headroom.
- A single request's input and output reservation must fit one account. Separate
  account capacity cannot be combined to split an oversized completion.
- Groq organization limits remain authoritative; extra keys in one organization do
  not add quota. Your reported email approval is the basis for enabling independent
  accounts; this implementation does not independently verify that email's scope.
- No Vercel code or environment change is required for this backend-only feature.
  The previously required hosted backend callback and frontend gateway setup remain
  separate prerequisites for end-to-end Cloud voice ordering.

LiveKit reference: [secrets management](https://docs.livekit.io/deploy/agents/secrets/)
and [deployment management](https://docs.livekit.io/deploy/agents/managing-deployments/).
