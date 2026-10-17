# Final orchestration Phase 4 verification

Date: 17 October 2026. Branch: `codex/phase-4-live-conversation-runtime`.

Phase 4 attaches the integrated streaming conversation/action runtime to the
actual bound worker entrypoint. It adds all thirteen tools, current-context
reasoning, deterministic controls, per-turn admission, owned pending actions,
read-only reconciliation, delivered checkout consent and finite idle scheduling.
The real website remains the shopping authority. No UI/browser implementation
or later-phase opening conversation was added.

**IMPLEMENTATION GATE: PASS for Phase 4's scoped offline checks.**

**ACTIVATION GATE: not passed or claimed.** Browser SDK wiring and actual rendering
remain Phase 5; the opening voice/manual choice remains Phase 6. No paid provider,
Cloud room, microphone, audible playback, human listening score, production
deployment or measured voice latency is established by these tests.

## Repeatable command and results

From `orchestration/`:

```powershell
.venv\Scripts\python.exe tools\phase4_verify.py --output evidence\final\phase-04\run-2
```

The final [run summary](run-2/summary.json) records every command and exit code;
adjacent raw logs provide the results. Dotenv is disabled and provider credentials
are removed from child environments. Historical handover evidence and frozen v1
files are restored after the legacy tests' known write side effects.

| Check | Final result |
|---|---|
| Worker runtime, production RPC adapter, actual entrypoint, startup and RTC bridge | 46 passed |
| Scoped runtime/adapter/worker/test lint | Pass |
| Scoped runtime/adapter/worker/test types | 0 errors, 0 warnings |
| Website regression suite | 38 passed; one existing Starlette/httpx warning |
| Orchestration regression suite | 36 passed; one existing Starlette/httpx warning |
| Website and orchestration lint | Pass |
| Website/shared-contract and orchestration types | 0 errors, 0 warnings |
| JavaScript session/lifecycle regressions | 18 passed |
| Frozen v2 model/schema/example/handoff check | Pass |
| Frozen v1 preservation | 92 files checked; zero drift |
| Phase 4 verifier lint | Pass |
| Complete agent suite | 310 passed; the one inherited mock-boundary failure |
| Complete agent lint | 39 inherited issues |
| Complete agent types | 27 inherited errors, 2 warnings |

The agent-wide failures match the Phase 3 baseline. The existing failure is
`tests/test_no_mock_leak.py::test_no_mock_imports_outside_adapters`, caused by the
unchanged `integration/scenarios.py` MockAdapter import. The scoped changed paths
have no lint/type errors. The verifier treats an unexpected failure or changed
baseline count as failure rather than calling the whole repository green.

## Gate evidence

- **Actual streaming path:** a real LiveKit `AgentSession` uses a local fake LLM
  stream, executes the real SDK tool wrapper against website SessionStore, resumes
  the model with its result and produces assistant text. Current bounded context
  reaches both initial reasoning and the tool continuation. No RulePlanner or
  DialogueSuitePlanner drives integrated conversation.
- **All thirteen operations:** the actual SDK agent exposes thirteen tools. Tests
  exercise every operation, normalize/preserve/clear filters, inspect factual
  search/details output, and compare cart quantities/subtotal/fees/total to the
  real seed domain. Cart narration contains authoritative quantities and total.
- **Production adapter:** a fake bound RTC seat routes the actual v2 RPC adapter
  into real SessionStore/domain execution. Context pushes, lost replies, original
  result lookup, wrong senders and uncorrelated results are exercised. Lookup
  reconciles an accepted mutation without submitting it again.
- **Actual worker wiring:** the real entrypoint/factory prepares providers through
  a test seam, forces preemptive generation off and starts only after authorized
  ready acknowledgement. Room I/O links the bound user; native text is disabled.
  Unselected mode is silent. Bound controls select the mode and a user disconnect
  immediately disables local media/admission.
- **Turn safety:** actual user-turn callbacks bind generated speech to exact turn
  identities. Uncommitted, discarded, old, interrupted and stale-context tools
  cannot mutate. Two scheduling-race tests revoke the lane between admission and
  transport entry and prove zero submissions and zero abandoned pending records.
- **Cancellation safety:** pending actions exist before send. Cancelling a tool's
  caller and selecting manual preserves the already-entered mutation. Shutdown
  drains accepted action ownership and records its terminal result; it does not
  roll back or speak a late result under a newer/manual lane.
- **Checkout safety:** interrupted/error/queued/no-audio summaries followed by
  casual yes submit nothing. Corrections and cart changes invalidate consent.
  Exact rendered typed summary consent submits once; missing/mismatched receipts
  cannot authorize. Tokens stay out of model tool facts. User speech lifecycle
  retains only a summary whose delivery was already completed.
- **Controls and context:** stop interrupts audio without a model generation;
  pause/resume, repeat, manual, typing, speed, truthful device-volume guidance,
  actual back and actual undo are exercised. Manual context clears obsolete
  references/repeat text, updates orientation and interrupts outdated speech.
  Ambiguous references and invalid quantities send nothing.
- **Idle and output:** at most two idle tips, none before selection, during speech,
  in manual mode or after disconnect. Pause-tips is deterministic. The output gate
  preserves streaming tool chunks, sanitizes speech and rejects tested common
  outcome claims without matching current successful action witnesses. This is
  not a general semantic verifier of every possible model utterance.

## Test-first and review record

The first new runtime test collection failed with the expected
`ModuleNotFoundError: No module named 'foodease_agent.integrated'` before the
runtime implementation was added. Early iterations corrected fixture expectations
for persistent filters, actual website service fees and source/mode authorization.
An actual SDK streaming test also caught misplaced test-tail code, which was moved
back to its intended typed-summary test before the focused suite passed.

The initial broad [run](run-1/summary.json) retained its intermediate results:
scoped checks passed, full lint detected two newly added unformatted race-test
lines, and frozen v1 had zero drift. Those lines were formatted. Final run-2 then
passed every scoped check and matched all inherited baseline failures. No
implementation changed after run-2; only documentation was completed.

## Remaining integration boundary

See [runtime and transport handoff](../../../docs/PHASE_04_LIVE_CONVERSATION_RUNTIME.md)
for exact RPC and delivery receipt requirements. Phase 5 must implement app/user
seats, action forwarding/render ordering, canonical typed/controls, assistant
output and typed summary post-render receipts. Phase 6 owns the initial mode-choice
conversation. The existing page is not a completed live voice-ordering flow yet.

Action/result ownership remains process-local and bounded. A worker/process kill
cannot provide durable reconciliation; terminal application records remain the
authority. Provider speech quality, actual browser playback and humanized spoken
behavior require later direct live verification.
