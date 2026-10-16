# FoodEase Phase 14 Handover Documentation

Generated for Zainab's website seat on 2026-10-11.

This document is the website-side handover for marking and for Habiba's voice
agent integration. It describes how the project runs, where the source of truth
lives, which semantic operations are supported, how context/events should cross
the LiveKit boundary, and what remains a joint final decision.

## 1. Project Identity

FoodEase is a standalone accessible food-ordering website for a Human Computer
Interaction project. It supports a complete manual journey and a mock-agent
journey before any real speech system is attached.

Primary goals:

- Let sighted and blind/low-vision users browse, understand, add, review and
  place a simulated food order.
- Keep manual ordering fully usable when the voice agent is off, denied or
  disconnected.
- Expose a stable semantic application boundary for Habiba's future voice agent.
- Add 3D/AR-style presentation as progressive enhancement, never as a required
  ordering path.

## 2. Run Instructions

```bash
cd website
uv sync
uv run foodease-website
```

Default URL:

```text
http://127.0.0.1:8080
```

Useful checks:

```bash
cd website
.venv\Scripts\python.exe -m pytest tests\test_app.py tests\test_domain.py
.venv\Scripts\python.exe -m ruff check src tests
node --check static\js\app.js
```

No real payment, microphone, LiveKit token, API key or cloud database is needed
for the standalone website demo.

## 3. Architecture Summary

| Layer | Files | Responsibility |
|---|---|---|
| FastAPI app | `src/foodease_website/app.py` | Routes, template render, static serving, catalog/context/action API. |
| Domain state | `src/foodease_website/domain.py` | Single source of truth for cart, revision, search/filter, checkout and action idempotency. |
| Catalog loader | `src/foodease_website/catalog.py` | Loads and validates the frozen seed catalog. |
| UI template | `templates/index.html` | Main accessible ordering page, dialogs, AR fallback, mock harness and evidence console. |
| Browser behavior | `static/js/app.js` | Manual actions, mock-agent actions, AR fallback, context/evidence export. |
| Styling/assets | `static/css/app.css`, `static/img/` | Responsive visual system, food imagery, 3D/AR presentation. |
| Evidence/docs | `docs/` | UX blueprint, acceptance evidence, handover and rehearsal notes. |

State ownership:

- The website owns catalog display, cart, checkout and app context.
- The voice agent must call website operations instead of keeping a separate
  cart or menu truth.
- `voice-agent/` and `orchestration/` remain Habiba-owned.

## 4. Catalog And Data Dictionary

Catalog source:

```text
../zainab-pack/catalog-seed.json
```

Current catalog:

- Currency: PKR
- Service fee: 50 PKR
- Items: 28
- Categories: `biryani`, `burgers`, `desserts`, `drinks`, `karahi`,
  `platters`, `rolls`, `sides`, `wraps`

Important item fields:

| Field | Meaning |
|---|---|
| `item_id` | Stable ID used by buttons, API actions and mock agent requests. |
| `name` | Human-readable dish name. |
| `unit_price_pkr` | Unit price before service fee. |
| `category` | Stable category ID. |
| `tags` | Filter metadata such as `vegetarian`, `spicy`, `classic`. |
| `available` | If false, `cart.add_item` must reject with `out_of_stock`. |
| `description` | User-facing short dish description. |
| `ingredients` | Optional ingredient list for detail/agent responses. |

Cart math:

- `subtotal = sum(unit_price * quantity)`.
- Service fee applies only when at least one line exists.
- `total = subtotal + service fee`.
- Quantity is absolute for `cart.set_quantity` and additive for `cart.add_item`.

## 5. Operation API Reference

Endpoint:

```text
POST /api/app/action
```

Request shape:

```json
{
  "action_id": "unique-client-or-agent-id",
  "operation": "cart.add_item",
  "arguments": { "item_id": "wrap-hot-chicken", "quantity": 1 },
  "context_revision": 12
}
```

Supported operations:

