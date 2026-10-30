## Delivery and motion refinement

Current preview: http://127.0.0.1:8193/?design=delivery-7. Images now use lighter responsive delivery assets, priority hero loading, lazy lower images and versioned caching. The navbar is flush with the top; lower static copy reveals on scroll with motion preferences respected. See `docs/DELIVERY_OPTIMIZATION.md` for measurements, asset locations and validation.

## Catalog and lower-page refinement

The approved editorial hero is unchanged. Everything below it now uses the coordinated collection design in `website/static/css/catalog.css`, with 28 alpha-preserving food photographs, four large preview cards, consistent categories/menu/details/tabletop imagery, and refined cart/assistant surfaces. Current preview: http://127.0.0.1:8193/?design=catalog-6. See `docs/CATALOG_ARTWORK.md` for the saved assets, prompts and validation.

# FoodEase current art direction — editorial edition

The supplied references establish the current direction: a full-frame olive composition, one photographic food object, expansive condensed typography behind the object, fine orbital lines, sparse metadata, hard-edged orange actions, and a charcoal catalog. This supersedes the previous restaurant-card hero and paper/linen finish. `textures.css` is no longer imported by the production stylesheet.

The new identity is implemented in `static/css/editorial.css`. Bebas Neue is self-hosted for display type, DM Sans remains the reading face, and system monospace is used for short metadata. The menu, categories, cart, details, tabletop, assistant and checkout share the same palette and geometry.

The photographic campaign is the default hero view. Its generated, alpha-preserved studio artwork is `static/img/editorial/chicken-burger-hero.webp`; its exact prompt and source provenance are in `docs/EDITORIAL_ARTWORK.md`. Pointer parallax and float motion add depth without claiming the photograph is a 360-degree model. The explicit **Inspect 3D** view retains the working illustrated model, drag/keyboard rotation, layer controls, pause, reduced motion, and fallback. `studio-loader.mjs` loads the WebGL bundle only when the inspector is requested. Voice and ordering state have no dependency on either hero view.

The existing app route, API endpoints, catalog data, shopping session authority, confirmation tokens, ordering operations, LiveKit wiring, media consent, and worker/orchestration source remain unchanged. Both campaign and inspector views are presentation state only. Existing data hooks remain available, including the featured-dish carousel and assistance controls inside shopping dialogs.

Current preview: http://127.0.0.1:8193/?design=editorial-5. Screenshots: `artifacts/editorial-v5/`.

Build: `npm.cmd run build` from `website/`. This copies local font files/licenses and builds the minified CSS and optional 3D bundle. The original PNG food assets and responsive WebP derivatives remain intact. The live website still uses the existing orchestration/worker arrangement; this local preview starts the website only.

## Editorial edition verification

- Production build, browser-module syntax, changed-file Ruff and Git whitespace checks passed.
- Full offline browser suite: 58 passed. JavaScript regression suite: 44 passed.
- Website tests: 39 passed after updating the two homepage copy assertions.
- Default campaign loads no Three.js bundle; requesting Inspect 3D loads it on demand.
- Ordering, backend, orchestration and voice source modules are unchanged. Live provider audio was not retested.

## Earlier implementation and verification history

# FoodEase premium interaction design

## Existing application and preservation boundary

The app is FastAPI + Jinja with vanilla JavaScript, CSS, esbuild, and the existing LiveKit browser client. There is one customer-facing HTML route (`/`). Item details, tabletop preview, checkout review, and receipt are dialogs driven by the existing application state. Category, menu, cart, assistant, and project evidence are sections on that page.

The redesign preserves all data attributes used by the app, menu and cart operations, authoritative sessions, confirmation tokens, API routes, provider integrations, and voice consent/media lifecycle. `app.js`, `application.mjs`, `assistance-controller.mjs`, `livekit-bridge.mjs`, orchestration source, worker source, and the existing LiveKit version are unchanged.

## Design direction and implementation plan

Use a warm food-tech identity: evergreen ink, tomato actions, ivory paper, peach/coral 3D stage, and butter-yellow highlights. Pair a bold geometric sans with an expressive culinary serif. UI/UX Pro Max informed the 3D/hyperrealism direction, forest-green/warm-accent palette, geometric-body/editorial-heading pairing, 300–400 ms spatial feedback, container-based canvas resizing, pointer/touch alternatives, focus, contrast, and reduced-motion requirements. Its generic brutalist recommendation was rejected because it did not fit a premium food-ordering experience.

