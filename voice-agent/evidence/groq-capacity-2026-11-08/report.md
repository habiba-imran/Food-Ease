# Proactive Groq capacity management — 2026-11-08

Implemented locally and verified with mocked provider traffic. **The new worker has
not been deployed:** the deployment preflight stopped because shared Redis has not
been configured. The user requested a setup guide and will configure Redis later.

## Implementation

- `src/foodease_agent/groq_capacity.py`: conservative token estimator, primary-first
  admission, shared organization pools, atomic Redis ledger, local-only SQLite,
  rolling TPM/RPM/RPD/TPD and optional ITPM/OTPM guards, header/reset observations,
  pending reservations, usage settlement, bounded HTTP rejection recovery and SSE
  observation without changing the streamed bytes.
- `src/foodease_agent/groq_llm.py`: native LiveKit Groq plugin with one reused HTTP
  connection pool; disables both SDK retry layers. Only an HTTP 429 received before
  streaming can move to the next authorized independent pool. The transport does
  not run tools, replace chat history or reconstruct a LiveKit session.
- Configuration accepts all four Groq key slots, deduplicates identical credentials,
  excludes Groq credentials and Redis URLs from representations, and requires an
  explicit approval flag for independent organization labels. Default pool labels
  share one allowance. No credentials were added, printed or committed.
- The existing nonfatal localized recovery keeps assistance active, revokes the
  failed reply and warns callers to check their cart before repeating an order.
  English and Urdu recovery both preserve an actual website-authority cart mutation
  exactly once in regression tests.
- Docker prefetches the tokenizer vocabulary at build time. Locked dependencies
  add redis 6.4.0 and tiktoken 0.14.0; fakeredis 2.40.0 is development-only.
- `deployment/cloud.py` checks a TLS shared ledger before changing the existing
  Cloud deployment, uploads configured key slots/capacity settings securely, and
  adds `check-capacity`. Redis connection errors and deployment output are sanitized.

## Prediction and admission calculation

```text
raw = token_count_o200k_base(JSON(messages, tools, response_format))
framing = 64 + 12 * message_count
predicted_input = ceil((raw + framing) * safety_factor) + safety_tokens
reservation = predicted_input + output_token_cap
```

Defaults: safety factor 1.2, safety tokens 128, output cap 1,024. A caller-supplied
output cap takes precedence; otherwise the default is added to the outgoing request.
That cap includes reasoning tokens and is a new, configurable bound. The model,
Groq plugin's existing reasoning setting, prompts, tools, STT and TTS remain intact.

For each organization, compare the new reservation with rolling completed usage
and outstanding reservations. Check configured minute/day request and token caps,
learned lower TPM/RPD ceilings, unexpired response-header headroom and Retry-After
cooldowns. Pending budgets are charged atomically before the HTTP request. Actual
input/output usage replaces predictions on completion; missing usage or interrupted
streams retain their full predicted charge. Header ceilings are conservative and
never inflated by an out-of-order live snapshot. Reset expiry does not bypass the
independent rolling guards. Cold/stale organizations admit at most one observation
request in flight, within configured budgets.

Redis transactions use Redis server time and WATCH/MULTI/EXEC. All workers share
one model-specific ledger and the same organization labels. Transactions have a
1.5-second total deadline; socket operations have 0.5-second timeouts, without
Redis connection retries. A failed reservation blocks the request. Ledger storage
contains counters, nonsecret pool labels and random reservation IDs, not prompts,
tool arguments, cart state or API keys. Local SQLite is cross-process on one host
and is never a Cloud fallback.

An offline native serialization of the **static Urdu policy and actual tools**
produced an input reservation of 4,282 tokens, or 5,306 including the output cap.
This excludes dynamic application context and conversation history and is not a
measurement of actual provider usage or latency. Large later requests must fit one
account individually; capacity from several accounts cannot split one completion.

## Executed validation

All commands below used `voice-agent/.venv/Scripts/python.exe` with no real Groq
traffic. Windows sandbox socketpair restrictions required elevated async test
execution; after an initial approval-review usage-limit error, the user requested
continuation and the subsequent review/test runs succeeded.

