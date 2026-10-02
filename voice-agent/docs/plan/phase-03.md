## Phase 3 — Adapter interface and mock app (Size M)

**Goal:** a deterministic fake application so every later phase is testable without the website.

**Tasks**

- **3.1 [AGENT]** `adapters/base.py`: async `AppAdapter` with `get_snapshot()`, `submit_action(request) -> ActionResult` (per-operation timeout), and subscriptions for context updates, control events and typed text input. Voice code imports only this interface.
- **3.2 [AGENT]** `MockAdapter` (in-process): ~28 fictional PKR menu items (burgers, wraps, rolls, desserts, drinks, a few karahi/biryani-style dishes) with tags (spicy, vegetarian), availability flags, and descriptive attributes. **Include traps:** near-duplicate names (two "Zinger" items), two items matching "the wrap", prices like 150 vs 1,500, an out-of-stock item, an item with no ingredient data (to test "I don't have that information"), and an item description containing an injection string. A page model (home, category, item, cart, checkout summary, order confirmation) with a back stack, cart with fees/total, and a `revision` that increments on every state change.
- **3.3 [AGENT]** Scenario controller: per-action outcomes success, failed, rejected(reason), stale_context, requires_confirmation, delayed(ms), never_reply (→ `timeout_unknown`); plus `simulate_gui_navigation(page)` and `simulate_cart_change()` (T09, T13).
- **3.4 [AGENT]** `tests/adapter_conformance/`: suite parametrized by adapter (idempotency, revision monotonicity, stale handling, result correlation, timeout behavior). Any future adapter, including the website's, runs the same suite.

**Strict guidelines**

- The voice code must not assume anything the contract does not promise.
- Mock data is fictional, in `tests/fixtures/`. Deterministic by default; randomness only behind an explicit seed.

**Verification**

| ID | Check | Pass condition |
|---|---|---|
| V3.1 | Unit tests: totals, quantity edits, remove, fees, rounding | Pass |
| V3.2 | Duplicate `action_id` returns prior outcome, no second mutation | Pass |
| V3.3 | Each scenario mode yields a contract-valid result | Pass |
| V3.4 | Conformance suite on `MockAdapter` | 100% |
| V3.5 | Nothing outside `adapters/` imports `mock` | Pass |

**Gate:** V3.1–V3.5.

---

