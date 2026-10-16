# FoodEase Website

Python-first website/application seat for the accessible FoodEase ordering demo.

This folder is owned by Zainab's website work. It must not duplicate Habiba's
voice brain or orchestration secrets. The website owns catalog display, cart
state, checkout state, app context and the future app-seat integration boundary.

## What This App Demonstrates

- Complete manual food-ordering journey.
- Search, filters, categories, item details, cart, review and simulated checkout.
- Consent-first mock assistant panel with typed fallback.
- Semantic action API for Habiba's voice agent.
- Versioned app context with revision, route, focused item, visible items and cart.
- Idempotent action IDs, stale-context refusal and checkout confirmation tokens.
- Optional 3D/AR-style dish preview with graceful non-AR fallback.
- Accessibility controls for larger text, high contrast and calm motion.
- Phase 13 evidence console and written W01-W22 acceptance record.

## Quick Start

```bash
cd website
uv sync
uv run foodease-website
```

Default local URL:

```text
http://127.0.0.1:8080
```

No real payment, microphone, LiveKit token, LLM key, TTS key or cloud database is
required for the standalone website demo.

## Verification

```bash
cd website
.venv\Scripts\python.exe -m pytest tests\test_app.py tests\test_domain.py
.venv\Scripts\python.exe -m ruff check src tests
node --check static\js\app.js
```

## Important Docs

| File | Purpose |
|---|---|
| `docs/PHASE_14_HANDOVER_DOCUMENTATION.md` | Full handover: architecture, catalog, API, context/events, LiveKit, accessibility, HCI rationale and limitations. |
| `docs/PHASE_15_FINAL_DEMO_REHEARSAL.md` | Presentation script, manual demo, mock-agent demo, AR demo, mobile checks and fallback lines. |
| `docs/PHASE_13_TESTING_AND_ACCEPTANCE_EVIDENCE.md` | W01-W22 acceptance record, event trace and manual evidence checklist. |
| `docs/PHASE_02_UX_BLUEPRINT.md` | Early visual/UX direction. |

## Project Structure

```text
website/
  src/foodease_website/
    app.py          FastAPI routes and template context
    catalog.py      frozen catalog loader/validation
    domain.py       cart, checkout, revisions and semantic action handling
  templates/
    index.html      main page, dialogs, AR/evidence/assistant sections
  static/
    css/app.css     responsive visual system
    js/app.js       UI actions, mock harness, AR fallback, evidence runner
    img/            generated food images and sprites
  tests/
    test_app.py
    test_catalog.py
    test_domain.py
  docs/
```

## Data Source

The website loads the frozen seed catalog from:

```text
../zainab-pack/catalog-seed.json
```

Current demo data:

- 28 menu items
- 9 categories
- PKR pricing
- 50 PKR service fee
- Stable item/category IDs for the UI and future agent

Do not create a second catalog for voice integration. Habiba's agent should use
the website context/action results as the source of truth.

## API Summary

Catalog:

```text
GET /api/catalog/summary
GET /api/catalog/items
```

App context:

```text
GET /api/app/context
```

Semantic action endpoint:

```text
POST /api/app/action
```

Supported operations:

```text
navigate
search_menu
filter_menu
select_item
get_item_details
get_cart
cart.add_item
cart.set_quantity
cart.remove_item
checkout.get_summary
checkout.submit_demo_order
undo_last_reversible_action
get_current_context
```

See `docs/PHASE_14_HANDOVER_DOCUMENTATION.md` for arguments, result behavior and
integration notes.

## Mock-Agent Demo

Open the website and use:

```text
Guide -> Start typed guidance
```

Available demo scenarios:

- Filter vegetarian under 800.
- Add hot chicken wrap.
- Ask checkout summary.
- Send typed request.
- Pause/end guidance without losing cart progress.

The harness does not start a microphone. It injects contract-shaped mock actions
into the same `/api/app/action` endpoint used by manual UI behavior.

## Phase 12 AR/3D Notes

The app includes:

- Hero dish carousel with 3D-inspired staging.
- Optional `View on table` preview.
- WebXR support detection without automatic camera start.
- Non-AR tabletop fallback for desktop/unsupported browsers.

AR must never be required for cart, checkout or accessibility.

## Phase 13 Evidence

Open:

```text
Evidence -> Run contract smoke
```

The console runs a browser-side smoke check for key contract behavior and can
download:

- `foodease-phase-13-acceptance-evidence.json`
- `foodease-context-snapshot.json`

Written acceptance notes are in:

```text
docs/PHASE_13_TESTING_AND_ACCEPTANCE_EVIDENCE.md
```

## LiveKit Handoff Boundary

The website is ready to replace Habiba's MockApp at the semantic boundary.
Habiba's side should:

1. Start/dispatch the voice worker through the session API.
2. Let the website join the LiveKit room as the app participant.
3. Register RPC `foodease.action`.
4. Publish website context on `foodease.context`.
5. Consume `agent.status` and transcript events into the assistant UI.

Reference files outside this folder:

```text
voice-agent/docs/handover/FRONTEND_QUICKSTART.md
voice-agent/docs/handover/INTEGRATION_NOTE.md
zainab-pack/contract/v1/schemas/
```

## Boundaries

- `voice-agent/` stays Habiba-owned.
- `orchestration/` stays Habiba-owned.
- No LiveKit, Deepgram, Cartesia, LLM, service-role or database secrets belong in
  browser code.
- The website is allowed to simulate checkout only; it must not claim real
  payment or real restaurant fulfilment.

## Known Manual Checks Before Final Submission

- Keyboard-only full order recording.
- Screen-reader smoke notes.
- Mobile screenshots.
- Optional WebXR phone check if a supported browser/device is available.
- Final demo script review using `docs/PHASE_15_FINAL_DEMO_REHEARSAL.md`.
