# ACCESSIBLE FOOD-ORDERING WEBSITE — UI/UX & FUNCTIONAL APPLICATION REQUIREMENTS

**Project:** Accessible Multimodal Food Ordering Website (working name: *FoodEase*)  
**Document owner / website:** Zainab  
**Voice-agent counterpart:** Habiba  
**Shared responsibility:** Final orchestration and end-to-end integration  
**Specification version:** 1.0 | **Date:** 01 October 2026  
**Document type:** Requirements, interfaces, acceptance criteria and final deliverables — **not an implementation plan**  
**Companion specification:** `Habiba_Voice_Agent_Requirements_Specification.md` (v1.0)

---

## 1. Purpose and product definition

Zainab's deliverable is a **complete, independently usable, accessible food-ordering web application**. A user must be able to explore food, search and filter the menu, inspect and customize an item, maintain a cart, review an order and complete a **simulated checkout** using the graphical interface **without** Habiba's voice agent connected. The same application must expose stable, semantic actions and authoritative context so Habiba's independently developed LiveKit agent can operate it later **without duplicating shopping logic or simulating mouse clicks**.

The HCI contribution is **choice of interaction and continuity between modes**: a person may browse with mouse, keyboard, assistive technology, typed conversation and—after integration—voice assistance. The primary intended persona is a blind or low-vision user, but disability disclosure must never be required. The voice agent is optional and **does not replace a fundamentally accessible website**.

**Non-negotiable invariants:**

1. **Manual mode is a full product, not a visual demo**; every core operation works without agent/LLM/STT/TTS/LiveKit availability.
2. Manual input and agent-requested actions call the **same application operations** and observe **one authoritative state** (selection, menu filters, cart, prices and order).
3. The application—not the LLM—resolves IDs, validates actions, calculates prices and totals, confirms stock/availability and decides whether a demo order succeeded.
4. The agent **requests** semantic actions; the app **executes or refuses** and returns a correlated result. The app never interprets free-form generated text as executable code.
5. Voice/text assistance requires user choice; denial/failure of microphone or voice provider cannot block manual ordering.
6. Zainab's project can be demonstrated against a **mock agent/event simulator** before Habiba's actual service is attached.

**Requirements notation:** **MUST** = acceptance condition; **SHOULD** = strong usability target; **STRETCH** = optional enhancement only after all MUST items pass.

---

## 2. Responsibilities and independence boundary

### 2.1 Zainab owns (MUST)

- The complete information architecture, UI/UX designs, interactive frontend and responsive visual presentation.
- A usable conventional flow: welcome/mode selection, home/categories, menu/discovery, item details/customization, cart, demo checkout, confirmation and useful error/empty states.
- Accessible semantics, keyboard behavior, focus management, readable text, feedback and meaningful error recovery.
- A single catalog/data model, product availability, deterministic search/filter logic, cart operations, quantity rules, total calculation, demo checkout and session state.
- An **application action interface** and an **application-context/event interface** matching Habiba's companion specification, testable with a mock agent.
- A safe way to connect the future agent session to the UI, plus a voice-panel UI and typed-input affordance; the real voice/STT/TTS engine is Habiba's responsibility.
- Optional database/persistence using Supabase **only if the product needs it**; the standalone manual experience must not depend on a paid service.
- Documented deliverables, accessible tests and reproducible traces of example agent actions.

### 2.2 Zainab does **not** own

- Habiba's LiveKit agent, conversational prompt/persona, Deepgram STT, Cartesia TTS, LLM choice, turn detection, audio streaming, proactive silence timing or real spoken-response synthesis.
- Reimplementing the agent's intent parsing in the website. The UI only needs to **display/forward typed user input** and **consume validated semantic actions/events**.
- Live payments, actual restaurant fulfilment, real customer accounts, production-scale inventory management, sensitive patient/identity records or a medical-booking workflow.
- A second cart or copy of business rules specific to voice mode.

### 2.3 Independent-completion rule

Before orchestration, Zainab must be able to disconnect all voice-related services, start the website, complete an entire demo order manually, and run an **internal mock-agent scenario** that exercises the agreed incoming action events. A simulated agent panel may be used **only as a development/test harness** and must never be represented to users as a real connected voice agent.

---

## 3. Interaction modes and onboarding requirements

### WEB-01 — Non-assumptive mode choice (MUST)

- Provide an approachable first-run choice between normal browsing and optional guided assistance; no question such as “Are you blind?” is required.
- Explain the choice in simple language. The standard website remains accessible in all modes.
- The user may continue manually if speech, microphone access or the future LiveKit room is unavailable.
- Do not activate the microphone, open a live voice session, play unsolicited audio or claim to be listening before **explicit opt-in** and required permissions.
- Provide an obvious way to enter, pause, resume or leave assistance; do not discard a confirmed cart when switching modes.
- Treat the assistant as a helpful alternative to manual browsing, **not** as a mandatory accessibility gateway.

