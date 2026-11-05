# FoodEase frontend audit — 3 November 2026

The existing FoodEase visual identity and real catalog are preserved. The manual
ordering path has been verified in Chromium on desktop, tablet and mobile, and
with a keyboard-only journey. Checkout remains an explicitly simulated order:
the UI displays a receipt only after the existing website authority confirms it.
No payment or restaurant fulfilment was added.

## Architecture and scope

The website uses FastAPI/Jinja2, plain JavaScript modules and layered CSS bundled
with esbuild. The existing application queue and Python domain remain the shared
authority for manual and agent actions, cart prices, quantities, confirmation
tokens and receipts. Native HTML dialogs provide modal focus containment and
background inertness. Relevant assets also have a `public/static` hosting copy.

Reviewed surfaces include the hero/mode choice, navigation, categories, search,
filters, product cards, product details, cart, checkout, receipt, display controls,
optional previews and the shared assistance UI. Existing unrelated work in the
checkout was preserved, including the local editorial and cart-dialog work.

## Problems found and fixes

| Finding | Resulting behavior |
| --- | --- |
| Overlapping cart-link handlers and duplicate Edit cart handlers | Each interaction issues one navigation action; repeated navigation targets share their pending request. |
| Cart rerenders could drop focus when quantities changed or a line disappeared | Focus remains on the corresponding enabled control, a nearby line or the close button. Reaching 99 moves focus to decrement when increment becomes disabled. |
| Background scrolling and modal dismissal were inconsistent | Open dialogs lock background scrolling. Native focus containment, Escape, backdrop dismissal and return focus are verified. Dismissal still works after an unresolved request. Clicking dialog padding does not count as clicking the backdrop. |
| Cart rows truncated names, lacked photos and used small controls | Rows show decorative product thumbnails, full wrapping names, unit price, quantity and line total. Controls have at least 44px targets. The cart itself scrolls with a sticky close header. |
| Entire cart lists were live regions, while ordinary status text was inside a closed cart | One concise status region on the active surface announces changes/errors. Lists and background context summaries no longer repeatedly announce their entire contents. |
| Quantity input silently clamped invalid numbers | Blank, fractional and out-of-range quantities receive associated inline errors and focus. The selected item total updates with valid input. |
| Product and checkout surfaces inherited conflicting styles | Responsive sizing, image presentation, spacing, readable copy, totals and actions now use the existing FoodEase palette and typography consistently. |
| Dark-mode rules forced nearly black text onto dark Details and quantity controls | Removed the conflicting hardcoded rules and use theme variables. High-contrast mode also overrides theme combinations consistently. |
| Author CSS overrode the native `hidden` attribute | A shared rule keeps inactive receipt, recovery and assistance content hidden. |
| Repeated confirmation clicks could enter the handler before UI state settled | Confirmation starts disabled, becomes available only with a verified review, and is guarded during submission. Uncertain outcomes keep confirmation disabled until recovery. Existing idempotent request recovery remains intact. |
| Item headings shared the category heading level | Menu hierarchy is now section h2, category h3, item h4. The skip link focuses the menu. |
| Ordering modes were easy to miss inside optional features | The hero's manual action selects manual mode, and nearby copy links directly to voice/typed choices and explains microphone consent. No automatic microphone request was added. |
| Native dialogs made the existing typed assistance form inert in the background | While typed guidance is active, the original form and transcript move into the active shopping dialog and return afterward. No duplicate inputs or new session logic are created. Dialog actions can switch an already-active voice session to typing or end assistance using existing lifecycle functions. |

The frozen catalog has no configurable variants or add-ons. The detail UI states
that the dish is served as listed; it does not invent customization data or
change pricing contracts. The existing default authority window contains 25
items; category filters and search expose the full 28-item catalog.

## Files changed for this audit

Paths below are relative to `website/`.

| File | Purpose |
| --- | --- |
| `templates/index.html` | Dialog markup, mode explanation, heading hierarchy, labels, validation/status regions and safe initial confirmation state. |
| `static/js/app.js` | Cart/dialog rendering, navigation guards, focus restoration, quantity validation, submission guards and UI-only placement of existing typed guidance. |
| `static/css/app.css` | Remove conflicting legacy dark-mode control colors. |
| `static/css/redesign.css` | Remove a forced tiny menu-category font size. |
| `static/css/food-experience.css` | Include the scoped ordering polish stylesheet. |
| `static/css/cart-window.css` | Refine the existing local cart window: scrolling, backdrop and wrapping names. |
| `static/css/ordering-polish.css` | Shared ordering surfaces, controls, focus rings, responsive layouts, theme/contrast fixes and reduced-motion support. |
| `static/vendor/food-experience.css` | Rebuilt stylesheet bundle. |
| `tests/browser/manual-ordering.spec.mjs` | New end-to-end manual, keyboard, validation, limits, failure, focus, scrolling and duplicate-submission regressions. |
| `tests/browser/ui.spec.mjs` | Exercise checkout through the cart trigger and the updated heading semantics. |
| `tests/browser/delivery.spec.mjs` | Keyboard checkout and accessible dialog assistance exit. |
| `tests/browser/opening.spec.mjs` | Open the real assistance disclosure and verify voice-to-typing inside checkout. |
| `tests/browser/recovery.spec.mjs` | Open assistance before interacting, and recover checkout through the cart. |
| `tests/browser/conversation.spec.mjs` | Open assistance through actual navigation before typed conversation tests. |
| `tests/browser/integration.spec.mjs` | Recovery selectors respect active surfaces; screenshots go to current audit evidence rather than overwriting historical orchestration evidence. |
| `tests/browser/food-studio.spec.mjs` | Expand the assistant section before using it as the offscreen scroll destination. |
| `tools/ui-audit.mjs` | Reproducible local visual, native accessibility snapshot and computed text-contrast audit. |
| `docs/ui-audit-evidence/` | Current screenshots, accessibility snapshots and `audit.json`. |
| `docs/FRONTEND_AUDIT_2026-11-03.md` | This handoff. |

