# Menu-list question correction — 2026-11-07

**Superseded implementation:** The later [Urdu/semantic follow-up](../urdu-2026-11-07/report.md)
removes this report's shopping keyword parser. The results below document the
initial repair; current free-form menu interpretation uses the LLM/tool path.

The reported requests, “list all the items below 1000” and “list items on the
juice menu”, previously fell through to model generation. The integrated policy
also limited lists to three options and treated under-budget requests as inclusive.
The catalog has a drinks category, with Mango Juice as a product rather than a
separate juice category.

Clear price/category list requests now use the existing revision-aware broker and
website filter/search operations directly. Facts and prices come from correlated
successful application results. This path does not call the LLM and therefore
does not depend on model capacity for these requests. Juice/juices searches the
actual menu. Named categories come from application navigation targets.

Explicit list/read requests deliver every returned match with prices. Ordinary
show requests retain short lists and next/previous navigation. Below/under/less
than exclude the requested price; up to/within/at most include it. Spoken prices,
comma-separated numbers and currency labels are supported. Dietary tags remain;
an explicitly new category/search clears conflicting text, and “all items” clears
the previous category/search. Other price-only refinements retain category/search.
Negation, compound actions, unsupported units and ambiguous amounts retain the
model path. The model policy also describes the corrected listing/budget behavior.

The existing 25-row contract bound remains. When result_count exceeds the
returned rows, speech explicitly says more matches exist and asks for a narrower
query; it never calls that partial list complete. For the current catalog, the
below-1,000 query returns all 25 matching products. The juice query returns Mango
Juice at 200 rupees. Full-list captions preserve all delivered names.

## Verification

From `voice-agent/`:

```text
.venv/Scripts/python.exe -m pytest tests/test_integrated_menu_queries.py tests/test_integrated_conversation.py tests/test_integrated_runtime.py tests/test_integrated_output.py tests/test_integrated_recovery.py tests/test_phase4_engine.py tests/test_phase4_acceptance.py tests/test_phase6_dialogue.py -q
128 passed in 13.03s

.venv/Scripts/python.exe -m ruff check src/foodease_agent/integrated/menu_queries.py src/foodease_agent/integrated/runtime.py src/foodease_agent/integrated/agent.py tests/test_integrated_menu_queries.py
All checks passed!

.venv/Scripts/python.exe -m pyright src/foodease_agent/integrated/menu_queries.py src/foodease_agent/integrated/runtime.py src/foodease_agent/integrated/agent.py tests/test_integrated_menu_queries.py
0 errors, 0 warnings, 0 informations

git diff --check
Passed (only existing LF/CRLF notices).
```

The first baseline run outside the sandbox failed both audio/text budget cases
because they entered model generation. Initial sandboxed asyncio runs stalled
while creating Windows' local socket pair; those owned runs were interrupted.
Offline tests then ran with the required local-socket access. No provider calls
were made.

The new regression file covers both input sources, actual catalog names/prices,
strict/inclusive price boundaries, spoken amounts, category/search transitions,
empty results, failed actions, stale/mode guards, stop during an outstanding
request, delivered-item references, pagination and complete captions. Existing
cart, confirmation, recovery, safety and dialogue checks also passed.

No running worker was restarted, and no push or deployment was performed.
The active worker must reload this source before a new voice session uses it.
Live microphone/STT/TTS and caller-heard behavior were not evaluated in this
follow-up. Pre-existing workspace changes were preserved.
