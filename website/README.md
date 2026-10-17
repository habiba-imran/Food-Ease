# FoodEase Website

Python-first website/application seat for the accessible FoodEase ordering demo.

**Final delivery:** Use the [final runbook](../orchestration/docs/FINAL_RUNBOOK.md)
for the real website/session/worker stack and supported PowerShell commands.
Phase 9 adds keyboard activation/exit and real browser session-isolation checks;
human screen-reader, physical-device and live provider acceptance remain separate.
No visual polish or animations are part of this orchestration delivery.

**Final orchestration Phase 8:** The browser blocks new assistance work and audio
during reconnect, waits for fresh worker-acknowledged state, keeps original pending
action IDs and recovers cleanup identity after reload. Backgrounding/expired
credentials stop locally and require a new gesture; duplicate tab ownership is
guarded where browser Web Locks are supported. See
[recovery handoff](../orchestration/docs/PHASE_08_RECOVERY.md) and
[evidence](../orchestration/evidence/final/phase-08/report.md). No UI redesign is
included. Cloud/provider failures and actual audible interruption timing still
need live validation; Phase 9 is not implemented.

**Final orchestration Phase 7:** Actual worker/browser tests now cover page reading,
selection by presented position, semantic Add to cart, next/previous, manual-change
clarification, filter refinement and quantity correction. The live worker has the
semantic context and streaming prompt/tool wiring; the separate real-model and
human listening quality gate is pending. See the
[conversation handoff](../orchestration/docs/PHASE_07_GROUNDED_CONVERSATION.md).
No UI polish or animation work is included.

**Final orchestration Phase 6:** The existing assistant surface now offers explicit
spoken-choice consent, direct manual/voice/typing, complete local media shutdown,
brief same-session resumption and optional typed speech output without capture.
See [mode handoff](../orchestration/docs/PHASE_06_OPENING_MODES.md) and
[evidence](../orchestration/evidence/final/phase-06/report.md). Returning visits
still require activation. No UI redesign or Phase 7 work is included.

This folder is owned by Zainab's website work. It must not duplicate Habiba's
voice brain or orchestration secrets. The website owns catalog display, cart
state, checkout state, app context and the app-seat integration boundary.

**Final orchestration Phase 5:** The page now imports the LiveKit bridge, the
assistance controller and one authoritative renderer. Explicit typed/voice buttons
connect the existing shopping session to the worker. See [browser/runtime handoff](../orchestration/docs/PHASE_05_BROWSER_INTEGRATION.md)
and [verification report](../orchestration/evidence/final/phase-05/report.md).
The opening spoken mode chooser remains Phase 6; live provider/audio activation
is not claimed. The dated Phase 2/3 notes below are historical milestones.

Final orchestration Phase 2 adds owner-scoped shopping sessions, the shared 2.0
validator, atomic/idempotent operation handling and receipt lookup. See the
[authority API and limits](../orchestration/docs/PHASE_02_APPLICATION_AUTHORITY.md).
Use one website process: state is bounded and in memory. Voice/LiveKit integration
and the spoken mode chooser remain later work.

Phase 3 adds the tested, injectable `assistance-controller.mjs` lifecycle module.
The page does not import it yet; LiveKit SDK/page wiring remains Phase 5. See the
[lifecycle and verification boundary](../orchestration/docs/PHASE_03_ASSISTANCE_LIFECYCLE.md).

## What This App Demonstrates

- Complete manual food-ordering journey.
- Search, filters, categories, item details, cart, review and simulated checkout.
- Consented typed/voice assistant panel connected to the configured session service and worker.
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
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m ruff check src tests
node --check static\js\app.js
node --test tests\session_transport.test.cjs
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