### WEB-02 — Seamless mode continuity (MUST)

- A user may begin manually, switch to guided mode and return to manual mode **within the same shopping session**.
- All modes display/receive the latest selected item, filters, route, cart quantities and totals.
- If a manual action changes the visible page while the assistant is active, the context sent to the agent must change promptly; stale item details must not remain authoritative.
- Leaving voice mode prevents further unsolicited voice prompts but does not clear the menu, cart or demo-order history unless the user explicitly chooses a reset.
- If typed conversation is available, messages go via the companion contract's `app.text_input`; do not pretend typed text is a microphone transcript.

### WEB-03 — Orientation and task discoverability (MUST)

- A person should be able to determine the current page/section, active filters, selection, item count, cart count, price total and next available actions **without relying on visual position or color**.
- Route and section titles must describe the current location; provide a coherent way to return to the menu, home, previous context and cart.
- Show a manageable number of relevant options at a time; avoid overwhelming the user with a wall of information.
- Support meaningful empty, no-search-results, loading, unavailable-item and order-failure states with a clear recovery route.

---

## 4. Required UI/UX surfaces and functional behavior

These are **functional areas**, not prescribed colors, typography, themes, exact layouts or component designs. Zainab decides visual identity, spatial composition, illustrations, animations and specific control forms based on HCI rationale and accessibility testing.

| Area / screen | Minimum required functionality | Essential feedback and accessibility |
|---|---|---|
| **Welcome / mode selection** | Introduce the food-ordering service; manual browsing; explicit invitation to optional assistance. | Keyboard-operable choices, descriptive guidance, no automatic microphone activation. |
| **Home / category discovery** | Reach catalog sections, offers/featured items if present, search and cart. | Clear page/section headings, consistent navigation and category names. |
| **Menu listing** | Display real items with stable identifiers, names, images, prices, category and availability. | Useful item count, current filters, no-results recovery, descriptive alternatives for imagery. |
| **Search and filters** | Search by name/description; combine supported filters such as category, max price, vegetarian and spicy where catalog data supports them; clear/reset filters. | Announce/indicate changed result count and active criteria; keyboard operable. |
| **Item detail / customization** | Show factual price, description, ingredients/attributes when available, availability, quantity and meaningful choices/options if offered. | Current product identity remains clear; constraints and resulting cost are understandable. |
| **Cart** | Add, view, increment/decrement or set quantity, remove, recover from mistakes where safely reversible, compute price/fee summary. | After every action, show verified new quantity and total; accessible status message. |
| **Demo checkout** | Review cart and any fictional delivery/contact fields actually necessary for the demonstration; validate; obtain explicit confirmation of current order summary. | The user can edit before confirmation; no silent purchase from a casual “yes.” |
| **Demo confirmation / failure** | Display a simulated order outcome from the authoritative application, with a demo ID if successful. | Never suggest a real order/payment occurred; recover from submission failures/unknown result safely. |
| **Assistance panel** | Show future agent status, text/captions, optional text entry, user-facing start/pause/mute/end controls and connection errors. | Accessible labels/status; never obscure the main task or make the website unusable when disconnected. |
| **System states** | Loading, blocked action, failed search/action, offline/reconnecting as relevant, empty cart, unavailable product. | Clear language and next possible action; no inert controls or misleading success toasts. |

### WEB-04 — Fully functional manual shopping (MUST)

- Standard interactions must actually navigate or change shared state; no decorative controls that appear usable but do nothing.
- Search and filters act on the **same** catalog that the agent later queries. If a user searches “spicy under 1,000,” the result must come from implemented product attributes, not decorative/static cards.
- Price presentation uses a consistent currency (initial demo: **PKR**), quantity rules and subtotal/fee/total breakdown. Never use hidden hard-coded totals that conflict with cart contents.
- Prevent illegal quantities, selecting unavailable options and checkout with an empty or invalid cart.
- If item customization changes price or cart identity, show the outcome and preserve it in order summaries.
- Manual actions are reflected in the context/events available to the future agent, including navigation, selection, filtering, cart edits and checkout state.

### WEB-05 — Interaction polish (MUST, with visual freedom)

- Each interactive component has understandable default, pointer, focus, pressed/selected, disabled, pending and error behavior where applicable; the designer selects the exact aesthetic.
- Offer prompt visible feedback for action initiation and truthful confirmation after completion. A pending action must not look like completed success.
- State transitions should be coherent and not disorient the user; important information remains discoverable after UI changes.
- Provide recovery for accidental edits; destructive/irreversible transitions receive suitable confirmation when necessary.
- Layout adapts to ordinary phone and desktop widths, including zoom and enlarged text; no critical content is clipped by an assistant overlay.

---

## 5. Accessibility and measurable HCI requirements

