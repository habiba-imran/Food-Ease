# Zara's conversational Urdu personality — 2026-11-22

The user requested natural, playful, emotionally expressive Urdu instead of a
receptionist script. The active integrated policy now gives Zara a gently witty,
context-aware register and spoken Urdu examples for indecision, playful exchanges,
budget concerns and frustration. Humor is occasional; direct orders remain direct.
There are no invented human experiences, fake laughter, filler sounds or delays.

Personal recommendations and discussions can continue through the LLM after real
tool facts, rather than ending on a fixed tool receipt. Straightforward actions,
reads and lists retain the one-model fast path. Urdu opening/list/detail/cart
phrasing now fits the conversational register. Delivered checkout/clear reviews,
prices, quantities, consent, manual-action coexistence and interruption settings
retain their existing controls.

Cartesia's current documentation supports context-driven Urdu intonation in Sonic
3.6, but explicitly limits emotion tags to English. The existing voice/model/pace
are retained; expression comes from the actual Urdu wording and punctuation.
No unsupported emotion setting or spoken markup was added. Sources:
[expression controls](https://docs.cartesia.ai/build-with-cartesia/capability-guides/volume-speed-emotion),
[Sonic 3.6](https://docs.cartesia.ai/build-with-cartesia/tts-models/latest).

## Verification

- Full worker + website regression suite: **632 passed / one inherited failure**
  (`test_no_mock_imports_outside_adapters`, unchanged integration/scenarios.py).
  All existing dialogue/safety, native playout/manual-coexistence, Urdu shaping
  and one-versus-two LLM request tests were included. Raw output:
  [regression-tests.txt](regression-tests.txt).
- Scoped Ruff, Pyright (zero errors/warnings) and JavaScript syntax checks passed.

The hosted personality profile covers indecision, a budgeted recommendation,
playful conversation, a request to stop joking, and a real cart addition. It uses
the authenticated website/LiveKit/worker/provider path with synthetic recognized
text and a silent microphone. Successful synthesis and transcripts do not establish
human listening quality, physical microphone behavior or caller-heard latency.

## Live refinement

The first run completed two Urdu replies, then stopped on an audit assumption:
the recommendation used the current authoritative application context without a
new tool call. The next run explicitly requested filtering and successfully used
filter_menu and get_item_details. It then stopped on the same overly strict tool
assertion for a price already present in that returned context. Both retained
reports show actual outputs; neither is counted as a completely passing run.

The second run also caught an undesirable playful metaphor implying Zara adjusts
flavors and another purchase invitation after casual banter. Refined the prompt
to use a truthful playful pivot about her role, avoid repeated purchase questions,
and avoid invented texture/temperature/preparation claims. The final audit permits
a plain price reply from the current bound application facts, while the explicit
filter request and cart addition must still exercise real application tools.
Raw initial runs: [initial](hosted-initial.json), [refinement](hosted-refinement.json).

## Final deployment and hosted result

- Source **b6f0381**, pushed to origin/main, deployed code-only with existing
  Cloud provider settings. Final worker **sGUZJX5dppyG**, **Running / ap-south**,
  deployed at 2026-11-21 20:41:47 UTC (2026-11-22 local).
  [Deployment output](cloud-deploy.txt), [status](cloud-status.json).
- **All five hosted turns completed, zero audit errors and zero failed replies.**
  Indecision received a playful Urdu opening and a food preference question.
  Budgeted recommendation called filter_menu successfully and quoted returned
  PKR-200 mango juice and PKR-150 lassi. Casual banter used a truthful role-based
  line rather than claiming she tastes/cooks. The request to stop joking received
  the correct PKR-100 Cola price. The explicit add made one successful cart mutation,
  confirmed against authority: exactly one Cola, subtotal100, fee50, total150.
  [Complete final questions, replies, actions and cart](hosted-questions.json).
- Final bounded worker-log sample: **31 lines, zero ERROR/CRITICAL records**.
  [Redacted runtime sample](cloud-runtime.txt). Full regressions were rerun after
  the refinement: **632 passed / the same inherited mock-import failure**.
- Actual playful examples included “کھانا چننا بھی کبھی کبھی امتحان لگتا ہے!”
  and “میں تو مینو چھان لوں گی، مزے آپ نے لینے ہیں!” These are observed outputs,
  not promises that every response will use those words. Humor and description
  remain model-generated; this audit checks completion/actions and reviews text,
  not a general natural-language fact verifier or a human naturalness score.
- No website product assets, providers, recording controls, interruption thresholds
  or dependencies were changed. The browser audit used matched zara-34 assets.
  Restart an existing voice session to load the new agent instructions.
