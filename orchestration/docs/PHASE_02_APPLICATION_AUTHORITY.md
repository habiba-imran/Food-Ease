# Final orchestration Phase 2: application authority

Implemented on `phase-2-application-authority`. This phase establishes the real
website's session and operation boundary. It does not connect the voice worker.
The spoken mode chooser, LiveKit role binding, app-seat RPC and UI synchronization
remain later phases. Existing mock guidance remains a mock.

## Source of truth

- `website/src/foodease_website/sessions.py`: ownership, lifetime, admission,
  serialized execution, transaction commit, idempotency and read-only lookup.
- `website/src/foodease_website/domain.py`: the single business implementation for
  catalog queries, navigation, cart arithmetic and confirmed demo orders.
- `contracts/src/foodease_contract/`: shared, pure contract 2.0 models. The agent's
  `foodease_agent.contract.v2` paths remain compatibility imports. Original v1
  models and both frozen v1 artifact trees are unchanged.
- `website/static/js/app.js`: manual requests attach their shopping session and
  submit the summary revision with checkout approval. No visual redesign.

The website installs only the local shared package and its Pydantic dependency;
it does not install the voice stack. Run `uv sync --locked` in `website/` and
`voice-agent/` after pulling these changes. Both lockfiles include the sibling
editable `../contracts` dependency; retain that directory when copying the repo.

## Ownership and API

An anonymous owner is established by the website root or session creation. Its
opaque random cookie is HttpOnly, SameSite Strict, and Secure on HTTPS. An opaque
session ID is a handle, not authorization: every context, attachment, action and
lookup also verifies the server's owner association. Cross-origin POSTs with a
foreign Origin are rejected. Shopping responses carry `Cache-Control: no-store`.
There is no end-user login or LiveKit participant authentication in this phase.

| Endpoint | Shape and behavior |
|---|---|
| `POST /api/v2/app/sessions` | `{}`; creates a shopping session and owner cookie if needed; 201 |
| `POST /api/v2/app/sessions/attach` | `{session_id}`; reattaches only for its current owner |
| `GET /api/v2/app/context` | Contract 2.0 `ContextSnapshot` |
| `POST /api/v2/app/action` | Full `agent.action_request` 2.0 envelope; returns `app.action_result` |
| `GET /api/v2/app/actions/{action_id}` | Contract 2.0 `LookupResponse`; optional `X-FoodEase-Event-Id` is echoed as `reply_to` |
| `GET /api/app/context` | Manual client facade; same 2.0 snapshot |
| `POST /api/app/action` | Strict `action_id`, `operation`, `arguments`, `context_revision`; returns the result payload |

Send `X-FoodEase-Session` plus the same-origin owner cookie. For older manual
clients only, omission of the header selects one owner-scoped default session;
it never selects a global cart. The v2 endpoints require an explicit handle.
Manual and v2 actions call the exact same `SessionStore.submit` method. The future
app-seat forwarder must use this boundary and must not create its own cart.

Bodies are bounded to 14 KiB and validated before domain execution. Malformed
JSON returns 400; invalid/extra fields, unsupported versions and incorrect types
return 422; missing ownership returns 401; wrong owner/session or foreign Origin
returns 403; expired attachments return 410; capacity returns 429. No provider
exception details are returned. Rejected business actions return typed results.

## Revisions, duplicates and commits

All 13 operations have strict allowlisted arguments. Prices and totals always
come from the server catalog. Cart arithmetic uses Decimal before conversion to
the wire's validated money fields. Quantities above 99, including accumulated
adds, are rejected rather than silently clamped.

Each session serializes execution using its own lock. An action works on a copy
of the domain. The result, correlation and complete new snapshot must validate
before the new domain, revision and terminal result are committed together.
An exception or invalid output leaves the original state untouched and stores a
safe failed result. These transactions cover this local in-memory domain only;
they do not provide rollback for future external business effects.