| Check | Observed result |
| --- | --- |
| `pytest tests/test_groq_capacity.py -q` | **23 passed** |
| Capacity/config/session/recovery/environment focused suite | **88 passed** before the final two capacity tests were added; those two passed in the capacity and final full runs |
| Final `pytest -q` | **497 passed, 1 inherited failure** in 49.40 seconds |
| Scoped Ruff over changed Python files and deployment helper | Passed |
| Scoped Pyright over changed runtime and capacity tests | 0 errors, 0 warnings |
| `git diff --check` | Passed |
| Offline native serialization of Urdu policy/tools | Ran against mocked HTTP only; estimates above |

The inherited full-suite failure is
`tests/test_no_mock_leak.py::test_no_mock_imports_outside_adapters`, which flags the
pre-existing mock import in `src/foodease_agent/integration/scenarios.py`. That file
was not changed. This is not reported as a fully passing repository suite.

Capacity tests include adequate primary capacity, insufficient predicted tokens,
ordered fallback to the next key, simultaneous workers, shared-organization quota
deduplication, reset/cooldown behavior, unavailable pools, daily/request limits,
usage reconciliation, stale/unknown observations, streamed Groq usage, partial
stream failure without retries, Redis outages, credential/configuration controls,
and native LiveKit streamed history preservation after a rejected HTTP request.
One HTTP test seeds low primary headroom and observes **only Key 2 receiving a
request**, without a preceding primary request or HTTP 429.

Two separate production redis-py clients were also exercised against an isolated
local **mock Redis TCP server**, including real Redis wire protocol, connection
setup and atomic transactions. Simultaneous reservations admitted exactly one
request against one pool's remaining allowance. This is not a test of the user's
future managed Redis service or a multi-host Cloud deployment.

## Deployment outcome

Both commands were attempted:

```text
python deployment/cloud.py check-capacity
python deployment/cloud.py deploy
```

Both stopped before a Cloud change with:

```text
Set GROQ_CAPACITY_REDIS_URL (rediss://) before Cloud deployment
```

Authenticated current Cloud status was inspected and saved to
`deployment/evidence/capacity-cloud-status.txt`. Existing agent `CA_gibAwTdK3sjn`,
dispatch `foodease`, version `ckhnpPJ2Lg5h` remains deployed in `ap-south` and was
**Sleeping** at inspection. No new version or provider secret update was made.

The Docker engine was initially stopped and was started in the background for
image validation. `docker build -f Dockerfile -t foodease-zara-capacity:local .`
then failed resolving `registry-1.docker.io` while fetching the Dockerfile frontend.
The new production image build is therefore **unverified**, not passed. No Cloud
build, live Urdu call, live quota switching, or caller-heard latency measurement
was performed. No account was deliberately exhausted.

## Configuration handoff

Follow [Redis setup and Cloud rollout](../../../deployment/ZARA_REDIS_CAPACITY_SETUP.md).
Configure local `voice-agent/.env` with the TLS Redis URL, secondary keys, stable
organization labels and the approval flag; verify all applicable account/model
limits, then run `check-capacity` and `deploy`. The deployment helper uploads the
configured `GROQ_API_KEY` / `_2` / `_3` / `_4`, `GROQ_CAPACITY_REDIS_URL`, pool and
approval settings and optional prediction/limit knobs as Cloud secrets. Existing
provider/backend secrets remain necessary. No new Vercel changes are required.

The user reported Groq email approval for the separate accounts. The implementation
enforces an explicit configuration gate but does not independently authenticate
that email or its scope. Groq organization quotas, provider reset decisions and
contractual limits remain authoritative. External use of the same accounts,
tokenizer differences and stale provider observations can still cause a 429.
See [Groq rate limits](https://console.groq.com/docs/rate-limits),
[Groq project limits](https://console.groq.com/docs/projects), and the setup guide's
official Redis and LiveKit references.
