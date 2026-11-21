# Interactive Urdu website actions: verification

21 November 2026. See [implementation and supported commands](../../../website/docs/ZARA_INTERACTIVE_URDU_2026-11-21.md).

New domain tests were run before implementation: four failed for missing clear operations,
missing stock recheck and retained conflicting search. All four passed after implementation.
New Urdu runtime tests use scripted tool decisions with the real website SessionStore.
They cover later/delivered confirmation, purpose separation, manual cart invalidation,
Roman Urdu delivered-list references and unverified speech claims.

Final commands/results:

| Command (from indicated package) | Result |
| --- | --- |
| `python -m pytest website/tests -q` (root; worker venv) | 49 passed |
| `npm test` (website) | 63 passed |
| `python -m pytest -q` (voice-agent) | 525 passed, one inherited mock-import failure |
| `python -m pytest tests/test_interactive_urdu.py tests/test_zara_followup.py -q` | 29 passed after final navigation speech adjustment |
| `npm run test:browser -- interactive-urdu.spec.mjs voice-entry.spec.mjs lifecycle-edge-cases.spec.mjs footer-cart.spec.mjs menu.spec.mjs` | 39 existing regressions and Urdu clear passed; two new assertions initially used the wrong catalog label, corrected afterward |
| Changed production modules: `ruff check`, `pyright` | Passed; 0 type errors/warnings |
| `npm run build`; `node --check` on changed JS modules | Passed |
| `python tools/freeze_contract_v2.py`; contract tests | Generated both matching trees; pinned historical examples/v1 preserved |

Final browser verification:

- `npm run test:browser -- interactive-urdu.spec.mjs`: **3 passed** (16.6 seconds).
  Desktop 1440px and mobile 390px exercise category navigation despite prior search,
  cheapest available recommendations, Roman Urdu ordinal addition, quantity change,
  real cart opening/closing and removal. The third case covers a manual addition,
  current Urdu cart summary and later confirmation of the clear review.
- `manual-ordering.spec.mjs`: **12 passed**, including desktop/tablet/mobile checkout,
  keyboard-only ordering, focus restoration, double-submit guards and failed checkout.
- Combined with the 39 existing voice/menu/lifecycle/cart cases: **54 distinct
  browser tests passed** across the scoped runs. The initial new-scenario failures
  were corrected: exact existing product labels, then reopening the compact typing
  panel after closing the cart. The final three-scenario run passed completely.

Sandbox-only attempts stalled during Python/local-fixture access. The local loopback
verification was rerun with approved process access; six identified stale pytest processes
were stopped. Existing browser suites overwrite historical screenshots; those were restored
to their original repository bytes. No historical screenshot is presented as new evidence.

One added navigation alias initially appeared in the spoken category list and triggered
the Urdu fallback. It is now excluded from categories; the focused and full final worker
runs pass that regression. Remaining inherited failure:
`tests/test_no_mock_leak.py::test_no_mock_imports_outside_adapters`, unchanged
`src/foodease_agent/integration/scenarios.py`.

No live provider, Cloud room/conversation, deployment or listener test was performed.
Scripted semantic decisions do not demonstrate natural-language model/STT accuracy.
