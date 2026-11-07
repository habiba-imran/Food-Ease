# FoodEase menu and scrolling navigation — 7 November 2026

The existing food artwork, product names, item IDs, prices and categories are preserved. This update changes card framing, menu navigation, image delivery and add-to-cart feedback. Cart editing and checkout retain their existing layout and behavior.

## Implemented

- Original food images and descriptions open the existing full details dialog; titles also open it. Removed the separate Details button. The same voice assistant button remains inside the dialog, including keyboard access.
- Rounded outer card borders, inset image frames, consistent padding and readable prices/actions follow the supplied card reference while retaining FoodEase colors and photos. Wide screens use four columns; laptop, tablet and phone grids adapt to available width.
- Every category has a prominent heading banner framed by its existing food photos. No new food artwork or promotional claims were added.
- On entering the menu, the sticky navbar shows all nine category links, retains a compact FoodEase home link and theme toggle, highlights the current category and automatically scrolls its pill into view. Category links jump to their section; jumping to a hidden category clears the accepted search/filter state first.
- The same cart button moves from the navbar to the bottom-right corner while browsing the menu, retaining its existing count and event handler. It returns to the navbar at the top. The obsolete separate mobile cart bar was removed. Cart and voice shortcuts have separate positions.
- A successful authoritative Add displays an item-named notification on phone, tablet and laptop. It dismisses after 3.6 seconds, resets for another addition, and does not appear for a failed request. Existing live status announcements remain accessible; the visual toast does not duplicate them.
- All 28 catalog items are available and shown. The previous stock flag and stale stock description on Smoky BBQ Burger were updated in the canonical and deployed catalog copies. IDs, names, prices, categories, ingredients and all other product data remain unchanged.
- Full visual menu filtering uses the existing full catalog and server-accepted filter state, instead of treating the voice protocol's bounded 25-row context preview as the complete menu. The voice contract and backend endpoints are unchanged.

## Image loading

No original image files were changed or replaced. Cards now use the existing 160/320/480px responsive variants, instead of requesting up to 640px, and show a small original-image preview while the sharper version loads. Images near the viewport warm up ahead of scrolling; category jumps prioritize their relevant pictures. Full-size detail imagery remains available in the dialog.

Across the same 28 products, the existing 640px variants total 1,833,696 bytes. The 480px variants total 1,043,944 bytes (43.1% less); adding all 160px previews brings the card-image total to 1,231,712 bytes (32.8% below the 640px total). These are file-size comparisons, not a measured production loading-time improvement. Actual transfers depend on viewport, device density and cache. A browser test delayed the larger files and confirmed that the original-image preview stays visible until loading completes.

## Verification

- Build and JavaScript syntax checks passed.
- JavaScript unit suite: 49 passed.
- Website Python tests: 41 passed; lint passed. Stock-refusal coverage now simulates stock loss in a test session, rather than requiring a sold-out product in the shipped menu.
- New menu browser suite: 10 passed across 375px, 768px and 1440px, including image/description interaction, voice access, all 28 items, cart placement, timed feedback, category tracking, filter recovery, failure feedback and delayed image loading.
- Broader browser pass exercised 59 tests: 57 passed, then the home-link regression and obsolete mobile-cart test were corrected. Both affected cases passed on rerun, together with two additional voice/cart keyboard checks.
- Responsive hero, search/filter, detail quantities, merged cart actions, checkout and receipt paths remain covered by the existing suites.
- Light/dark/high-contrast audit: 824 solid-color text pairs across 15 surfaces, zero contrast failures, zero console errors and no viewport/header overflow. Gradients, images and disabled controls are outside the contrast audit.

## Main files

- `website/templates/index.html`
- `website/static/css/menu-polish.css` and `website/static/css/food-experience.css`
- `website/static/js/app.js` and `website/static/js/experience.mjs`
- Matching public assets and regenerated `food-experience.css`
- `zainab-pack/catalog-seed.json` and `website/zainab-pack/catalog-seed.json`
- `website/tests/browser/menu.spec.mjs`, `manual-ordering.spec.mjs`, `integration.spec.mjs` and the floating-controls case in `voice-entry.spec.mjs`
- `website/tests/test_catalog.py` and `website/tests/test_session_authority.py`

Snapshots and audit results are under `artifacts/menu-experience-2026-11-07/`. Existing voice/orchestration edits were preserved outside this UI change. Live provider audio, production deployment and physical-device interaction were not verified by the offline fixture.
