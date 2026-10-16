# FoodEase Phase 15 Final Demo Rehearsal

Generated for Zainab's website seat on 2026-10-11.

This is the final presentation runbook. Use it to rehearse the website without
needing Habiba's live voice stack. If the LiveKit agent is ready on demo day,
use the optional integration path at the end.

## Demo Setup

Start the website:

```bash
cd website
uv run foodease-website
```

Open:

```text
http://127.0.0.1:8080
```

Before presenting:

1. Use Chrome or Edge desktop.
2. Set browser zoom to 100 percent for the main run.
3. Keep DevTools closed unless asked to show API evidence.
4. Refresh once to clear old UI state.
5. Keep `docs/PHASE_13_TESTING_AND_ACCEPTANCE_EVIDENCE.md` ready for marking questions.

## 90-Second Opening Script

> FoodEase is an accessible food-ordering website built manual-first and
> voice-ready. The key HCI idea is that blind users, low-vision users and manual
> users should share one reliable ordering system. The voice agent does not own a
> separate cart; manual clicks and mock-agent requests go through the same
> semantic operations, same catalog and same checkout state. The 3D and AR
> previews are progressive enhancements, so the project looks engaging but never
> depends on camera, speech or payment services to complete an order.

## Demo Path A: Complete Manual Order

Goal: prove the website works when all agent services are off.

1. Show hero carousel.
2. Click a hero dish and explain the selected item updates app context.
3. Scroll to menu.
4. Search `biryani`, then clear.
5. Filter `Vegetarian`, then `All`.
6. Open `Details` on any available item.
7. Show price, tags, ingredients and quantity.
8. Add quantity two from details.
9. Show cart preview total and service fee.
10. Increase/decrease quantity once.
11. Click `Demo checkout`.
12. Explain no payment is collected.
13. Confirm demo order.
14. Show receipt and cleared cart.

Expected pass:

- Cart total updates accurately.
- Checkout requires explicit confirmation.
- Receipt ID appears.
- No voice/mic/camera prompt appears.

## Demo Path B: Accessibility Controls

Goal: show accessibility is not just claimed.

1. Use `Tab` to move through header and hero actions.
2. Activate `Larger text`.
3. Activate `High contrast`.
4. Activate `Calm motion`.
5. Use cart/status live feedback after adding an item.
6. Press `Escape` to close dialogs.

Expected pass:

- Focus outline is visible.
- Text remains readable.
- Manual ordering still works.
- Controls are named and reachable.

## Demo Path C: Mock-Agent Contract

Goal: prove Habiba can connect a real voice agent later without rewriting the
website cart/domain.

1. Go to `Guide`.
2. Click `Start typed guidance`.
3. Click `Filter vegetarian under 800`.
4. Click `Add hot chicken wrap`.
5. Click `Ask checkout summary`.
6. Type `show burgers` in the text field and send.
7. Pause assistance.
8. Add or remove an item manually.
9. End assistance.

Talking points:

- These are simulated agent events, not real speech.
- They call the same `/api/app/action` endpoint as manual UI logic.
- Manual changes and mock-agent changes share one cart and revision state.
- No microphone starts before consent.

Expected pass:

- Transcript logs `agent.action_request` and `app.action_result`.
- Cart updates from mock action.
- Manual order remains usable after pause/end.

## Demo Path D: Contract Cockpit And Evidence

Goal: show technical correctness for integration/marking.

1. Go to `Agent readiness`.
2. Show revision, route, focus item, visible items and cart total.
3. Click `Reject sold-out item`.
4. Click `Reject stale revision`.
5. Click `Duplicate action ID`.
6. Go to `Evidence`.
7. Click `Run contract smoke`.
8. Download evidence JSON if needed.
9. Download context snapshot if needed.

Talking points:

- Duplicate action IDs do not double-submit mutations.
- Stale revisions are refused instead of overwriting newer UI state.
- Sold-out items fail honestly.
- Context can be handed over to the voice agent.

Expected pass:

- Trace log shows safe rejections.
- Evidence score updates.
- JSON export downloads.

## Demo Path E: AR And 3D Enhancement

Goal: show creative enhancement without breaking accessibility.

1. Return to hero.
2. Use the carousel arrows or food rail.
3. Click `View on table`.
4. Read the AR support message.
5. Rotate the tabletop preview.
6. Continue ordering.

Talking points:

- AR is optional and safe.
- Desktop browsers usually show fallback; supported phones may detect WebXR.
- Camera is not opened automatically.
- The selected dish remains connected to the same catalog item.

Expected pass:

- Clear fallback message if AR is unsupported.
- Preview image is sharp and not stretched.
- Cart/checkout are unchanged by opening AR.

## Mobile Check

Use browser device toolbar or an actual phone.

Screen widths to check:

- 390 px mobile
- 768 px tablet
- 1366 px laptop

Checklist:

- Header does not cover content.
- Hero text does not overflow.
- Food images are visible and not cropped badly.
- Menu cards stack cleanly.
- Cart preview is reachable.
- AR dialog fits the screen.
- Evidence console remains readable.

## Optional LiveKit Demo

Only use this if Habiba's stack is ready and internet/local services are stable.
Mock-agent is enough for website-side marking if live voice is not ready.

Expected integration path:

1. Habiba starts voice worker.
2. Zainab starts website.
3. Browser asks session API for an app token after explicit consent.
4. Website joins LiveKit room as app participant.
5. Website registers RPC `foodease.action`.
6. Agent sends semantic action request.
7. Website returns action result and publishes updated context.

Fallback sentence if live voice is unavailable:

> The live voice pipeline is Habiba's integration layer. For Zainab's website
> deliverable, the mock harness proves the same receiving/sending contract
> without needing live microphone, LLM, TTS or LiveKit services.

## Regression Fix Checklist

Run these before the final demo:

```bash
cd website
.venv\Scripts\python.exe -m pytest tests\test_app.py tests\test_domain.py
.venv\Scripts\python.exe -m ruff check src tests
node --check static\js\app.js
```

Manual regression list:

- Add item from card.
- Add item from detail dialog.
- Remove item from cart.
- Checkout and confirm simulated order.
- Open and close AR preview.
- Start/pause/end guidance.
- Run Evidence smoke.
- Resize to mobile.

## Presenter Notes For Common Questions

**Is this real payment?**

No. It is simulated checkout for an HCI demo.

**Is this real voice?**

The website has the contract/harness. Habiba's separate voice agent can connect
through LiveKit using the documented RPC and context topics.

**Why no automatic microphone?**

Because consent-first interaction and manual accessibility are project
requirements. Voice must be optional.

**Why AR fallback instead of always real AR?**

WebXR support depends on device/browser. The fallback ensures desktop and
assistive users still get a complete experience.

**How is the cart protected from agent mistakes?**

All mutations pass through the same domain rules: action ID idempotency, stale
revision refusal, availability checks and checkout confirmation tokens.

## Final Approval Checklist

Before submission, Zainab should confirm:

- Visual design feels modern, creative and restaurant-like.
- Manual path completes successfully.
- Mock-agent path updates the same cart.
- Evidence file and JSON exports are understandable.
- Known limitations are honest.
- Demo script matches the desired presentation style.
