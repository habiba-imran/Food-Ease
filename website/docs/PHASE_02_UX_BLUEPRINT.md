# Phase 2 UX Blueprint

FoodEase should feel like a polished restaurant ordering product, not a plain
academic prototype. The visual direction is modern, elegant, slightly playful,
accessible, and 3D-ready. The visual inspiration now blends premium burger
ordering, editorial food layouts, red/gold hero panels, dark cuisine sections,
compact menu grids, and dish-first visual composition.

## Product Surfaces

1. Welcome and mode choice
2. Home and category discovery
3. Menu listing with search and filters
4. Item detail with future 3D dish preview
5. Cart and quantity controls
6. Demo checkout and confirmation
7. Assistance panel for consent, text, status, transcripts, and mock events
8. Mock-agent developer harness
9. Final 3D/AR enhancement surfaces

## Responsive Layout Rules

- Desktop: full restaurant-style hero, category rail, menu grid, sticky cart,
  assistant panel section.
- Tablet: stacked hero and cart, two-column menu when space allows.
- Mobile: one-column flow, large touch targets, horizontal nav where needed,
  no overlay that hides cart or checkout controls.
- Zoom/enlarged text: controls wrap instead of clipping.

## Visual System

- Food-forward colors: warm cream, deep ink/black, spicy red, gold, and
  controlled FoodEase green for accessible assistant/status cues.
- Buttons are bold and high contrast.
- Cards use food-ordering density: enough detail for scanning without clutter.
- The first viewport should show a clear brand, compact ordering promise,
  Start ordering CTA, and a large dish/plate preview rather than oversized text.
- Later image, 3D, and AR assets should replace CSS dish placeholders without
  changing the catalog item IDs or agent-facing action contract.
- Focus states stay strong and visible.
- Motion and 3D are progressive enhancements with reduced-motion fallback.

## Accessibility Intent

- Manual ordering must work before voice.
- All major areas have headings and landmarks.
- Assistant content must not create screen-reader announcement spam.
- No microphone or voice state is implied before explicit consent.
- The 3D/AR layer cannot be the only way to understand an item.

## Phase 2 Prototype Coverage

- Uses the real frozen catalog counts and featured items.
- Shows the future ordering shell, category filtering, menu search/filter
  controls, add-to-cart preview, cart totals, and assistant preview.
- Establishes the responsive design language for Phase 3 and Phase 4.