Matching public assets were synchronized and their hashes checked:

- `public/static/js/app.js`
- `public/static/css/app.css`
- `public/static/css/redesign.css`
- `public/static/css/editorial.css` (preserves the existing local editorial work)
- `public/static/css/food-experience.css`
- `public/static/css/cart-window.css`
- `public/static/css/ordering-polish.css`
- `public/static/vendor/food-experience.css`

No application-authority, catalog, API-contract, orchestration or voice-worker
source was changed. Dedicated browser assistance/session/media modules also
remain unchanged. The shared app renderer has the UI-only integration changes
described above. No secrets, environment files, dependency versions or Git
history were changed. Nothing was pushed or deployed.

## Verification

| Check | Actual result |
| --- | --- |
| `npm test` | 44 passed. |
| `.venv\Scripts\python.exe -m pytest -q` | 41 passed; existing Starlette/httpx deprecation warning. |
| `.venv\Scripts\python.exe -m ruff check src tests` | Passed. |
| `node --check static/js/app.js` | Passed. |
| `npm run build` and final `npm run build:studio` | Passed. |
| `npm run test:browser -- --reporter=dot` | 71 passed (4.7 minutes). |
| Targeted regressions for the final integration fixes | 8 passed. |
| `node tools/ui-audit.mjs` against the local fixture | 834 computed solid-color text pairs across light/dark/high-contrast ordering surfaces: zero contrast failures. Zero page/console errors or failed static assets in this audit. |
| Responsive visual checks | No page/header horizontal overflow at 320, 375, 667, 768 and 1440px widths. |
| Source/public copies | Eight asset pairs match by hash. |
| `git diff --check` | Passed. |

There is no JavaScript lint/typecheck script in this project. A Python pyright
configuration exists, but pyright is not installed in the available environment.
No static typecheck result is claimed; JavaScript syntax, Python lint, builds and
runtime tests are reported separately.

The browser tests use the real website authority and, for assistance regressions,
the existing offline worker/RTC/model fixtures. They do not use paid providers.
Browser processes required execution outside the filesystem sandbox because the
fixture could not start there. Offline media tests print warnings about missing
real audio IO; they are not evidence of real microphone, caller or speaker quality.

Verified journeys include:

- Desktop, tablet and mobile: manual mode, category filter, product details,
  quantity selection, add, multiple items, cart increment/decrement/removal,
  exact subtotal/service fee/total, checkout, confirmed demo receipt and reload.
- A complete Tab/Enter/number-key/Escape journey without mouse activation.
- Native dialog names, quantity descriptions, heading hierarchy, focus
  containment, return focus, sold-out items and disabled actions.
- Blank/zero/negative/fractional/over-limit quantities; repeated additions merge
  into one cart line; the domain's 99-per-item ceiling is reflected in controls.
- Ten real products in a scrolling mobile cart, with close and checkout reachable.
- Failed checkout, unresolved actions, lost responses, recovery without replay,
  and guarded quantity/order submissions.
- Manual mode without microphone capture or assistance dispatch; offline voice,
  typing, mode switching, local shutdown and reconnection regressions.

## Evidence and remaining acceptance

`docs/ui-audit-evidence/` contains desktop/tablet/mobile detail, cart and checkout
screenshots; theme screenshots; viewport screenshots; and `audit.json` with native
accessibility snapshots and measured text pairs. Reproduce the visual audit
against a running local website with:

```powershell
cd C:\HCI-PROJECT\website
node tools/ui-audit.mjs http://127.0.0.1:8080
```

These are browser automation and computed-color checks, not a WCAG certification
or a human screen-reader test. Gradients, imagery, transparency effects and
disabled controls are excluded from the text-contrast calculation.

Before a university demonstration, perform this human acceptance check:

1. With NVDA/Firefox or VoiceOver/Safari, reach **Skip to menu**, activate it,
   browse categories and confirm selected filter states are announced.
2. Open an item, read its name/price/ingredients, enter an invalid quantity and
   verify the associated error. Correct it, add it and hear the concise update.
3. Open the cart, use Tab/Shift+Tab, change/remove products and verify focus stays
   meaningful. Press Escape and confirm focus returns to the cart trigger.
4. Review and confirm the demo order. Hear the receipt/status and verify the
   interface clearly says no payment or restaurant fulfilment occurred.
5. On a physical phone, check scrolling, text enlargement and close/checkout
   reachability in portrait and landscape. Separately test real voice providers
   and audible playback if needed for the presentation.

Physical-device, human screen-reader, live-provider/audio and production hosting
acceptance remain unperformed. The existing in-memory shopping authority still
requires a single running server process; server restarts or independent
serverless instances do not provide durable/shared carts. No persistence or
backend redesign was included in this frontend task.