1. Establish local DM Sans and Fraunces fonts, semantic palette/elevation tokens, consistent radii, and tactile buttons.
2. Build a real Three.js illustrated burger scene with modeled layers, sesame seeds, plate, lighting, and shadows. Provide drag, keyboard rotation, explicit turn buttons, layer spacing, assembled/exploded controls, and a pause control. This is an illustration rather than a scan of a catalog dish.
3. Retain catalog photography and existing selection behavior in a separate featured-dish composition. Give category cards image feedback and clearly selected states.
4. Use responsive menu grids, subtle pointer tilt, section/card entrances, and image-to-bag feedback after a verified cart update. Keep a sticky desktop summary and show the mobile bag shortcut after items are added.
5. Style item details, quantity, checkout review, and receipt with the same typography, surfaces, spacing, and controls. Keep assistant controls readable when the app moves them inside a shopping dialog.
6. Style the optional tabletop photo preview and the assistant consistently. Keep the assistant decorative sculpture separate from real listening/voice state.
7. Verify actual phone control widths, anchored navigation beneath the header, larger text, dark/high-contrast modes, keyboard controls, and WebGL failure fallback.

## Performance and accessibility

The renderer is created on visibility/idle, sizes to its container, caps pixel ratio at 1.75 and animation at 30 fps, and stops while hidden/offscreen. Reduced motion and the existing calm-motion preference stop automatic movement. Rotation, layer spacing, and shopping remain usable without drag or automatic animation. WebGL failure leaves the fallback image and ordinary ordering available.

All 28 original food PNGs remain intact. Responsive 320/640 px WebP derivatives total 1,307,082 bytes versus 32,229,324 bytes of original PNGs. Menu cards choose a responsive derivative; larger interaction previews retain original assets. Three local variable-font files total about 119 KB. No font CDN or remote 3D assets are requested at runtime.

## Source and build

- `static/css/app.css`: original application foundation.
- `static/css/redesign.css`: restaurant visual foundation.
- `static/css/immersive.css`: final premium tokens, interactions, responsive layouts, and dialog components.
- `static/css/food-experience.css`: ordered CSS entrypoint, compiled into one minified stylesheet.
- `static/js/experience.mjs`: presentation-only interactions and feedback.
- `static/js/food-studio.mjs`: standalone 3D illustration with no API, shopping, microphone, or audio access.
- `tools/build-studio.mjs`: builds the 3D/CSS assets and copies local font files/licenses.
- `tools/optimize-images.py`: optional Pillow authoring utility for responsive image derivatives.

Run `npm.cmd run build` from `website/` after source/style changes. Generated browser assets and optimized images are included; Pillow is not needed to serve the website. This repository has no JavaScript lint script. Changed Python files are checked with the configured Ruff rules, and changed browser modules receive syntax/build checks.

## Verification boundary

Browser checks use the existing offline fixture with fake provider/RTC boundaries and real app/worker behavior. They cover manual and assisted checkout, consent, media cleanup, switching modes, recovery, isolation, responsiveness, real WebGL controls, reduced motion, offscreen suspension, and WebGL fallback. They do not establish live provider audio quality or public deployment.

The retained local preview at http://127.0.0.1:8193 serves the website only. Voice still requires the existing orchestration/worker arrangement; the redesign does not launch or restart it.

## Premium redesign verification

- Production build: `npm.cmd run build` passed. The renderer bundle is 503,419 bytes (127,567-byte gzip estimate); the combined minified stylesheet is 126,369 bytes.
- JavaScript regression tests: 44 passed.
- Full offline Chromium suite: 58 passed in the final completed run, including the 18 new UI/3D checks.
- Python website tests: 39 passed again after the completed template asset switch.
- Ruff for changed Python files, JavaScript syntax, and Git whitespace checks passed.
- The narrow typed-input collapse was fixed by overriding both inherited column direction and full-width submit-button behavior. The final 375 px input measured 221 px.
- Final screenshots and browser layout/error reports are in `artifacts/premium-final/`.

## Texture finish

The texture pass replaces uniform surfaces with shared paper-fibre, painted-grain, and woven-linen SVG tiles (16,921 bytes combined). Textures are background-only, so they cannot intercept controls or alter text selection. The high-contrast preference removes decorative background images from reading and control surfaces.

The 3D food now uses deterministic color and bump maps generated once for the bun, crust, patty, lettuce, cheese, tomato, and ceramic plate. These add toasted pores, char/grill marks, leaf veins, seed detail, and surface roughness without image downloads or new dependencies. Maps are disposed with the renderer. Optional material/GPU initialization waits for the first authoritative menu render.

The finish is defined in `static/css/textures.css`, the shared SVGs in `static/img/textures/`, and the procedural food materials in `static/js/food-materials.mjs`. The existing build compiles them into the same CSS and 3D bundles. Current preview: http://127.0.0.1:8193/?design=texture-4. Texture screenshots are in `artifacts/texture-pass/`.

Production build, browser-module syntax, and Git whitespace checks pass. Ordering, backend, orchestration, and voice source modules remain unchanged.

Texture-pass verification: production build passed; 44 JavaScript tests and all 21 focused browser checks passed. Browser review recorded no page errors, confirmed texture backgrounds, and confirmed no horizontal overflow at 390 px. Existing ordering and voice source modules are unchanged.