**Target standard:** design and test against the applicable **WCAG 2.2 Level AA** success criteria; do not claim formal conformance solely because a library or automated checker was used. A human test with keyboard and a screen reader is required.

### WEB-06 — Accessible foundation (MUST)

- Use meaningful document/section headings, navigation landmarks, native controls where appropriate, correctly associated form labels and accessible names for icon-only actions.
- The entire manual order flow—including mode choice, menu, search, item configuration, cart, confirmation and exit from assistance—works **without a mouse**. Provide a visible keyboard-focus indicator and logical focus sequence.
- Support keyboard activation and standard input behavior; do not trap focus in an overlay. If a dialog is used, manage entry, focus containment where appropriate and return focus after closure.
- Meaningful product images have useful alternative text; decorative visuals do not produce redundant announcements. Essential distinctions cannot rely solely on color, position, sound or animation.
- Supply readable contrast, reasonable target sizes, reflow at increased zoom, adjustable or responsive text, and no inaccessible hover-only information. Respect reduced-motion preferences.
- Announce consequential dynamic updates—e.g., “Item added,” “Quantity changed,” “Three matching dishes,” “Checkout failed”—through appropriately scoped screen-reader status/live messages **without flooding the user** during typing/interim transcripts.
- Provide instructions and errors in plain language that identify a specific recoverable problem, not only “Something went wrong.”
- Support assistive technologies rather than disabling screen readers or forcing speech-based interaction.

### WEB-07 — Orientation, cognitive load and error prevention (MUST)

- Present a predictable path through discovery → item details → cart → review → demo submission; avoid forcing users to memorize unseen options.
- Expose which menu item is currently selected and which filter set is active, as accessible text and in the agent context.
- Provide concise on-screen explanatory content for choices and a way to go back/edit without resetting unrelated progress.
- For checkout, show items, quantities, price breakdown and total before requiring explicit confirmation. Any cart edit invalidates a previously captured confirmation.
- Pair essential voice guidance with text equivalents after integration; do not make audio the only route to an action or understanding of a result.

### WEB-08 — HCI design evidence (MUST)

The final design handover must briefly explain **why** its main decisions support task success: mode choice, navigation hierarchy, product presentation, orientation, error prevention, predictable feedback, accessibility and mode switching. Include at least the main user flows and notable error/recovery states; the explanation is not a demand for a prescribed visual style.

---

## 6. Functional data and state ownership

### WEB-09 — One authoritative data model (MUST)

The website must provide deterministic, inspectable application data independent of the voice model. For the demo, the catalog should be varied enough to test categories, prices, conflicting search results, vegetarian/spicy combinations, quantity edits, unavailable items and an empty result. A small believable fictional menu is sufficient; a live restaurant API is **not** required.

**Required conceptual data entities:**

| Entity | Required or representative information |
|---|---|
| Menu item | Stable `item_id`; name; category ID; PKR unit price; description; availability; available descriptors/tags (e.g., vegetarian, spicy); useful image/alt text if shown; option data if customization exists. |
| Category | Stable category ID, human-readable label and catalog mapping. |
| Search/filter view | Query text, selected category/attributes, active price constraint, stable sorted result IDs, visible item/selection and empty-result state. |
| Cart line | Stable product ID, selected option identity if applicable, quantity, validated unit price and derived line amount. |
| Cart summary | Authoritative quantities, subtotal, clearly disclosed charges/fees if any, currency and final calculated total. |
| Demo order | Unique demo submission/order identity, snapshot of current confirmed cart, confirmation status, submission outcome and readable simulated receipt. |
| App context | Schema version, `session_id`, increasing `revision`, route/section, selected or focused item, available semantic operations, visible catalog summary, filters, cart, totals and pending states. |

Rules:

- Stable semantic IDs—not DOM coordinates, CSS classes, card positions or generated name guesses—are the binding between UI, app actions and agent.
- Show prices, totals, availability and current item labels from the data model. Reconcile changes rather than maintaining separate display-only values.
- Clear the stale selection if an item leaves the active result set; provide a valid next selection/context instead of pointing the agent to a deleted card.
- Preserve meaningful state during ordinary navigation and mode switching. Refreshing should not accidentally submit an order twice.
- The UI can maintain transient view state, but **business state has one authority**. If a backend or Supabase is used, server-side validation is needed for material mutations and totals; the frontend does not become a trusted pricing source.

### WEB-10 — Shared operation layer (MUST)

Every business capability that the user can perform manually and that Habiba may request must be reachable via a **documented semantic application operation**. Manual controls must use the same underlying rules and state transitions as the eventual `agent.action_request` handler. Implement meaningful result information for success, rejection, stale state and uncertain outcomes. A reusable independent mock adapter must be able to call these operations without synthesizing browser mouse events.

---

## 7. Exact companion contract alignment: Habiba ↔ Zainab