Every request needs an integer expected context revision. Consequential operations
require exact equality. Read operations may use an older revision; future
revisions are always refused. Failed/rejected actions do not bump the domain
revision. Cart revision is separate and changes with cart edits/undo/submission.

Idempotency is `(session_id, action_id)` with a fingerprint of operation and
normalized arguments. The same request returns its original terminal envelope,
including its original event IDs, turn ID, timestamp and revision. A changed
operation/argument set returns `idempotency_conflict` and cannot overwrite the
original record. Retransmit the original envelope when retrying the same action;
use lookup to reconcile a new transport attempt. Never treat an old cached
context result as a fresh snapshot; fetch current context separately.

Pending records are reserved before execution. Lookup can observe them without
waiting for the action lock. A duplicate wait exceeding five seconds returns a
transient `timeout_unknown`; it does not cancel the action or overwrite its
eventual result. Lookup never executes an action, bumps a revision or extends
idle lifetime. It reports `not_seen`, `pending`, `found` or `expired`; a found
receipt remains the original receipt after cart clearing or later cart changes.

## Checkout and navigation

`checkout.get_summary` issues a random, five-minute token bound to this session's
cart revision and exact server summary. A new summary replaces the prior token.
Submit requires all of `confirmed: true`, `confirmation_token`, `summary_revision`
and a current context revision. Wrong, expired, cross-session and consumed tokens
are refused. Cart edits and undo invalidate approval. Navigation changes context
revision but preserve cart approval. Refresh context before submitting.

A successful submit consumes approval, stores an authoritative simulated receipt,
clears the cart and undo history, and selects the confirmation route. Replaying
the same action returns that receipt; it cannot create another order or clear a
subsequent cart. There is no payment or real order provider.

Back restores a bounded history of actual view states rather than jumping home.
Search/filter/navigation clear stale item focus; category and budget are included
in context. Search/filter result lists are capped at 25 with an honest total
`result_count`; cart and receipt data are not silently truncated.

## Lifetime and operational limits

Defaults are 128 shopping sessions, 256 accepted action IDs per session, up to
256 anonymous owners, 30-minute shopping idle TTL, two-hour absolute TTL and
64 entries each for back/undo histories. Owner authorization also has a two-hour
absolute lifetime from owner creation. A shopping session cannot outlive its
owner. Limits are constructor parameters for tests/server configuration.

Accepted results are retained for the entire valid session. Reaching action
capacity refuses new IDs with 429; it does not evict a receipt and permit a
duplicate mutation. Expired inactive records are reclaimed on admission. Pending
work is not discarded during cleanup. Read-only status polling does not keep
sessions alive.

State is in one process. Run one website worker. Restart, expiry or switching to
another worker loses attachment and result availability. Report this as expired
or HTTP 410; never infer that an earlier uncertain order did not happen. Durable
storage and multiple-worker coordination are not implemented.

The browser stores its handle in sessionStorage, reattaches after reload and uses
one startup promise for concurrent requests. Fresh tab storage creates independent
sessions. Browser tab duplication can copy sessionStorage and intentionally attach
the same handle; create a fresh session for an independent cart. Blocked storage
uses an in-memory attachment and cannot promise reload continuity. An expired
attachment clears the saved handle and reports loss of state; it does not replace
a cart or retry a mutation automatically. Reload then starts a new session.

## Verification and phase boundary

From `orchestration/`:

```powershell
.venv\Scripts\python.exe tools\phase2_verify.py
```

The verifier runs website/API/concurrency/expiry/rollback tests, frozen contract
checks, shared-model lint/types, JavaScript transport tests, orchestration tests,
full legacy agent regression and disposable localhost manual/v2 HTTP flows. It
disables dotenv/providers and restores historical test-generated evidence. Use
an unused localhost port 18080; the verifier refuses an existing server.

See [Phase 2 report](../evidence/final/phase-02/report.md). Phase 1 fixtures are
hash-pinned historical captures; current conformance is tested at the real API.
Browser rendering, microphone, speech quality, Cloud/WebRTC and automatic mode
choice have no new live evidence. Phase 3 is not started.
