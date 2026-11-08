# Actual Redis connectivity diagnosis — 2026-11-09

## Outcome

**The actual `deployment/cloud.py check-capacity` command now passes against the
existing configured Upstash database.** No database recreation, credential change,
TLS bypass, system DNS change or LiveKit deployment was performed. Only disposable,
randomly named preflight keys were written and cleaned up.

## Root cause and evidence

The Redis URL was read privately from `voice-agent/.env`. It has one assignment,
uses `rediss://` on port 6379, contains credentials, has a syntactically valid
Upstash hostname and no whitespace, fragment, placeholder hostname or TLS query
override. No endpoint, IP address belonging to that endpoint, password or URL is
included in this report. The actual successful connection validates the endpoint
and credentials more strongly than syntax checks alone.

| Actual network test | Observed result |
| --- | --- |
| Cloudflare 1.1.1.1: configured endpoint | DNS SERVFAIL, zero answers |
| Google 8.8.8.8: configured endpoint | DNS SERVFAIL, zero answers |
| System getaddrinfo | Windows 11002/11001 name-resolution failure |
| TCP/TLS/Redis attempts through failing system DNS | Blocked at name resolution; TLS/authentication were not reached |
| Both resolvers: google.com and upstash.com controls | Answers received |
| upstash.io zone, unrelated public qstash.upstash.io and livekit.io | Also SERVFAIL on the failing resolver path |
| DNS-over-TCP to 1.1.1.1 and 8.8.8.8 | Same configured-endpoint SERVFAIL |
| OpenDNS 208.67.222.222 | Configured-endpoint SERVFAIL |
| Quad9 9.9.9.9, ordinary query with checking enabled | NOERROR and usable A/CNAME answers |
| Quad9 answer: real TCP port 6379 | Passed; one diagnostic sample took 187 ms |
| Same endpoint: real TLS with original hostname/SNI | TLS 1.3 passed, certificate chain and hostname verified |
| Same endpoint: real AUTH and PING | Passed |

Diagnostic-only queries with the DNS checking-disabled bit also returned answers
through the otherwise failing resolvers. This suggests a validation-dependent
resolver/path problem, but does not identify the exact upstream DNSSEC/forwarder/ISP
fault. The permanent fix **does not set that bit or disable DNSSEC checking**. Ordinary
Quad9 queries were sufficient. Verified HTTPS DNS attempts to Google/Cloudflare
also timed out or failed from this machine, including public controls, so they did
not provide an independent external-network verdict.

The evidence identifies the immediate failure precisely: the configured/system
resolver path returns DNS RCODE 2 before any Redis connection. It is not evidence
of invalid credentials, a bad Redis URL, Free-plan transaction rejection or an
unavailable Redis server. The working resolver plus real authenticated TLS proves
the endpoint was reachable. Upstash's [official status page](https://status.upstash.com/)
reported systems operational; that is supporting context, not proof of the DNS
incident's global scope. Further attribution of why those resolver paths failed
would require another network or resolver/operator diagnostics.

An attempted read-only browser-console inspection was stopped by the computer-use
tool because it could not verify the current browser URL. No authentication UI,
credentials, browser protections or account settings were accessed or bypassed.
Subsequent work used the independently authorized network/CLI diagnostics only.

## Second issue: preflight deadline

With a temporary process-only resolution override, native authenticated Redis PING
worked with the original client timeouts. Two measured samples completed in
1,312 ms and 1,453 ms including cold connection/authentication/setup. First writes
on the two preflight clients took 1,344 ms and 1,312 ms; a later GET took 266 ms.
The old five-second outer deadline still terminated the sequential preflight before
all checks completed. The final successful command took 8.68 seconds end to end,
including Python startup/imports. These are diagnostic timings, not voice latency.

## Minimal local changes

- Added optional `GROQ_CAPACITY_DNS_SERVER`, validated as a literal resolver IP.
  It is blank by default. The private local `.env` now sets it to the working
  `9.9.9.9`. A before/after parse asserted that **every other environment value,
  including the Redis URL and all credentials, stayed unchanged**.
- Added a small Redis SSL connection subclass using dnspython's asynchronous resolver.
  It resolves only Redis, respects DNS TTLs, retains the original hostname for SNI
  and certificate verification, and never pins a database IP or changes global
  `getaddrinfo`, the Windows hosts file, or system DNS. A resolver failure fails closed.
- Certificate/hostname errors are never bypassed or retried against another identity.
  Alternative A records are only connection candidates before any Redis command.
- Increased bounded preflight time to 20 seconds; an individual ledger transaction
  is bounded at 3 seconds, socket connect/read at 2/1 seconds, with command retries
  still disabled. This permits cold authenticated connections and sequential checks.
- Added sanitized preflight stage/error-class reporting. No raw Redis URL, auth
  parameters, command arguments or credentials are logged.
- Added dnspython 2.9.2 to the locked Python dependencies and documented the optional
  setting. No architecture, quota reservations, cart tools or audio/provider behavior
  was replaced. All changes remain compatible with native TCP on the Free plan.

The Redis resolver selection is an explicit local setting, not an automatic bypass
of a failed quota ledger. There is still no uncoordinated in-memory Cloud fallback.

## Actual final verification

```text
voice-agent/.venv/Scripts/python.exe deployment/cloud.py check-capacity

Two-client Redis conflict/reservation checks passed; no Groq request was sent.
This does not certify provider failover durability or global consistency.
```

Observed exit code: **0**. This used the existing database, the original URL and
credentials, and the new app-only resolver setting, without a diagnostic monkeypatch.
Actual native TCP tests covered TLS/authentication, forced WATCH invalidation,
MULTI/EXEC conflict abortion, fresh transactions, cross-client reads, simultaneous
quota reservations and temporary-key cleanup. This is finite protocol evidence,
not a claim about global failover behavior; the earlier consistency audit remains
separate.

Automated validation:

| Check | Result |
| --- | --- |
| Redis DNS + capacity + coordination + env-example tests | **49 passed** |
| Full offline worker suite | **521 passed, one inherited failure**, 32.54 seconds |
| Scoped Ruff | Passed |
| Scoped Pyright | 0 errors, 0 warnings |
| `git diff --check` | Passed |

The inherited failure is `test_no_mock_leak.py`, which flags the existing mock
import in `integration/scenarios.py`; that source was not changed. New tests check
resolver validation, fail-closed DNS errors, retained hostname/SNI, certificate
verification, credential/pool preservation and rejection of plaintext transport.
No real Groq request or deliberate account exhaustion was performed.

## Manual action

No manual database or credential repair is needed for the local preflight. Restart
an already-running local worker when ready so it loads the code and new environment
setting. Existing LiveKit Cloud code/secrets were not updated. Remove the optional
resolver setting to return to system DNS after that network path is repaired; leave
it unset in environments whose DNS works. No paid feature or DNS-hosting service
was purchased or enabled.