This section mirrors **§5–6 of Habiba's v1.0 voice-agent specification**. The event names and operation strings below should remain **identical**, not be paraphrased independently. Both owners may jointly freeze improved payload details before final integration, but no silent renaming on one side.

### WEB-11 — Shared event envelope (MUST)

All application-level events/requests exchanged with the agent must carry the agreed fields:

- `schema_version` (initial value `1.0`);
- `session_id`;
- unique `event_id`;
- `turn_id` when associated with a conversational turn;
- consistent machine-readable `timestamp`;
- `context_revision` when a request depends on a snapshot;
- `type`; and
- typed `payload`.

A mutating `agent.action_request` also carries a unique **`action_id` / idempotency key**. Treat duplicate `action_id` submissions as retries of the **same** operation, not as permission to add or order again. Keep action results correlated with their originating IDs.

### WEB-12 — Agent events the website must be ready to consume (MUST)

| Incoming from Habiba | Required website responsibility |
|---|---|
| `agent.status` | Display accurate lifecycle: `off/awaiting_consent`, `connecting`, `ready/listening`, `user_speaking`, `thinking`, `assistant_speaking`, `waiting_for_action_result`, `idle`, `muted/paused`, `reconnecting`, `error`, `ended`. Native LiveKit statuses may be mapped to these product-facing meanings at integration. |
| `transcript.user.partial` | Show interim speech text if enabled; revise it instead of appending duplicate messages or issuing operations from incomplete speech. |
| `transcript.user.final` | Replace/finalize the relevant partial using `turn_id`. |
| `transcript.assistant` | Display assistant speech text and `started/updated/completed/interrupted` lifecycle; do not portray interrupted, never-spoken words as if already delivered. |
| `agent.action_request` | Validate, authorize, execute or reject the allowlisted semantic operation and return a correlated `app.action_result`. |
| `agent.clarification_required` | Present an accessible question/options without auto-picking a consequential option. |
| `agent.control` | Reflect supported pause/mute/resume/end/switch-mode requests safely; preserve valid business state. |
| `agent.error` | Display useful, recoverable information and manual/typed fallback without exposing raw provider secrets. |

### WEB-13 — Application events Zainab must expose (MUST)

| Outgoing toward Habiba | Required behavior |
|---|---|
| `app.context_snapshot` | Send the **current authoritative** context on successful session association and when a full refresh is requested. |
| `app.context_updated` | Send an updated, monotonically versioned context after relevant **manual or agent-driven** changes; distinguish new revision from stale UI messages. |
| `app.action_result` | Return the original `action_id`, accurate result status and verified state/data or a concise failure/confirmation reason. |
| `app.control` | Convey the user's explicit start/pause/mute/unmute/end/brief explanation/switch-mode instructions as applicable. Do not interpret choosing the normal website as consent for microphone activation. |
| `app.text_input` | Forward typed requests through the same conversational interpretation channel as speech; preserve current context and user identity/session link without fabricating an STT transcript. |

**Minimum context snapshot content:** `schema_version`, `session_id`, monotonic `revision`, current route/page/section, known selected/focused item, valid current actions/navigation targets **as semantic IDs with readable labels**, current query/filters, **bounded** visible results with `item_id`, name, factual PKR price/descriptors/availability, cart line items and summary, checkout availability, pending-action status and language/spoken-feedback preferences. The data source must be the website's current catalog/cart, **not an LLM-generated summary**. Large catalog dumps into every prompt are not required.

**Important:** The website may send updates even when changes are initiated manually; **do not only publish events after agent requests**. Each new relevant state version must be ordered and monotonic. The future bridge must be able to request a fresh snapshot after a reconnect/stale request.

### WEB-14 — Fixed semantic action allowlist (MUST)

The website must support or return an explicit and well-documented `not_supported` rejection for the agreed actions. All operations needed for the core demo **MUST** function:

| Operation string — preserve spelling exactly | Required behavior in website |
|---|---|
| `navigate` | Move to a valid, named destination/section and produce updated context. |
| `search_menu` | Search real catalog data and expose bounded, ordered results. |
| `filter_menu` | Apply valid structured filters to real catalog attributes; allow reset. |
| `select_item` | Set selection using an actual `item_id` present/available in the relevant context. |
| `get_item_details` | Return factual item price, description, options/descriptors and availability. |
| `get_cart` | Return the authoritative current cart and price/fee breakdown. |
| `cart.add_item` | Add validated item/options/quantity once, returning verified quantity and summary. |
| `cart.set_quantity` | Set absolute quantity to a valid number; do not mistakenly interpret as incremental add. |
| `cart.remove_item` | Remove the identified line/item consistently; report the updated summary. |
| `checkout.get_summary` | Return the current reviewable order snapshot and confirmation-relevant version/identity. |
| `checkout.submit_demo_order` | Create **one simulated order** only after valid explicit confirmation tied to the unchanged current summary. Never charge money. |
| `undo_last_reversible_action` | Reverse only a truly reversible action when valid; otherwise explain what can still be edited. |
| `get_current_context` | Return fresh authoritative app context, including after reconnect or stale-revision rejection. |

