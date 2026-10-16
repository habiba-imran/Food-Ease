# Final orchestration Phase 2 verification

Date: 17 October 2026. Branch: `phase-2-application-authority`.
Scope: session-scoped application authority only. Phase 3 is not started.

The website now uses bounded owner-scoped shopping sessions and one validated
operation service for manual requests and the agent-facing v2 HTTP boundary.
Actions execute on a candidate domain under a per-session lock; state, revision
and terminal result commit only after schema/correlation validation. Checkout
approval is random, time-limited, single-use and bound to the session, cart
revision and exact server summary. Receipts survive cart clearing in the session
result store. Status lookup is read-only and cannot resubmit an action.

Canonical pure v2 types moved into the sibling `foodease-contract` package with
the agent's existing import paths preserved. Both package lockfiles contain the
local dependency. Original v1 models and both frozen v1 trees remain unchanged.
The Phase 1 corpus is hash-pinned historical data; actual Phase 2 conformance is
tested against current domain execution through the API and localhost HTTP.

## Implementation gate

**IMPLEMENTATION GATE: PASS for the scoped Phase 2 checks below.** Existing
repository-wide failures remain separately recorded and are not waived.

The initial test-first check failed at collection because the session authority
module did not yet exist. Subsequent checks exercised the implemented service.
The final repeatable run is `run-2/`; `run-1/` records the earlier verification
before final review added invalid-ID/overflow and mid-session expiry checks.

Command from `orchestration/`:

```powershell
.venv\Scripts\python.exe tools\phase2_verify.py --output evidence/final/phase-02/run-2
```

| Check | Final result |
|---|---|
| Website suite, including actual TestClient API and threaded authority tests | 38 passed; one inherited Starlette/httpx deprecation warning |
| Frozen v1/v2 contract suites | 77 passed |
| Contract regeneration, both handoff trees and pinned historical samples | Pass |
| Website/shared-contract lint | Pass |
| Changed agent contract/exporter lint | Pass |
| Website/shared-contract type check | 0 errors, 0 warnings |
| JavaScript syntax | Pass |
| JavaScript request transport with simulated fetch/storage | 6 passed |
| Existing orchestration suite | 19 passed; one inherited Starlette/httpx warning |
| Phase 2 verification-tool lint | Pass |
| Disposable localhost manual flow | Pass: authoritative totals, summary-bound checkout and duplicate receipt |
| Disposable localhost v2 flow | Pass: all 13 operations, separate owners, attachment and receipt reconciliation |
| Frozen v1 preservation | 92 files match Phase 1 hashes |

See [run summary](run-2/summary.json), individual `.log` files and the redacted
[v2 HTTP trace](run-2/v2-http-smoke.json). The tests establish these boundaries:

- Independent owners and independent sessions under one owner do not share cart,
  context, approval, receipts or action records. Reload attachment keeps state
  only for the owning browser cookie. Foreign owners and Origins are refused.
- All operations validate strict argument types before business execution;
  malformed JSON, extra fields, unsupported versions, oversized bodies, unknown
  IDs, unavailable items and cart overflow cannot partially mutate state.
- Twelve competing requests at the same revision commit one action and refuse
  eleven as stale. Concurrent identical IDs execute once. Changed arguments
  conflict without overwriting the original terminal outcome.
- Consequential actions require exact expected revision. Reads may be old but
  cannot claim a future revision. Context includes category/budget; back restores
  actual view history; selection does not linger after changing the view.
- Missing/wrong/cross-session/expired/consumed approval or an edited cart cannot
  submit. Navigation preserves approval. One confirmed submit produces one
  receipt, clears cart/undo, and cannot erase a later cart on replay.
- Exceptions, incorrect totals, wrong action correlation and invalid context
  abort the candidate transaction and retain a safe failed result.
- Lookup reports not_seen, pending, found and expired without execution,
  revision changes or idle-TTL extension. A transient duplicate timeout does not
  replace the eventual committed result. Capacity refuses new IDs rather than
  evicting results. Idle/absolute expiry and restart do not fabricate recovery.
- Manual transport carries the tab's session handle, reattaches on reload,
  creates only one session for concurrent startup requests, and reports expiry
  without silently creating a new cart or automatically retrying a write.

## Existing repository failures

Full checks were rerun and remain separate from the focused implementation gate:

| Existing agent check | Result |
|---|---|
| Full pytest | 267 passed, 1 existing failure: `test_no_mock_imports_outside_adapters`, caused by `integration/scenarios.py` importing MockAdapter |
| Full lint | 39 existing issues |
| Full pyright | 27 existing errors, 2 warnings |

These match the Phase 1 baseline and were not changed or waived. The verifier
preserves old phase-9/10 test-generated evidence and frozen v1 artifacts in a
`finally` block. The historical Phase 0 gate remains open for its recorded
repository failures and missing browser walkthrough.

## Activation gate and limitations

**ACTIVATION GATE: not run or passed; live voice integration remains later work.**

No Cloud, worker, microphone, live audio, paid provider or real order service was
started. HTTP traces establish a running local server; JavaScript tests use
simulated fetch/storage and do not establish actual browser rendering or audio.
No live activation or conversational-quality gate is passed by this phase.

State is bounded, in memory and single-process. Defaults: 128 sessions, 256 action
IDs per session, 30-minute idle lifetime, two-hour absolute owner/session lifetime,
five-minute approval lifetime and 64-entry back/undo histories. Restart or expiry
makes prior outcome availability unknown; it does not prove that no order happened.
Duplicated browser tabs can copy sessionStorage and attach the same session;
fresh tab storage or explicit session creation is required for an independent
cart. Storage-blocked browsers cannot promise reload continuity.

Changes to JavaScript are confined to session request transport, summary revision
and honest expiry status. No templates, visual styling, animation, voice prompts,
worker tools, assistance lifecycle or LiveKit role/RPC wiring were changed.
Existing dirty work from Phases 0/1 remains in place. No commit, push or deployment
was performed.

See [authority API and operational details](../../../docs/PHASE_02_APPLICATION_AUTHORITY.md).
Stop after Phase 2; obtain Habiba's next instruction before Phase 3.