| Operation | Arguments | Result / behavior |
|---|---|---|
| `navigate` | `{ "target": "home|menu|cart|checkout|back|category_id" }` | Changes route/filter context. |
| `search_menu` | `{ "query": "biryani" }` | Updates search and returns matching catalog items. |
| `filter_menu` | `{ "tags": [], "max_price_pkr": 800, "category": "wraps" }` | Updates filters and returns visible items. |
| `select_item` | `{ "item_id": "zinger-classic" }` | Sets focused item and route. |
| `get_item_details` | `{ "item_id": "zinger-classic" }` | Returns description, price, availability and ingredients. |
| `get_cart` | `{}` | Returns authoritative cart summary. |
| `cart.add_item` | `{ "item_id": "...", "quantity": 1 }` | Adds quantity if item exists and is available. |
| `cart.set_quantity` | `{ "item_id": "...", "quantity": 1 }` | Sets absolute line quantity for existing line. |
| `cart.remove_item` | `{ "item_id": "..." }` | Removes line. |
| `checkout.get_summary` | `{}` | Returns current summary plus confirmation token. |
| `checkout.submit_demo_order` | `{ "confirmed": true, "confirmation_token": "..." }` | Creates one simulated order, clears cart. |
| `undo_last_reversible_action` | `{}` | Restores prior cart where available. |
| `get_current_context` | `{}` | Returns current context snapshot. |

Important policies:

- Unknown operations are rejected with `unknown_operation`.
- Missing/invalid item IDs are rejected with `invalid_arguments`.
- Sold-out items are rejected with `out_of_stock`.
- Mutating operations with an old `context_revision` return `stale_context`.
- Reusing the same mutating `action_id` returns the same prior result without
  applying the mutation twice.
- Checkout confirmation is tied to the current cart. Cart edits invalidate the
  old token.

## 6. Context And Event Contract

Context endpoint:

```text
GET /api/app/context
```

Snapshot includes:

- `schema_version`
- `session_id`
- `revision`
- `route`
- `focus_item_id`
- `valid_actions`
- `valid_navigation_targets`
- `filter_tags`
- `search_query`
- `visible_items`
- `cart`
- `checkout_available`
- `action_pending`
- `language`

Browser demo evidence:

- Contract cockpit displays revision, route, focus, visible items, valid actions
  and cart totals.
- Evidence console can download the current context JSON.

Event names for Habiba alignment:

| Event / topic | Direction | Purpose |
|---|---|---|
| `agent.action_request` / RPC `foodease.action` | Agent to app | Ask website to perform a semantic operation. |
| `app.action_result` | App to agent | Return correlated verified result. |
| `app.context_snapshot` / `app.context_updated` | App to agent | Share current state and revision. |
| `app.text_input` | App to agent | Typed request parity with voice. |
| `agent.status` | Agent to app | Product-facing assistant status. |
| `transcript.user.*`, `transcript.assistant` | Agent to app | Caption/transcript display. |
| `app.control` / `foodease.control` | App to agent | Pause, mute, end and other assist controls. |

Schemas are in:

```text
../zainab-pack/contract/v1/schemas/
```

## 7. Mock-Agent Usage Guide

Website section:

```text
Guide -> Mock agent harness
```

Use it to demonstrate:

1. Start typed guidance.
2. Filter vegetarian under 800.
3. Add hot chicken wrap.
4. Ask checkout summary.
5. Type a request in the text box.
6. Pause/end assistance and continue manually.

Expected behavior:

- No microphone starts.
- Cart and context are the same as manual ordering.
- Refused actions show honest error feedback.
- Manual ordering remains available while guidance is paused or ended.

## 8. LiveKit Integration Guide

This website is ready to replace Habiba's MockApp at the application boundary.

Habiba-side references:

- `voice-agent/docs/handover/FRONTEND_QUICKSTART.md`
- `voice-agent/docs/handover/INTEGRATION_NOTE.md`
- `zainab-pack/handover/SESSION_API.md`
- `zainab-pack/contract/v1/schemas/transport_defaults.json`

Required LiveKit work:

1. On assistance start, call Habiba's session API with consent.
2. Join the LiveKit room as the app participant, ideally with
   `foodease.role=app`.
3. Register RPC `foodease.action`.
4. Route RPC payloads into the same domain behavior currently exposed by
   `/api/app/action`.