Each operation must use validated structured arguments and stable app IDs (e.g., `item_id`, category ID, `quantity`, filter fields), not arbitrary JavaScript, query selectors, CSS targets or browser coordinates. **Exact payload field lists and transport selection are a joint contract-freeze item**: match Habiba's final published schema; do not improvise incompatible formats. No requirement for Zainab to duplicate the agent's natural-language parsing.

### WEB-15 — Action results, confirmation and safety (MUST)

- Return `app.action_result` against the correct original `action_id`. Supported meanings must distinguish **`success`**, **`failed`**, **`rejected`**, **`stale_context`**, **`requires_confirmation`**, and **`timeout/unknown`** (precise wire values to be jointly frozen).
- Do not claim success through the interface before an action has actually succeeded. Show pending status first if necessary.
- For stale `context_revision`, reject or revalidate appropriately; a late result must not overwrite a newer manual navigation/cart change.
- Replaying the same mutation with the same `action_id` cannot create a second cart addition or demo order. After an uncertain timeout, reconcile by operation ID before any retry; **unknown is not failure and is not success**.
- Confirmation is bound to a **specific current checkout summary/cart revision**, not a vague remembered “yes.” If the cart changes, invalidate the previous confirmation and request a fresh summary/consent.
- Stopping or interrupting assistant *speech* does not automatically mean an in-flight application mutation was undone. Preserve and report the true outcome.
- Refuse out-of-scope operations and unrecognized IDs/quantities/fields gracefully. Never accept LLM-provided price or arbitrary discount as a trusted override.

### WEB-16 — Example exchange, for agreement and tests

The following mirrors Habiba's sample shape and shows the intended direction. It is an **interface example**, not an implementation recipe.

**Mock agent → website:**

```json
{
  "schema_version": "1.0",
  "type": "agent.action_request",
  "session_id": "demo-session-7",
  "event_id": "event-42",
  "turn_id": "turn-15",
  "timestamp": "2026-10-01T13:18:00+05:00",
  "context_revision": 8,
  "payload": {
    "action_id": "action-123",
    "operation": "cart.set_quantity",
    "arguments": { "item_id": "wrap-hot-chicken", "quantity": 1 }
  }
}
```

**Website → mock agent after a verified update:**

```json
{
  "schema_version": "1.0",
  "type": "app.action_result",
  "session_id": "demo-session-7",
  "event_id": "event-43",
  "turn_id": "turn-15",
  "timestamp": "2026-10-01T13:18:01+05:00",
  "context_revision": 9,
  "payload": {
    "action_id": "action-123",
    "status": "success",
    "verified_state": {
      "cart": [{ "item_id": "wrap-hot-chicken", "name": "Hot Chicken Wrap", "quantity": 1, "unit_price": 850 }],
      "currency": "PKR",
      "total": 850
    }
  }
}
```

A fresh `app.context_updated` is also made available for the changed state. Habiba may say that the quantity/total changed **only after** the verified result, as required by her companion specification.

---

## 8. Agent presence, voice panel and typed-access requirements

### WEB-17 — Agent-ready visual surface (MUST)

- Reserve a coherent, accessible place for optional conversational assistance. Zainab chooses panel/overlay/in-page layout; it must not obscure critical checkout controls, trap the user or permanently replace normal navigation.
- Express actual `agent.status` visually **and with meaningful accessible text**: connecting, ready/listening, user speaking, thinking, speaking, waiting for action, paused/muted, reconnecting and error/ended.
- Show user and assistant messages with accurate source/lifecycle. Interim STT is provisional; finalized text replaces the same utterance; canceled/unheard assistant output must not be misrepresented.
- Expose understandable start/stop/pause/mute/exit and (where applicable) typed-input controls. These controls publish user intent via `app.control`/`app.text_input`; the eventual LiveKit bridge decides provider-level actions.
- Display limited contextual options/help when appropriate; future proactive idle prompts come from **Habiba's agent**, not an independently running Zainab prompt timer. Provide a clear **Pause tips** preference that can be communicated to the agent.
- If the agent fails/disconnects, clearly identify that only **assistance** is unavailable, preserve the valid shopping session and allow normal browsing/checkout. Do not fake a connected microphone or generated speech.

### WEB-18 — Synchronized focus and navigation (MUST)

- After a meaningful **agent-driven** route transition, the page title/primary heading and selected context are announced appropriately for keyboard/screen-reader use, without unnecessary focus thrashing on every cart update.
- After a manual route/selection change, publish the new app context so agent orientation questions describe the current screen.
- Agent-triggered actions should change the **actual application state and rendered UI**; text in the assistance panel must never be the only place an action “happens.”
- Preserve meaningful user focus while transient captions/status updates stream. Avoid an audio/ARIA announcement storm when the future agent is speaking and the user has a screen reader enabled.
- Maintain the user's ability to operate the interface while a response is pending unless an operation truly requires a controlled temporary lock.

