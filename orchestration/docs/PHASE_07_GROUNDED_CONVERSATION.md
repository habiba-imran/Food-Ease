# Final orchestration Phase 7: grounded conversation

Scope: Phase 7 implementation only. No UI redesign, new shopping operation,
provider migration, Phase 8 recovery implementation or Phase 9 deployment work.
Earlier uncommitted Phase 4–6 work is retained on
`codex/phase-7-grounded-conversation`.

## Runtime behavior

The live worker now supplies `semantic_page`: current location and selection,
useful semantic buttons, navigation targets, filters, a small result sample,
authoritative cart and up to eight verified item-detail records. The original
snapshot remains bounded by v2. Its visible count is never called a whole-catalog
count. Detail/ingredient data comes from `get_item_details`; unavailable ingredients
remain unknown, without dietary/allergen assurances.

Exact orientation commands, next/previous, supported Add to cart commands and
presented ordinal selection run through the same owned action broker as model
tools. Page reading first verifies context. A selected-item read also verifies
details; cart/checkout reading includes actual quantity and fee-inclusive total.
The resulting action is reflected by the existing website renderer. Unsupported
camera/payment controls are explained without inventing an operation. Other
paraphrases continue through the real streaming model path, whose quality still
needs the separate live campaign below.

`BrowseMemory` separates returned candidates from completed output. Tool results
alone cannot establish a spoken list. Completed SDK output is matched against
full current product names and their pronunciation variants; overlapping names
such as Zinger Burger and Zinger Burger Supreme preserve their actual order.
Only those delivered names become ordinal references. Interrupted/unmatched
output does not grant a new list. A manual context change clears references and
cached details; the assistant must clarify or present the current options again.
Completion is local SDK/caption evidence, not proof a person physically heard audio.

Next/previous presents up to three options from the bounded current view. Previous
uses completed windows, and next excludes previously presented candidates.
There is no invented paging beyond the website's current 25-item snapshot.

The thirteen existing tools support recommendation/comparison and dependent
shopping requests. Recommendations use returned price, descriptors and stock;
comparisons can read each item separately. The actual prompt asks for one useful
follow-up, one to three short sentences by default, restraint with acknowledgments,
and no upselling, fake fillers, invented ingredients or human identity claim.
No scripted planner is installed in the live runtime.

Filter refinements preserve existing category/tags/budget/search. The wrapper can
replace tags and explicitly clear only budget, category or search. Deferred filter
arguments are merged inside the broker's serialized lane against refreshed state,
so overlapping tool invocations cannot silently discard an earlier refinement.
The frozen wire shape is unchanged. Quantity corrections use the current selected
or last verified cart item when unambiguous; stale/ambiguous references clarify.

Each turn has a bounded eight-operation budget and records normalized mutation
arguments. An identical mutation cannot execute twice in one turn. A failed or
ambiguous step blocks subsequent mutations in that turn while allowing read-only
inspection; unknown results still use the existing original-ID reconciliation.
New explicit user turns remain distinct requests. The SDK `max_tool_steps=8`
supports finite multi-step turns; the existing broker/consent/delivery gates remain.

## Streaming speech and preferences

The existing shaping/pronunciation functions now operate at the bounded sentence
boundary before the TTS/transcription split, and on static runtime utterances.
Tool chunks remain unchanged. The pipeline does not wait for a whole response to
polish it. PKR amounts become explicit English words; both fractional digits are
spoken, so 350.05 cannot become 350.5. Captions follow the actual shaped/aligned
words, without changing timed transcription objects downstream. The written cart
still displays its normal numeric totals.

Production Sonic 3 model configuration declares speed/volume capability based on
the installed public SDK. Controls invoke real `TTS.update_options`, retain their
requested setting, and acknowledge only accepted configuration updates. Unsupported
capability or rejected options produce an honest fallback. This verifies configured
behavior, not a measured perceptual change in live audio. English/PKR remains the
core; no bilingual STT/TTS quality claim is added.