5. Publish context on topic `foodease.context` after every meaningful GUI/cart
   change.
6. Consume `agent.status` and transcript events into the existing assistant
   panel.
7. Keep browser mic mute and pause/end controls consent-first.

Do not put LiveKit, Deepgram, Cartesia, LLM, service-role or database secrets in
browser code.

## 9. Accessibility Report

Target: WCAG 2.2 AA-aligned class project implementation.

Implemented:

- Manual flow is complete without voice.
- No microphone starts before consent.
- Buttons, links, form inputs and dialogs use semantic HTML.
- Visible focus styling is defined.
- Live regions announce cart/status/context changes.
- Larger text, high contrast and calm motion controls are available.
- Checkout is explicit and simulated; no hidden payment claim.
- AR is optional and has a non-camera fallback.
- Food images use descriptive alt text in menu cards.

Manual checks still required before final submission:

- Keyboard-only complete order recording.
- Screen-reader smoke test notes.
- Mobile reflow screenshots.
- Browser zoom check at 200 percent.

## 10. HCI Rationale

FoodEase uses a manual-first, assistance-ready design because the target users
may include blind/low-vision users and users who simply prefer ordinary ordering.

Principal decisions:

- Orientation: persistent header, skip link, category rail, cart preview and
  context cockpit help users understand where they are.
- Feedback: cart totals, order status, live context and action traces make system
  state visible.
- Flexibility: users can browse by category, search, filters, details, mock
  guidance or AR preview.
- Error prevention: sold-out items, invalid quantities, stale revisions and old
  checkout tokens are refused safely.
- User control: assistance can start, pause and end without losing cart progress.
- Accessibility: display comfort controls, keyboard-friendly controls and
  manual fallback reduce dependence on any one modality.
- Continuity: manual and agent actions share the same semantic operations and
  cart state, so handoff between modes is coherent.

## 11. AR And 3D Enhancement Notes

Current state:

- Hero has a 3D-inspired dish carousel.
- Phase 12 adds optional tabletop AR/fallback preview.
- WebXR support is detected without opening the camera.
- Fallback works on desktop and unsupported browsers.

Future upgrade path:

- Replace fallback image surface with a real WebXR model viewer or Three.js
  scene when suitable assets are available.
- Keep AR behind explicit user action.
- Keep cart, checkout and details outside the AR dependency.
- Maintain text/alt/fallback equivalents for every dish.

## 12. Joint Decisions And Known Limitations

Joint with Habiba:

- Final LiveKit transport details and room credential issuance.
- Exact `app.context_updated` publish timing after each GUI action.
- Transcript replacement/interruption behavior for real streaming captions.
- Timeout/unknown result reconciliation in live network failures.
- Final demo catalog agreement if Habiba's agent seed differs from this website.

Current limitations:

- Real camera AR is not guaranteed on desktop browsers.
- Live voice pipeline is not embedded in the website yet.
- Final university format/template has not been provided.
- Screenshots/videos must be captured manually on the demo device.

## 13. Deliverables Mapping

| Required deliverable | Website status |
|---|---|
| Editable UI/UX design | Implemented in code; Figma/comparable editable design remains optional if required by teacher. |
| Working standalone frontend/application | Complete manual app with FastAPI/Jinja/CSS/JS. |
| Accessible interaction implementation | Implemented with manual flow, semantic controls and display comfort modes. |
| Single source-of-truth catalog/domain | `catalog-seed.json` plus `FoodEaseDomain`. |
| Semantic application API/adapter | `/api/app/action` with 13 operations. |
| Versioned state/context contract | `/api/app/context`, revision policy, context cockpit and export. |
| Event/action handling contract | Documented here and backed by idempotent/stale/confirmation behavior. |
| Assistance panel/mock harness | Implemented in Guide section. |
| Backend/database handoff | Local FastAPI demo; no external DB/secrets required. |
| Independent acceptance record | `PHASE_13_TESTING_AND_ACCEPTANCE_EVIDENCE.md` and evidence console. |
| Integration handover README | This document plus root `README.md`. |
| Short HCI rationale | Included above for presentation use. |
