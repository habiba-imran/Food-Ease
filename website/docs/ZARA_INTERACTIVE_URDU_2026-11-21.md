# Zara: interactive Urdu website actions

Implemented locally on 21 November 2026. No deployment, provider change, new dependency,
catalog/price change, or website redesign.

## Existing architecture and implementation

FoodEase uses a FastAPI/Jinja website with JavaScript modules, rather than React.
The existing Python LiveKit worker interprets Urdu, Roman Urdu and English, and replies
in Urdu. The existing microphone button, providers and connection lifecycle are retained.

The existing action path is reused throughout:

`Zara tool → IntegratedRpcAdapter → bound browser RPC → Application queue → shared
SessionStore/FoodEaseDomain → rendered website/context publication → correlated result → speech`.

Manual and voice actions use the same authoritative session cart. Product IDs, prices,
availability and totals come from the catalog/domain. Requests have stable action IDs,
strict argument schemas and revision checks. Existing result lookup reconciles a lost
response without repeating a mutation. A render failure cannot produce a successful
action RPC response. The agent's output gate also checks common Urdu/English outcome claims;
it supplements the result boundary and is not a general natural-language fact verifier.

Changes:

- Category navigation clears a conflicting product search. Successful voice browsing
  scrolls to the existing category/menu section even when the route was already `menu`.
  Home navigation scrolls to the existing top section. Missing sections fail delivery.
  Scrolling respects reduced-motion/calm settings and does not explicitly move focus.
- `popular` opens the existing `#popular` menu section. No popularity ranking is invented.
- Quantity increases now recheck authoritative availability; decreases/removal still
  work when an item becomes unavailable. Additions already checked stock in the domain.
- Confirmed voice cart changes show the existing toast in Urdu and announce current
  quantity/total through the existing active accessible status surface (`lang=ur`, RTL).
  Existing dialogs retain native modal focus and focus restoration.
- Clear-cart adds two allowlisted operations, using existing confirmation and undo logic:
  `cart.get_clear_summary` reads the real cart and opens the existing cart dialog;
  `cart.clear` clears atomically only with a current app-issued review token.
  The runtime delivers the Urdu review/question separately, then requires a later
  affirmative user turn after completed delivery. The token expires, is invalidated
  by cart edits, and is purpose-bound: clear consent cannot place an order and checkout
  consent cannot clear the cart. Repeated action IDs do not repeat a clear. Undo restores it.
- The Urdu policy and tool descriptions explain shopping/navigation references and
  the clear-cart review boundary. Menu meaning still belongs to the existing LLM;
  no production command phrase parser or arbitrary browser JavaScript was added.

## Supported requests

Examples describe supported intents; exact recognition/paraphrase accuracy needs live validation.

| Intent | Urdu / Roman Urdu examples |
| --- | --- |
| Add a named available product/quantity | «دو زنگر برگر کارٹ میں شامل کر دو»; `do zinger burger add kar do` |
| Contextual addition | «ایک اور شامل کرو»; `aik aur add kar do` when one item is unambiguous |
| Set/decrease quantity | «اس کی تعداد تین کر دو»; «ایک کم کر دو» |
| Remove a line or scoped group | «یہ والا ہٹا دو»; «کارٹ سے تمام مشروبات ہٹا دو» using current cart/catalog IDs |
| Open/read/close cart | «کارٹ دکھاؤ»; «کل کتنا ہوا؟»; «کارٹ بند کرو» |
| Clear whole cart | «کارٹ خالی کرو», then answer the delivered Urdu confirmation question |
| Navigate | «برگر دکھاؤ»; «میٹھا دکھاؤ»; «مینو کھولو»; «اوپر لے جاؤ» |
| Recommend/filter | «سب سے سستا برگر دکھاؤ»; «ایک ہزار روپے سے کم میں کچھ بتاؤ»; «تیز مصالحے والا کھانا دکھاؤ» |
| Follow a delivered recommendation | «پہلے والے دو شامل کرو»; `pehle wale do add kar do` |
| Checkout | Ask for checkout/review; a separately delivered current summary and explicit confirmation remain required |

Ambiguous products/references require clarification. Recommendations use real returned
descriptors, prices and availability; missing ingredients/options cannot be invented.
The catalog currently contains no required customization choices or live inventory service.
Availability is authoritative within the existing application catalog, not a connection
to a restaurant stock system. Checkout remains a demo: it does not charge a payment.

## Files

- `website/src/foodease_website/domain.py`: navigation, stock recheck, purpose-bound clear review/commit.
- `website/static/js/app.js`, `application.mjs`, `livekit-bridge.mjs`: rendering, Urdu status/toast,
  operation allowlist and verified typed clear-review delivery. Matching `website/public/static/js/`
  copies are synchronized; the template entry URL was advanced to `zara-26`.
- `voice-agent/src/foodease_agent/integrated/{agent,broker,runtime,output}.py`: tools,
  confirmation purpose, review delivery, navigation feedback and speech outcome checks.
- `contracts/src/foodease_contract/{enums,models}.py`: two new operations, strict review/clear
  argument/result validation, advertised action bound 15. Existing 13 operations are retained.
- `voice-agent/tools/freeze_contract_v2.py` and both `contract/v2` handoff trees: regenerated
  schemas and extension notes. Historical hash-pinned examples and v1 remain unchanged.
- New tests: `website/tests/test_interactive_actions.py`,
  `voice-agent/tests/test_interactive_urdu.py`, `website/tests/browser/interactive-urdu.spec.mjs`.
  Existing tool-count assertions were updated. `website/tests/browser_server.py` adds only
  test-fixture language selection and scripted Urdu tool decisions, never production routing.

## Verification

- Website Python: **49 passed** (one dependency deprecation warning).
- Browser JavaScript: **63 passed**.
- Full worker suite: **525 passed, one inherited failure** in `test_no_mock_imports_outside_adapters`:
  the unchanged legacy `integration/scenarios.py` imports the mock adapter.
- After the final navigation speech adjustment, Urdu/follow-up tests: **29 passed**.
- Existing browser voice entry, lifecycle, menu and footer/cart regressions: **39 passed**.
- Final Urdu desktop/mobile browser scenarios: **3 passed**. Manual ordering/checkout,
  keyboard-only flow and dialog focus: **12 passed**. Together with the existing
  regressions above, **54 distinct browser checks passed** across the final scoped runs.
- Changed production Python lint/type checks, JavaScript syntax checks, asset build and
  generated-contract checks passed. No speech-provider calls were made.

Browser tests use the real SDK session/tool runtime, RPC adapter, server cart and browser DOM,
with deterministic model decisions and fake RTC. Synthetic microphone lifecycle tests do
not establish physical Urdu STT/TTS quality, current Groq capacity, live Cloud connectivity,
human screen-reader acceptance or caller-heard latency. Those remain unperformed.

## Activation

Restart/redeploy the existing backend, browser assets and LiveKit worker together using
the existing hosting configuration. The two added operations enlarge the advertised v2
action list to 15; an old validator capped it at 13. Do not deploy only one component.
No environment variables, credentials, hosting settings, provider choices or live services
were changed by this task. Use the existing voice button after the matched components run.