### WEB-19 — Connection and consent boundary (MUST)

- The browser must be capable of securely joining a future LiveKit session with short-lived server-issued credentials/appropriate permissions; **the actual token/room wiring is joint orchestration work**, not a prerequisite for Zainab's independent completion.
- The UI needs a clear opt-in/opt-out state and recoverable permission, connection and agent-unavailable states.
- Never embed LiveKit API secrets, Deepgram/Cartesia/LLM credentials or server-service keys in frontend code. No microphone recording or transcript persistence by default.
- A standalone **mock agent/event simulator** must exercise the same panel/action/context interfaces until the real agent is available.

---

## 9. Data persistence and optional Supabase

### WEB-20 — Persistence is a product decision, not a blocker (MUST)

A standalone working version may use a typed local/JSON catalog and suitable in-session application storage/state. **Supabase is optional**, and lack of a database must not justify an unfinished manual experience. If persistence is selected, use it to simplify the project, not to expand scope with unnecessary admin/auth features.

**Reasonable responsibility split:**

| Data/task | Initial acceptable approach | Supabase if chosen |
|---|---|---|
| Product catalog/categories | One consistent local JSON/data module | Public-read menu tables / controlled updates. |
| Search and filtering | Deterministic app-domain operations on catalog | Server query if needed, with same result contract. |
| Cart | Authoritative shared app state for current session | Optional persisted cart; not necessary for demo. |
| Demo orders | Deterministic simulated submission with unique ID/outcome | Optional saved order record and status. |
| Voice lifecycle/transcripts | Ephemeral connection/UI state | **Do not persist by default**; not required for ordering. |
| Authentication, live payments | Out of scope | Out of scope unless explicitly approved later. |

**If using Supabase (MUST):** maintain a schema/data dictionary, correct access policy (e.g., Row Level Security where data is exposed), backend validation of checkout and prices, appropriate public vs secret key separation, placeholder configuration only, and a reproducible demonstration seed. Do not expose a service-role key in the browser, leave unrestricted writes to orders, or store real personal/payment data for the lab. Avoid fragile dependencies on trial services: provide a local/demo-data fallback if relevant.

---

## 10. Trust, privacy, and truthful order flow

### WEB-21 — Safety and privacy (MUST)

- Label all orders/checkouts as a **demonstration**; no real payment requests, card capture, restaurant dispatch or fabricated successful transactions.
- Use fictional product/customer/delivery data for demonstration and testing. Minimize the information asked for; only request fields needed to show interaction quality.
- A confirmation action must correspond to a visible, current itemized summary; cannot be inferred from silence, incidental utterances or a stale earlier approval.
- Validate inputs and authorized operations independent of UI rendering. Protect against duplicate submission, invalid IDs and client-supplied price tampering.
- Avoid persistent audio/transcript capture. Any study recordings or participant data require informed consent and deliberate retention/deletion rules.
- Display recoverable user-facing errors; raw exception stacks, connection strings, tokens and vendor secrets do not appear in UI or published demo materials.

---

## 11. Responsiveness, reliability and experience-quality targets

These are **project acceptance/evaluation goals**, not guarantees from any third-party service. Document test device/browser and observed limitations.

### WEB-22 — Application quality (MUST)

- The app must be usable at common desktop and mobile widths and under keyboard-only navigation; major actions also remain functional at increased text size/zoom.
- Responsive action feedback: show an immediate perceivable pending/selection response wherever a longer operation follows; avoid treating a local loading animation as proof of backend success.
- Cart totals and selected-state rendering remain internally consistent after rapid clicks and repeated mock agent requests.
- Handle refresh/reconnect/agent failure without duplicate checkout effects or a fabricated confirmation message. Document what session state is intentionally preserved versus reset.
- Menu imagery and interface assets have reasonable performance/alternatives; do not let decorative motion interfere with task completion or screen-reader use.
- Failed network/data reads, unavailable item, malformed action, stale context and action timeout all produce distinguishable recoverable states.
- Basic automated and human accessibility checks are completed; outstanding limitations are documented rather than hidden.

**Optional internal experience targets (SHOULD, measured where feasible):** visible acknowledgment of a local control action within ~100 ms; no visually disruptive content/layout shifts; intelligible loading feedback for delayed actions; a manual checkout path that can be completed without unnecessary fields or repeated navigation.

---

## 12. Independent mock-agent acceptance tests

Zainab is **not** required to implement speech recognition, a real LLM or TTS. She **is** required to prove the website's receiving/sending side of Habiba's frozen contract by injecting correctly shaped mock agent events into the application adapter and inspecting the resulting app events. These tests can run before LiveKit is attached.