APIs were checked against the installed 1.8.4 SDK source and public signatures,
with current official references for
[pipeline nodes](https://docs.livekit.io/agents/logic/nodes/),
[Cartesia](https://docs.livekit.io/reference/python/livekit/plugins/cartesia/index.html)
and [Google](https://docs.livekit.io/reference/python/livekit/plugins/google/index.html).

## Verification and live campaign

From the repository root:

```powershell
.\voice-agent\.venv\Scripts\python.exe orchestration/tools/phase7_verify.py --output orchestration/evidence/final/phase-07/run-2
```

See [verification report](../evidence/final/phase-07/report.md). The runner disables
dotenv, strips provider credentials and preserves historical contract/evidence
trees, including legacy dialogue outputs. It reruns V4.4/V4.5 safety and legacy
DS-01–25 families, the new actual-worker cases, and actual website/browser checks.
Legacy scripted metrics and local fake-model browser tests are not model-quality
or human listening results.

The separate campaign is prepared at
`evidence/final/phase-07/campaign-prepared/`: 41 cases and 50 planned turns using
the current fictional catalog. It covers varied preferences, recommendations,
comparisons, quantities, corrections, combined requests, page orientation,
unsupported controls and unsafe checkout/invented-success requests. Onboarding
and silence are covered by the Phase 6 tests retained in the gate. DS-21–25's
legacy fault wording is rerun; actual provider-failure exercises remain Phase 8.

Preparation makes **zero** provider calls:

```powershell
.\voice-agent\.venv\Scripts\python.exe orchestration/tools/phase7_campaign.py --output orchestration/evidence/final/phase-07/new-campaign
```

Only after explicit provider-cost approval and a Google key already configured in
the launching environment, use a fresh directory and the selected real model:

```powershell
.\voice-agent\.venv\Scripts\python.exe orchestration/tools/phase7_campaign.py --live --allow-provider-cost --model YOUR_CONFIGURED_MODEL --thinking-level minimal --max-provider-requests 160 --output orchestration/evidence/final/phase-07/live-text-1
```

The runner never loads `.env`. Both SDK and Google HTTP retries are disabled for
this campaign. It caps model requests and output tokens, records real model turns
separately from deterministic controls, and uses actual website HTTP authority and
the integrated SDK agent/tools. Its summary receipt is explicitly headless text;
it is not a browser or audible delivery proof. Operation-family checks are limited
automatic diagnostics; review arguments, final carts, false claims, unnecessary
clarification and duplicate effects in the retained traces before scoring quality.

The live quality gate remains open: obtain at least 40 actual model turns, inspect
critical factual/consent errors, then have at least three listeners rate sampled
actual provider/browser replies for naturalness, relevance, brevity and comfort.
Use anonymous listener IDs and real playback/session references in
`listening-ratings.csv`; duplicate rows for additional listeners. Record sample
sizes and medians (target at least 4/5) and retain failures. Blank rows are not
ratings. No recordings are enabled automatically. A successful text campaign still
does not establish STT accuracy, spoken pronunciation or live audio naturalness.

No Google key was loaded in this execution environment; no real-model campaign
or human panel ran. Implementation and live quality are separate gates.

## Remaining work

After Phase 7 implementation, **two planned phases remain**:

1. **Phase 8:** real provider/bridge faults, interruption, reconnect/reload,
   expired credentials and uncertain outcomes, with no duplicate effects or late
   speech. This is substantial remaining reliability work.
2. **Phase 9:** reproducible bring-up/handoff and joint real-browser acceptance,
   desktop/phone and keyboard/screen-reader checks, plus measured live greeting,
   response and interruption performance.

Phase 7's real-model/listener gate and earlier live activation checks are also
still open; phase counts are not a percentage of remaining effort. Zainab's visual
polish/animations remain a separate UI track. No next phase has been started.
