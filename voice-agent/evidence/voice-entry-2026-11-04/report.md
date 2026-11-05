# Voice entry and website integration follow-up

Date: 4 November 2026. Scope: the explicitly requested integrated website voice
experience, using the existing provider/LiveKit stack and real website authority.

The detailed changes, environment variable **names only**, actual test results,
known legacy failures, screenshots and live setup steps are recorded in
[the voice integration handoff](../../../website/docs/VOICE_INTEGRATION_2026-11-04.md).

The expanded deterministic opening tests first reproduced unsupported phrases;
the final opening suite passed 21 cases. Lifecycle tests first reproduced blocked
cleanup retry and missing microphone feedback; the final JavaScript suite passed
49 cases, including cancellation during a cleanup retry. Nine new Chromium
entry/control scenarios passed against the local offline fixture. The focused
integrated worker suite passed 102 cases; changed Python source/tests passed Ruff
and scoped pyright with zero errors/warnings.

Full worker suite: 377 passed, one inherited mock-boundary failure in the unchanged
legacy integration scenario runner. Orchestration: 53 passed, three acceptance
generator failures caused by the pre-existing deleted website requirements file.
Website Python tests: 41 passed. The complete Chromium suite passed 80 scenarios.
Build and syntax checks passed. Eleven source/public asset pairs match. The
visual audit checked 15 surfaces and 201 text-color pairs with zero failures,
overflow or page/console errors. The welcome fits the checked mobile viewport.

No private environment files were inspected or changed, and no paid provider, Cloud
dispatch, physical microphone test or human listening test was run. No live gate
was closed. No push or deployment occurred.
