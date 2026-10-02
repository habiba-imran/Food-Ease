## Phase 2 — Contract v1.0, owned and frozen by you (Size M)

**Goal:** a versioned, machine-checkable contract based on the spec's names, usable by the agent now and by Zainab later. **No sign-off from anyone is required.**

**Tasks**

- **2.1 [AGENT]** JSON Schemas in `contract/v1/` for: the envelope (`schema_version`, `session_id`, `event_id`, `turn_id`, `timestamp`, `context_revision`, `type`, `payload`); every event in VA-11/VA-12; arguments of each of the 13 actions with constraints (item IDs match a pattern; quantity is an integer in a defined range); the context snapshot (VA-09 fields, with a **bounded** visible-items list and `valid_navigation_targets` including `back`/`home` when available, so "go back" is a semantic `navigate` target, not a click); action-result statuses `success`, `failed`, `rejected`, `stale_context`, `requires_confirmation`, `timeout_unknown`; user-safe error codes.
- **2.2 [AGENT]** Where the spec is silent, choose defaults and mark them `x-habiba-default` in the schema: transport mapping (agent→app actions via LiveKit RPC with the result as the RPC response; context updates/control/text input via RPC or a data topic; transcripts and agent state via LiveKit's native mechanisms, mirrored as envelope events), topic and method names, payload-size limits (check LiveKit's RPC limits), and an **optional** `confirmation_token` on `checkout.get_summary` results and `checkout.submit_demo_order` requests.
- **2.3 [AGENT]** Pydantic models are the single source for the schemas (or the reverse), with a CI drift check. Golden examples in `contract/v1/examples/`: add item, set quantity, stale context, rejected, requires_confirmation, timeout/unknown, duplicate `action_id`, checkout with and without token, reconnect with a fresh snapshot.
- **2.4 [AGENT]** `contract/v1/STATE_MACHINES.md`: (a) conversation lifecycle mapped from LiveKit states to the VA-07 product states; (b) action lifecycle (`created → submitted → success | failed | rejected | stale_context | requires_confirmation | timeout_unknown`).
- **2.5 [HUMAN]** Read the contract once against the spec; tag `contract-v1.0-frozen`. Later changes follow semver: additive/optional = minor, breaking = major.
- **2.6 [LATER] (optional, non-blocking)** If Zainab wants to review, send her `contract/v1/` when convenient. Her feedback becomes v1.1 via `LiveKitRpcAdapter` translation, not a rewrite.

**Strict guidelines**

- Every action request has a unique `action_id`; duplicates must be idempotent on the app side (the app returns the prior outcome). The agent also never reuses an `action_id` for a different request.
- Contract fields use the application's IDs, never label matching.
- Agent logic must work when the optional fields are absent.

**Verification**

| ID | Check | Pass condition |
|---|---|---|
| V2.1 | Schema lint + all golden examples validate | 100% |
| V2.2 | Negative tests: unknown operation, missing `action_id`, quantity 0 or 99999, wrong types | All rejected |
| V2.3 | Drift check (models ↔ schemas) in CI | Green |
| V2.4 | Every optional field has a golden example *without* it | Present |

**Gate:** V2.1–V2.4 and tag `contract-v1.0-frozen`.

---

