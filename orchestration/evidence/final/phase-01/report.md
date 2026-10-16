# Final orchestration Phase 1 report

Date: 17 October 2026. Branch: `phase-1-orchestration-contract`.
Repository base: `23e2b64`; existing Phase 0 working files were preserved.

**Phase 1 implementation gate: PASS for the versioned contract. Phase 2 has not
started. Live activation: NOT RUN.** No browser, room, worker or paid provider
was started. Phase 0's inherited agent failures and pending browser walkthrough
remain recorded; Habiba explicitly requested Phase 1 next.

## Delivered contract

- Separate contract **2.0** with canonical executable Pydantic models, strict
  event decoding/encoding, explicit website/legacy payload projections and
  generated JSON Schemas. This is a major version because mandatory revision,
  correlation and checkout token/summary requirements break v1 compatibility.
- Field-by-field source matrix covering lines/cart, line_total, complete filters,
  result details, routes, summary identities and typed demo receipts.
- All thirteen operation argument schemas and all thirteen existing event types.
  Strict quantities, finite PKR arithmetic, search/result bounds, explicit
  metadata, timezone-aware RFC3339 timestamps and a full UTF-8 byte budget.
- Request/result, embedded-context and lookup correlation guards; session/sender
  binding rules; exact stale/future revision policy and read exceptions; canonical
  intent fingerprints for future idempotency enforcement.
- Required current-summary confirmation fields, exact status/error behavior,
  worker-facing typed/control direction and transcript lifecycle identities.
- Read-only action-result lookup models, found/pending/not_seen/expired meanings,
  retention/expiry policy and reserved transport paths. No lookup endpoint/store
  was implemented or registered.
- Identical 79-file contract trees under voice-agent/contract/v2 and
  zainab-pack/contract/v2: 18 schema/config JSON files, 46 positive event examples,
  four lookup examples, nine negative fixtures, a manifest and contract README.
- Read-only drift verification, including a test that deliberately corrupts a
  temporary copy and proves detection. Ordinary tests check both generated trees.

Canonical documentation:
[contract/v2/README.md](../../../../voice-agent/contract/v2/README.md).
Integration pointer:
[Phase 1 freeze](../../../docs/PHASE_01_CONTRACT_FREEZE.md).

## Test-first and source evidence

Before implementation, `pytest tests/test_contract_v2.py -q` failed collection
with ModuleNotFoundError for foodease_agent.contract.v2. Tests were added before
the new models. They then reproduced the original real-website issues explicitly:

- Original ContextSnapshot rejects a nonempty website cart because of line_total.
- Original FilterMenuArgs rejects the live tool's category/vegetarian fields.
- Website emits lines while the old broker expects cart.

The same test suite now captures actual FoodEaseDomain outputs using the existing
catalog seed, projects them explicitly and validates all thirteen successful
operations with the new canonical contract. Empty and nonempty context validate.
Original code was not made to accept different values through relaxed v1 models.

Rejected, stale_context and requires_confirmation examples are real domain
results. Failed and timeout_unknown examples are explicitly synthetic transport
fixtures. Status/transcript/control examples are authored interface examples,
not evidence that a live session emitted them. Fixed fixture timestamps are not
latency measurements. Fixture-only removal of summary_revision for the current
legacy domain is documented and must not be used in production v2 execution.

## Verification

| Check | Result | Evidence |
|---|---|---|
| New v2 + unchanged v1 contract tests | **77 passed** (49 new + 28 original) | contract-tests.log |
| Canonical/model/fixture/handoff drift check | Pass | contract-drift.log |
| Focused Phase 1 lint | Pass | contract-lint.log |
| Focused Phase 1 typecheck | 0 errors, 0 warnings | contract-typecheck.log |
| Full agent regression | 267 passed, 1 inherited failure | agent-regression.log |
| Full agent lint | Same 39 inherited errors | agent-full-lint.log |
| Full agent typecheck | Same 27 inherited errors | agent-full-typecheck.log |
| Website regression | 10 passed, one inherited deprecation warning | website-regression.log |
| Orchestration regression | 19 passed, one inherited deprecation warning | orchestration-regression.log |
| Website's own Python/Pydantic compatibility | 46 event + 4 lookup examples validate | website-model-compatibility.json |

The independent website compatibility check used Python 3.11.14 and Pydantic
2.14.1, without installing dependencies or starting services. The primary suite
uses the agent environment and actual website domain source; neither uses
MockAdapter as a substitute for the website contract.

Negative checks include forbidden fields/operations, wrong quantity types,
missing/unsupported versions, missing revision/turn/action IDs, session/turn/
reply/action/operation mismatches, malformed filter tags and timestamps,
nonfinite/incorrect cart totals, missing checkout binding, non-demo receipts,
oversized UTF-8 messages, false successful state on timeout and unresolved
lookup outcomes presented as found.

The original failure remains
`test_no_mock_imports_outside_adapters`: integration/scenarios.py imports the
mock outside adapters/. The existing test was not weakened. Lint/type errors
match the Phase 0 totals. Full repository health is therefore not green, despite
the Phase 1 contract gate passing.

Exact executed commands and exit codes are in verification.json. Existing
handover files regenerated by tests and both v1 trees were preserved during
verification; preservation.json records SHA-256 values and any restored side
effects. Git scope checks show no changes to original v1 schemas/models/enums,
website source/static/templates, agent.py, broker.py or worker.py.

## Phase 1 gate mapping

| Planned gate | Result |
|---|---|
| Real-domain fixtures: empty/nonempty carts, every operation/status | Pass, with transport-only statuses explicitly synthetic |
| Negative fixtures: fields, identities, malformed arguments, versions | Pass; JSON Schema shape checks plus executable cross-message guards |
| Reproduce legacy mismatches then validate the agreed representation | Pass; regression assertions keep the original failures visible |
| Detect canonical/schema/handoff regeneration drift | Pass; both generated trees and a negative drift test |

Standard JSON Schema does not enforce all cross-field/cross-message arithmetic,
correlation and authorization invariants. The executable guards and migration
document explicitly identify those additional obligations. Publishing schemas
is not a claim that the current app already enforces them.

## Scope boundary and next phase

Only new contract modules/tests/export tooling, generated v2 artifacts and
documentation were added in this phase. ADR-0013 explains versioning; STATUS.md
and the orchestration freeze pointer record the result. Original v1 stays usable
and unchanged. No new application dependency or lockfile change was introduced
in Phase 1.

Actual per-session authority, atomic idempotency, token creation/consumption,
action-result storage/lookup and runtime validation belong to Phase 2. The worker,
browser transport, rendering and spoken mode chooser remain later work.
No teammate signoff, release tag, live behavior, deployment or conversational
quality is claimed. Stop here until Habiba requests the next phase.