| Test ID | Scenario / input | Observable pass condition |
|---|---|---|
| W01 | Open website with all agent services disconnected. | Home, menu, cart and demo checkout remain usable manually. |
| W02 | Choose manual browsing at first visit. | No mic request/autoplay; user can immediately shop. |
| W03 | Keyboard-only full demo order. | All essential controls work, focus remains visible/logical and confirmation is reachable. |
| W04 | Search/filter vegetarian and price max 800, then clear. | Actual catalog results and count change; app context matches displayed filters/results. |
| W05 | Select a product, edit a valid option if offered, add quantity two. | Correct item/options and calculated prices appear in one shared cart. |
| W06 | Manually reduce quantity or remove a line. | Cart and total change accurately; user receives readable/accessibility feedback. |
| W07 | Attempt empty cart checkout or invalid quantity/unavailable item. | Action refused with actionable error, no fake success. |
| W08 | Complete valid manual checkout with explicit current-summary confirmation. | Exactly one **simulated** order is recorded/shown; no real payment claims. |
| W09 | Trigger a page/item change while a mock agent is subscribed. | `app.context_updated` emits the latest route/item and a higher revision. |
| W10 | Inject mock `agent.action_request` for `filter_menu`/`select_item`. | Real menu view/selection changes through shared operations; factual results are returned. |
| W11 | Inject `cart.add_item` followed by `cart.set_quantity` absolute quantity=1. | One verified final line quantity=1, coherent cart total and correlated `app.action_result`s. |
| W12 | Repeat the same mutating `action_id` / same request. | No duplicate add/submit effect; prior outcome can be reconciled. |
| W13 | Inject a request using a stale `context_revision` or invalid `item_id`. | Safe refusal/revalidation with proper reason; newer UI state is not overwritten. |
| W14 | Mock checkout request before explicit confirmation, then alter the cart. | `requires_confirmation`/rejection; old approval invalidated; updated summary required. |
| W15 | Simulate `timeout/unknown` on a demo-order submission. | No automatic second order; pending/uncertain state can be reconciled by `action_id`. |
| W16 | Mock `agent.status` for connect → listen → speak → pause → error. | UI displays correct product-facing states and remains keyboard accessible. |
| W17 | Inject user interim/final transcript with same `turn_id`, then interrupted assistant text. | Partial is replaced rather than duplicated; unheard assistant continuation is not represented as delivered. |
| W18 | Enter typed help/request while assistance UI is active. | Correct `app.text_input` envelope is emitted; no fake microphone/STT claim. |
| W19 | Manual cart edit during a simulated agent response, then request `get_current_context`. | Fresh result reflects manual edit; no separate agent cart. |
| W20 | Mock disconnect or denied microphone permission. | User can exit/pause the assistant and complete the **existing** cart manually. |
| W21 | Switch from manual → simulated assisted → manual. | Navigation/cart progress retained; unsolicited assistant guidance stops after exit. |
| W22 | Zoom/enlarge text, navigate with screen reader, trigger async cart updates. | Key content reflows; controls are named; status information is intelligible without announcement spam. |

**Evidence required:** Pass/fail notes, short screenshots or clips where useful, browser/device tested, a representative input/event trace and resulting app state, and an explicit list of unresolved issues. A strong project includes negative/failure cases as well as a happy-path demo.

---

## 13. Final deliverables Zainab must hand over to Habiba

The following is the **definitive handoff checklist**. Completion means Habiba can replace her mock application adapter with this website's documented shared interaction boundary; she must not have to reverse-engineer undocumented button logic or request a second menu/cart implementation.

