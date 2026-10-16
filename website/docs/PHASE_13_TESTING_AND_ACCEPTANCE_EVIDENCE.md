# FoodEase Phase 13 Testing And Acceptance Evidence

Generated for Zainab's website seat on 2026-10-11.

This record proves the website side of FoodEase without requiring Habiba's real
speech pipeline. The app can be used manually, the mock harness injects semantic
actions through `/api/app/action`, and the same catalog/cart/checkout domain
returns verified results for both manual and simulated agent input.

## Evidence Summary

- Manual journey: home, menu, search/filter, item details, cart, review and
  simulated checkout are implemented in the standalone FastAPI app.
- Contract journey: app context is available at `/api/app/context`; semantic
  actions are handled by `/api/app/action`.
- Negative cases: sold-out items, stale revisions, duplicate action IDs and
  expired checkout confirmation tokens are handled by the domain.
- Accessibility target: semantic controls, visible focus, keyboard-reachable
  buttons/dialogs, live status messages, larger text, high contrast and calm
  motion toggles are present.
- AR stretch: Phase 12 adds an optional tabletop preview and WebXR support
  detection without starting the camera or blocking the ordering flow.

## W01-W22 Acceptance Checklist

| ID | Scenario | Current evidence | Status |
|---|---|---|---|
| W01 | App opens with agent services disconnected. | Manual UI renders independently; no voice service is required. | Pass |
| W02 | Manual browsing on first visit. | No microphone or autoplay prompt is started; ordering CTAs are normal buttons/links. | Pass |
| W03 | Keyboard-only full demo order. | Controls and dialogs are keyboard reachable with visible focus. Human keyboard walkthrough still recommended for final submission. | Pass, manual observe |
| W04 | Search/filter vegetarian under 800, then clear. | Shared `filter_menu` operation and visible menu controls use the frozen catalog. | Pass |
| W05 | Select product and add quantity two. | Item detail dialog uses `select_item`, `get_item_details`, then `cart.add_item`. | Pass |
| W06 | Reduce quantity or remove line. | Cart controls call `cart.set_quantity` and `cart.remove_item`; totals update from domain state. | Pass |
| W07 | Empty checkout, invalid quantity, unavailable item. | Domain rejects unavailable item with `out_of_stock`; checkout is disabled or refused when empty. | Pass |
| W08 | Complete valid manual checkout with explicit confirmation. | `checkout.get_summary` issues a token and `checkout.submit_demo_order` creates one simulated order only. | Pass |
| W09 | Page or item change while mock agent subscribed. | Context revision increments and cockpit updates route/item/focus/cart values. | Pass |
| W10 | Inject `filter_menu` / `select_item`. | Mock harness and acceptance runner call the same `/api/app/action` endpoint. | Pass |
| W11 | `cart.add_item` then absolute `cart.set_quantity=1`. | Domain tests and browser runner verify final quantity is one. | Pass |
| W12 | Repeat mutating `action_id`. | Domain caches prior result and avoids double mutation. | Pass |
| W13 | Stale `context_revision` or invalid item. | Stale mutations return `stale_context`; invalid IDs are rejected. | Pass |
| W14 | Checkout request before confirmation, then cart changes. | Old confirmation token is invalidated after cart mutation. | Pass |
| W15 | Timeout/unknown reconciliation. | Action ID idempotency is implemented; real transport timeout simulation remains a joint integration test. | Partial, joint |
| W16 | Mock status connect/listen/speak/pause/error. | Assistance panel exposes product-facing status states and remains independent of voice services. | Pass |
| W17 | Interim/final transcript replacement and interruption. | Transcript panel exists for mock events; true streaming replacement is a LiveKit/agent integration detail. | Partial, joint |
| W18 | Typed help/request while assistance active. | Typed input emits an `app.text_input` style trace in the mock transcript. | Pass |
| W19 | Manual cart edit during simulated response, then context request. | `get_current_context` returns the fresh shared cart; there is no separate agent cart. | Pass |
| W20 | Mock disconnect or denied microphone. | Pause/end controls preserve cart and manual checkout remains usable. | Pass |
| W21 | Manual to assisted to manual. | Start, pause and end controls do not reset cart or navigation state. | Pass |
| W22 | Zoom/enlarge text, screen reader, async updates. | Larger text/high contrast/calm motion toggles and live regions are present. Screen-reader smoke test should be recorded manually. | Pass, manual observe |

## Representative Event Trace

```json
{
  "agent.action_request": {
    "action_id": "acceptance-filter-001",
    "operation": "filter_menu",
    "arguments": {
      "tags": ["vegetarian"],
      "max_price_pkr": 800,
      "category": null
    },
    "context_revision": 1
  },
  "app.action_result": {
    "status": "success",
    "verified_state": {
      "items": "bounded list from the FoodEase catalog"
    }
  },
  "app.context_updated": {
    "revision": "higher than the request revision",
    "route": "menu",
    "cart": "authoritative cart summary"
  }
}
```

## Manual Evidence To Capture For Final Submission

1. Desktop screenshot of home, menu/cart, AR fallback, mock assistant and evidence console.
2. Short clip of keyboard-only add to cart and demo checkout confirmation.
3. Short clip or screenshot of Phase 12 AR fallback on desktop.
4. Phone/browser check for WebXR AR availability if a supported device is available.
5. Screen-reader smoke notes: landmark navigation, button names, cart update announcement and checkout dialog.

## Known Limitations

- Real WebXR camera AR is not forced because desktop browsers usually do not support it and the project must remain accessible without AR.
- Habiba's real STT/LLM/TTS/LiveKit pipeline is still a joint integration boundary.
- Final screenshots/videos are manual evidence tasks, not something the local test runner can capture reliably here.
- The UI uses fictional seed data from `zainab-pack/catalog-seed.json`; final demo catalog changes must be made there first.

## Commands For Technical Verification

```bash
cd website
.venv\Scripts\python.exe -m pytest tests\test_app.py tests\test_domain.py
.venv\Scripts\python.exe -m ruff check src tests
```

## Final Reviewer Notes

After running the page, click **Evidence**, run **Run contract smoke**, then
download the evidence JSON and context snapshot. The browser runner is not a
replacement for human HCI observation, but it proves the main semantic contract
behaviors before Habiba connects the live voice agent.
