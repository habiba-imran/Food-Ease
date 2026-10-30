# FoodEase catalog artwork and lower-page redesign

The approved campaign hero is preserved byte-for-byte in the template; its markup SHA-256 is recorded in `artifacts/lower-section/approved-hero.sha256`. The new CSS is scoped to the collection, menu, ordering surfaces and lower sections.

The daily rotation now uses four large product cards with dedicated colored stages, transparent photography, prices, visible selection and keyboard-accessible controls. Category tiles, the full menu, item details and tabletop preview use the same artwork family. The cart, comfort controls and assistant panel have coordinated spacing and surfaces. Existing action hooks, catalog data, prices, availability and voice/session implementations remain intact. The sole app.js change is its presentation-only image URL helper.

## Saved assets

Built-in ImageGen generated 27 individual food photographs. The approved hero artwork was reused for `zinger-classic` without changing the hero asset. All 28 production assets are saved inside `website/static/img/catalog/` as alpha-preserving `-320.webp`, `-640.webp` and `-960.webp` derivatives (84 files). Original image files were retained. No broken legacy cutouts or sprite crops are used in the new catalog.

`website/tools/prepare-catalog-photos.py` performs only alpha-bound framing and responsive format preparation; it does not generate or repair food. Its input provenance is in `artifacts/lower-section/photo-manifest.json`. The complete contact sheet is `artifacts/lower-section/new-photos-contact.jpg`.

## Prompt set

Tool: built-in ImageGen, transparent background enabled. One request per product; connection failures were retried. Images are illustrative studio artwork for this HCI project.

Common prefix:

Use case: product-mockup. Create one high-end, photorealistic commercial food photograph as a transparent-background cutout for a premium food-ordering website. Subject: 

Common suffix:

 Composition: one complete food item or its specified dish, centered in a square image, viewed from an appetizing front three-quarter angle, entire silhouette and all bowl handles visible, 12 percent transparent margin around every edge. Natural warm studio key light from upper left, gentle fill from right, crisp true food textures, balanced colour, tasteful professional food styling. Genuinely transparent background with preserved alpha. NO background, NO table, NO rectangular photo border, NO lettering, NO price, NO logos, NO utensils, NO hands, NO floating unrelated ingredients, NO hard cast shadow outside the food. Not a cartoon, not a low-poly 3D render, not a plastic toy. Focus sharply on the product; retain natural material detail and appetizing realism.

Each subject below was inserted between the prefix and suffix:

- **wrap-hot-chicken**: One grilled tortilla wrap with crispy spicy chicken, lettuce, red chilli and creamy mayo, cut into two halves to reveal the filling; natural char lines on tortilla.
- **biryani-chicken**: Pakistani chicken biryani: fragrant long-grain basmati rice with golden saffron rice, a realistic chicken leg and caramelized onion; in one shallow matte charcoal ceramic bowl.
- **dessert-gulab**: Two authentic gulab jamun, deep golden brown with a glossy sugar syrup coating, in one small matte charcoal ceramic dessert bowl, a restrained edible pistachio garnish.
- **burger-beef**: One double beef smash burger with two thin craggy seared beef patties, melted cheddar, lettuce, tomato and sesame brioche bun; convincing juicy grilled textures.
- **zinger-supreme**: One premium crispy chicken zinger burger with a thick craggy golden fried chicken fillet, a melted cheese slice and creamy sauce, fresh lettuce and sesame bun.
- **burger-veg**: One vegetarian chickpea patty burger with a visibly textured chickpea patty, lettuce, tomato and sesame bun; not meat.
- **burger-soldout**: One smoky BBQ beef burger with grilled patty, dark barbecue sauce, caramelized onions and lettuce in a sesame bun.
- **wrap-chicken**: One grilled chicken tortilla wrap cut into two clean halves, with juicy grilled chicken strips, lettuce, tomato and creamy sauce, natural tortilla grill marks.
- **wrap-veg**: One vegetarian tortilla wrap cut into two halves, with colourful roasted vegetables, lettuce and a light sauce, appetizing real vegetable textures.
- **roll-seekh**: One Pakistani seekh kebab paratha roll cut into two halves, showing a chargrilled minced meat seekh kebab with sliced onion and green chutney.
- **roll-paneer**: One vegetarian paneer tikka paratha roll cut into two halves, showing golden grilled paneer cheese cubes, sliced onion and peppers.
- **roll-chicken**: One Pakistani chicken tikka paratha roll cut into two halves, with red-gold chargrilled chicken tikka pieces and onion.
- **karahi-chicken**: Authentic Pakistani chicken karahi with chunks of chicken in rich reddish tomato-based gravy, fresh ginger julienne and restrained green chilli garnish, in one small black iron karahi with two handles.
- **karahi-mutton**: Authentic Pakistani mutton karahi with realistic tender mutton pieces in thick dark reddish brown gravy and ginger julienne, in one black iron karahi with two handles.
- **biryani-beef**: Authentic beef biryani: long-grain basmati and saffron rice with tender brown beef chunks and caramelized onion, in one shallow matte charcoal ceramic bowl.
- **drink-lassi-small**: A single small clear straight-sided glass of creamy plain sweet lassi, ivory white with a subtle natural frothy surface; no fruit, no toppings, no straw.
- **platter-family**: One family mixed grill platter on a large matte charcoal oval plate: Pakistani chicken tikka, seekh kebabs, grilled chicken pieces, naan at the back and a small amount of onion salad. Show the entire platter.
- **drink-chai**: One clear handled glass cup of hot Pakistani karak chai, warm caramel milk-tea colour, subtle surface foam and delicate steam, no saucer or props.
- **drink-cola**: One unbranded clear cylindrical tumbler of dark brown cola with realistic ice cubes, fizzy bubbles and light condensation, no text or logos, no straw.
- **drink-mango**: One clear glass tumbler of thick bright golden mango juice, completely liquid with a smooth surface and subtle condensation, no fruit pieces or decorative garnish.
- **dessert-kheer**: Authentic Pakistani rice kheer: creamy ivory rice pudding with visible soft rice texture in one small matte charcoal ceramic bowl, restrained traditional nut garnish.
- **dessert-brownie**: One generous square of dark chocolate walnut brownie with a moist fudgy crumb, a little glossy chocolate sauce and a few walnut pieces, on a small matte charcoal ceramic dessert plate.
- **dessert-mystery**: One understated seasonal Indian/Pakistani creamy milk sweet, presented as a small ivory dessert in a matte charcoal dessert bowl. No labels and no identifiable fruit or nuts; emphasize smooth cream texture.
- **side-fries**: One serving of crisp golden masala fries with fine spice seasoning, in a shallow matte charcoal ceramic bowl, no sauce or other food.
- **side-salad**: One fresh mixed vegetable salad with crisp lettuce, cucumber, tomato, onion and carrot, in a small matte charcoal ceramic bowl.
- **side-raita**: One serving of creamy white yogurt raita with subtle herbs and cucumber flecks, in a small matte charcoal ceramic bowl.
- **soup-corn**: One serving of golden creamy sweet corn soup with visible corn kernels and a small amount of fresh green herbs, in a small matte charcoal ceramic soup bowl.

For `zinger-classic`, see the original generation prompt in `docs/EDITORIAL_ARTWORK.md`.

## Verification

- Production build passed.
- 44 JavaScript tests and 39 Python website tests passed.
- Full 58-test browser regression suite passed, including checkout, consent, and voice recovery using offline provider fixtures. This is not live microphone/provider acceptance evidence.
- Final image decoding and responsive audit: `artifacts/lower-section/image-audit.json`.
- Final desktop/phone screenshots and dialog examples: `artifacts/lower-section/`.