1. **Complete editable UI/UX design** — Figma project (or comparable editable design file) covering the required screens, normal shopping flow, mode entry/exit, assistant states, and significant empty/loading/error/confirmation states. Include desktop and responsive presentation without mandating one specific visual theme.
2. **Working standalone frontend and application** — readable source project that launches independently and supports a complete functional manual food-ordering journey, including discovery, combined search/filters, item detail/customization where applicable, cart, review and simulated checkout.
3. **Accessible interaction implementation** — semantic structure, keyboard/focus behavior, appropriate alternative text/labels, usable feedback/status announcements, readable responsive layout and a documented WCAG 2.2 AA target/testing record.
4. **Single source-of-truth catalog and shopping domain** — documented stable item/category/option IDs, consistent PKR pricing, availability, filters, quantity rules, cart math and demo order semantics. Provide deterministic fictional seed/demo data.
5. **Documented semantic application API/adapter** — callable forms and argument/result types for **every operation in WEB-14**, shared by manual interactions and mock agent requests. It must be independent of fragile DOM selector/coordinate automation.
6. **Versioned state/context contract** — export shape for `app.context_snapshot` / `app.context_updated`, including session/revision, route, item selection, bounded results, filters, cart, totals, pending state and valid semantic actions. Provide example payloads and explicit update triggers for manual as well as simulated agent changes.
7. **Event/action handling contract** — schema or documented examples for the exact v1 envelope, `agent.action_request` consumption, `app.action_result` correlation, idempotency, stale-context policy, confirmation binding, result statuses and recovery after `timeout/unknown`. Include the actual implementation-facing entry point.
8. **Assistance panel and mock-agent test harness** — independently demonstrable product-facing agent status display, transcripts/captions, typed-input and control affordances, and a means of injecting mock agent events without LiveKit/provider keys. Clearly label simulated events as test/demo mode.
9. **Backend and optional database handoff** — explain the chosen data boundary, validation, session/order handling and any local/demo fallback. If Supabase is used, include schema/seed, RLS/access notes, placeholder `.env.example` and safe configuration requirements; **never hand over live secrets**.
10. **Independent acceptance record** — W01–W22 results, a keyboard + screen-reader smoke test, typical manual order evidence, negative/error scenarios and representative request/result/context event traces.
11. **Integration handover README** — how the project runs, dependencies/configuration placeholders, primary routes, shared state ownership, event subscription/dispatch entry points, expected integration inputs/outputs, any known limitations, and every item that must be **jointly finalized** with Habiba.
12. **Short HCI rationale** — maps the principal design decisions to orientation, feedback, flexibility, error prevention, user control, accessibility and continuity of manual/assisted interaction. Enough material for the final class presentation, without requiring a full research thesis.

### Definition of Zainab's independent work complete

With Habiba's agent switched off, a person can **successfully use the website from welcome through demo-order confirmation** using mouse/keyboard and accessible controls. With the mock agent harness, semantic requests correctly manipulate **that same website**, and each application action exposes validated, correlated results plus up-to-date context. The assistance UI accurately handles mocked speech/status events and provides honest manual/typed fallback. No integration requires Zainab to redesign the UI or rewrite cart/business rules.

---

## 14. Final orchestration readiness: joint agreement points (not assigned to Zainab alone)

Habiba and Zainab should compare both delivered interfaces before combining them. These are deliberately flagged as **shared boundary decisions**, not implementation work required before either partner finishes independently:

- Final wire schema/required and optional argument fields for all v1 operations; data types and exact result/error status values.
- Transport choice across LiveKit's supported frontend/agent messaging, text streams, RPC and/or an application backend. The transport is replaceable; **semantic event names and behavior are not**.
- Session association and secure short-lived room credential issuance; reconnect policy; how latest context is requested after transport recovery.
- Action result vs context-update ordering; revision handling; idempotency retention and timeout reconciliation.
- Active voice mode vs typed mode vs manual focus announcements, especially preventing screen-reader/voice output conflicts.
- Actual catalog/options/fees/availability seed agreed for the combined demo; Habiba's mock catalog must not become a competing source of truth.
- Cross-party end-to-end tests: welcome without user speech, barge-in during a description, manual-to-voice handoff, voice-to-manual return, stale context after manual edit, cart correction, explicit demo checkout confirmation and agent/provider outage.

**Integration success is defined by behavior, not by which framework calls which service.** Manual GUI input and agent input must reach the same validated shopping actions and return the same authoritative results.

---

## 15. Explicit out of scope and optional enhancements

**Out of scope for Zainab's independent deliverable:** building Habiba's real speech pipeline; training a speech model; actual money transfer; commercial restaurant inventory/fulfilment; extensive auth/admin features; indefinite storage of personal transcripts; disability verification; doctor appointment functionality; real voice biometrics; production multilingual guarantees; full autonomous purchases without explicit confirmation.

**STRETCH only if core requirements are already met:** persistent order history, favorite items, bilingual text, user-configurable larger typography/contrast options, richer dietary filters, refined low-bandwidth/offline handling, usability-study analytics using anonymous data, or advanced undo beyond safe reversible cart/navigation actions. These must not break core accessibility or event compatibility.

---

## 16. Shared reference and contract precedence

The **companion Habiba specification v1.0, especially its §§5–6**, defines the current interface direction: event envelope, exact event types, action allowlist, state revisions, action IDs, verified results, confirmation, interruption and text parity. This document mirrors those values for the application side. If the team changes any field, action or status, publish **one jointly agreed versioned contract** and update both partners' mock adapters and examples before final integration. Provider-specific speech implementation details remain Habiba's responsibility and must not leak into the website's domain action interface.

Useful accessibility references: [WCAG 2.2](https://www.w3.org/TR/WCAG22/), [WAI ARIA Authoring Practices Guide](https://www.w3.org/WAI/ARIA/apg/), and [WAI Natural Language Interface Accessibility User Requirements](https://www.w3.org/TR/naur/). These guide accessibility decisions but do not prescribe Zainab's colors, theme or specific page layout.

**End of Zainab's requirements specification.**
