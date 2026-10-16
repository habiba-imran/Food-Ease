# Final orchestration Phase 0 report

Date: 17 October 2026. Branch: `phase-0-orchestration-baseline`.
Baseline commit: `23e2b64` (`Add website and update project code`).

**Scope delivered:** reproducible package setup, baseline tooling/evidence,
installed SDK/API inventory and complete requirements mapping. **Phase 1 has not
started.** No application, conversation policy, UI, contract or schema logic was
changed. The implementation plan was already present before this phase.

**Gate status: OPEN / baseline characterized.** Setup and offline verification
are repeatable; existing agent checks fail and an actual browser walkthrough
could not be performed because the browser connector had no available browsers.
The HTTP order smoke is not substituted for browser acceptance.

## Changes made

1. Added website/uv.lock and installed its declared dependencies in website/.venv
   with the existing Python 3.11 pin. Added orchestration/.python-version = 3.12
   to make its existing runtime selection explicit. Existing Habiba lockfiles
   were preserved; dependency requirements were not loosened or upgraded.
2. Converted voice-agent/README.md from UTF-16LE without BOM to UTF-8 without BOM.
   uv_build rejected the previous encoding. Strict decode/re-encode round-trip
   and decoded-text comparison confirmed content preservation.
3. Added tools/phase0_baseline.py: per-package test/lint, agent typecheck,
   JavaScript syntax, installed versions/API signatures and map validation.
   It returns failure when any check fails, disables dotenv/provider credentials,
   forces model-cache offline mode and restores historical acceptance artifacts.
4. Added tools/phase0_website_smoke.py: loopback-only actual HTTP application
   smoke with a freshness guard against changing an existing cart. It exercises
   search/filter, item selection/details, cart correction, summary/confirmation
   and replay of the original submission. It labels browser/voice verification
   false.
5. Added requirements-map.md (102 rows), api-audit.md, raw logs/JSON and the
   Phase 0 runbook. Ignored the workspace-local .tools/ package cache.

## Environment diagnosis and setup

The earlier `No Python at ...` output did **not** mean the environments needed
rebuilding. Sandboxed execution could not access the uv-managed interpreter
directory. With appropriate execution access, both existing environments ran
Python 3.12.12. No existing virtual environment was deleted or recreated, and
no secret file was read or changed.

The actual setup defect was the agent README encoding: locked sync failed with
`stream did not contain valid UTF-8`. After encoding-only correction, locked
sync succeeded. Website setup resolved 33 packages and installed 32 distributions;
its lockfile is now part of the reproducible setup.

Final `uv sync --locked --offline --no-python-downloads` succeeded for all three
packages; see *-locked-setup.log. Comparing the old Git blob decoded as UTF-16LE
with the new UTF-8 README also passed. Existing source trees and both Habiba
lockfiles have no Git diff. The disposable website process was confirmed stopped.

| Package/tool | Observed version |
|---|---|
| Agent / orchestration Python | 3.12.12 |
| Website Python | 3.11.14 |
| uv / Node | 0.10.6 / v24.12.0 |
| livekit-agents / five voice plugins | 1.8.4 |
| livekit RTC Python / livekit-api | 1.1.20 / 1.2.1 |
| Harness JS reference | livekit-client 2.15.4 CDN; no website installation yet |

Exact distributions, source signatures and lock hashes are in both run
directories. api-audit.md records API compatibility findings, including the
existing unawaited set_attributes call and RPC exception-handling gap. Those
runtime issues were not fixed in Phase 0.

## Verification results

Both complete checks ran in new PowerShell processes after locked setup. The
second run includes the finalized HTTP smoke tool in orchestration lint.

| Check | Run 1 | Run 2 | Interpretation |
|---|---|---|---|
| Agent pytest | 218 passed, 1 failed | 218 passed, 1 failed | Same pre-existing architecture failure |
| Agent ruff | 39 errors | 39 errors | Existing source/test/tool lint debt |
| Agent pyright | 27 errors | 27 errors | Existing source/test type errors |
| Orchestration pytest | 19 passed | 19 passed | Fake dispatch/component tests, no Cloud |
| Orchestration ruff src/tests/tools | Pass | Pass | Includes new Phase 0 tools |
| Website pytest | 10 passed | 10 passed | App/domain/catalog component tests |
| Website ruff src/tests | Pass | Pass | No website runtime edits |
| Website JavaScript syntax | Pass | Pass | Syntax only, not DOM/runtime proof |
| Three environment inventories | Pass | Pass | Fresh interpreters and SDK signatures |
| Requirements map | 102 rows validated | 102 rows validated | WEB 22 + VA 17 + W 22 + T 20 + O 21 |
| Standalone HTTP order | Pass, separate localhost run | Not rerun on modified state | Real website authority, no browser/voice |
| Browser manual order | Unavailable | Pending | Connector browser inventory returned [] |

Website and orchestration tests each report one Starlette/httpx deprecation
warning. No dependency change hides that warning. Baseline failures remain
visible and cause a nonzero exit status.

Git whitespace checking flags the README's existing two-space Markdown hard
break on line 5, now exposed by conversion from a binary-classified encoding.
The byte-decoded content comparison confirms that this whitespace was inherited;
it was retained to keep the README conversion text-identical.

### Existing failures

- `tests/test_no_mock_leak.py::test_no_mock_imports_outside_adapters` fails because
  src/foodease_agent/integration/scenarios.py imports MockAdapter outside adapters/.
  That source is unchanged by Phase 0. See each voice-agent-tests.log.
- Agent lint reports 39 issues, including long lines, import ordering and unused
  imports across existing spikes, source, tools and tests. See voice-agent-lint.log.
  No bulk formatter, --fix, ignore-list change or test suppression was applied.
- Agent pyright reports 27 errors, including protocol-return annotations,
  unawaited set_attributes, SDK/config argument types and test fixture typing.
  See voice-agent-typecheck.log. No runtime workaround was added.

This full baseline supersedes the earlier selected 79-test observation. It does
not establish that the live worker is complete or active.

## Actual standalone website HTTP demonstration

Started only foodease_website.main on 127.0.0.1:18080, with dotenv disabled and
the mock-assistant feature flag false. No worker, session service, dispatch or
provider was started. Homepage and /healthz returned HTTP 200.

The smoke used the same /api/app/action operations the manual controls use:

- Empty-cart checkout refused.
- Menu navigation, vegetarian-under-800 filter, clear and wrap search.
- Hot Chicken Wrap selection/details, price PKR 850.
- Add quantity two: PKR 1,750 including PKR 50 fee.
- Set absolute quantity one: PKR 900.
- Retrieve summary and explicitly confirm using its returned token.
- Replay the same submission action ID: exactly the original result.
- Result: DEMO-0001, demo=true, order total PKR 900, route confirmation and empty
  final cart.

The fictional request/result/context trace is in website-http-smoke.json. The
disposable server was stopped. This is actual HTTP/domain evidence, not proof
that existing JavaScript renders every step correctly.

## Phase 0 gate checklist

| Gate item | Status | Evidence / outstanding item |
|---|---|---|
| Three interpreters usable in fresh shells | Pass with host access | Two inventories per package |
| Locked setup works | Pass | Three syncs; README fix; website lock |
| Baseline captured and repeatable | Pass as baseline record | Same inherited failures in run-1/run-2 |
| Baseline all green | Not passed | Agent test/lint/type failures above |
| SDK versions/relevant APIs audited | Pass, bounded audit | api-audit.md; uninspected JS details labeled pending |
| Requirement traceability complete | Pass | 102 rows checked against specs/plan |
| Website independently executes demo order | Pass at HTTP/application layer | website-http-smoke.json |
| Actual browser manual order | Pending | No browser surface; runbook walkthrough provided |
| No live/paid provider probe | Pass | Offline checks; only standalone website HTTP |

Do not mark the overall gate passed or advance to Phase 1. Capturing inherited
failures is the Phase 0 task; repairing voice runtime or changing architecture
and contract is outside this instruction. Browser acceptance also needs actual
observation before closure.

## Reproduction and evidence

See the [Phase 0 runbook](../../../docs/PHASE_00_BASELINE_RUNBOOK.md).

- run-1/summary.json and run-2/summary.json: commands, cwd, exit, duration and locks.
- run-1/*.log and run-2/*.log: full component check output.
- requirements-map.md and run-*/requirements-coverage.json: specification coverage.
- api-audit.md and *-inventory.log: installed APIs/versions and source audit.
- website-http-smoke.json: actual standalone website operation trace.

No claim is made about audio latency, microphone release, real-model dialogue,
screen-reader conformance, deployment or production readiness.
