# Zara behavior review — 8 November 2026

This follow-up compared the requested Urdu assistant behavior with the current integrated
implementation. It preserves the website design, providers, v2 contract, shopping authority
and existing session lifecycle. It does not rebuild the older standalone demo.

## Current implementation and targeted changes

The default LLM is **Groq `openai/gpt-oss-20b`**, not a provider called “Drop”. Gemini
remains selectable. Urdu recognition already uses Groq `whisper-large-v3-turbo` plus Silero
VAD. Cartesia already uses the configured voice and `sonic-3.6`, with `language=ur` and
Urdu-aligned timestamps disabled. Provider clients and credentials were not replaced.

The existing LiveKit tools already use the website's actual catalog, session cart, fees,
prices, stock flags and demo checkout through correlated, revision-checked actions. Model
conversation history, delivered-list references, interruption ownership, duplicate guards,
explicit checkout consent and recovery were retained.

Changes:

- Expanded the central integrated Urdu policy: Zara's identity, feminine self-reference,
  everyday Pakistani Urdu, common borrowed words in Urdu script, brief contextual replies,
  patience with uncertainty/corrections/budget concerns, and varied wording. No rotating
  phrase pool, synthetic laughter, artificial delay, invented age or human identity.
- Updated the Urdu welcome, short invitations and cart/review wording. The first spoken
  chooser introduces Zara once. Safety-critical summaries remain application-controlled.
- Added optional **Enable Hey Zara** controls within the existing welcome and voice panel.
  No speech recognition or automatic microphone access occurs on page load.
- Added browser recognition lifecycle ownership, Urdu/Roman-script wake matching,
  discarded ambient/interim transcripts, duplicate activation latching, native microphone
  release before LiveKit capture, cross-tab lease reuse, bounded restarts and accessible
  permission/unsupported-browser/autoplay errors. Only the wake utterance's addressed
  command is forwarded; a bare name opens the normal voice conversation.
- Fixed the floating speaking/thinking state so it survives removal of the old debug
  status element. A single panel live status announces wake errors without duplicate
  status regions; microphone-closing feedback never claims that capture is already off.
- Added code validation for Roman Urdu references, including `pehla`, `doosra`, `isko`
  and `uske`, with punctuation handling. These use the delivered order and current state;
  ambiguous or stale references still require clarification.
- Added finite Roman Urdu checkout affirmations. A correction or question does not count
  as consent. The delivered-summary, revision and cart-hash checks still apply.
- Added verified result sorting to existing search/filter tools: ascending price,
  descending price or name. This sorts returned facts and spoken-list memory, without
  changing application prices or the frozen wire contract. Truncated results must still
  be disclosed and narrowed before claiming a whole-menu cheapest choice.
- Extended the supplemental speech outcome guard for casual Urdu add/order/success claims.
  A success claim still needs a correlated successful result for the operation and turn.
  This guard is an additional check, not a general semantic fact verifier.
- Normalized grouped PKR/Rs amounts and removed common director/SSML/Markdown formatting
  before speech. Decimal digits are preserved. Captions and speech retain the same words.
- Rebuilt browser CSS, refreshed public asset mirrors and versioned changed entry assets.

## Voice and wake lifecycle

1. Entry shows the existing accessible mode chooser. Start Voice Assistant is the explicit
   microphone/playback gesture and speaks the Urdu welcome; manual and typing are available.
2. In manual browsing, enabling Hey Zara opts into browser recognition and acquires the
   existing assistance lease. The visible status distinguishes starting, listening and off.
3. Only a final utterance beginning with a bounded address is accepted: `Hey Zara`, `Zara`,
   `Zara suno`, `Zara meri baat suno`, and Urdu-script equivalents. Ordinary mentions later
   in a sentence and `ذرا` are not wake addresses. Other transcripts are discarded.
4. Recognition is aborted and its native end event awaited before releasing the lease and
   starting the existing bound voice session. If release cannot be established, capture
   fails closed. Late results and repeated triggers cannot dispatch another session.
5. The existing voice session handles successive turns and interruptions. Browser wake
   recognition is off throughout that session, including Zara's TTS playback.
6. End, manual selection, page hiding and page exit disable wake listening. It is a
   per-page opt-in and must be enabled again after the conversation; it never silently
   reopens on a return visit. Pause does not start a second listener.

## Actual ordering capabilities

The existing thirteen application operations remain authoritative: navigation,
search/filter, selection/details, cart read/add/set quantity/remove, checkout summary,
demo submission, undo and fresh context. Category reading is a validated local control
over actual navigation/category context. A multi-product request executes sequentially;
later writes stop on ambiguity, failure or uncertainty. Unknown writes are reconciled
using their original IDs rather than automatically retried.

Menu budgets/categories, item descriptions/availability, cart quantities and service fees
come from the website. Unsupported variants are not invented. Checkout is still a
**simulated demo**, with explicit confirmation of a delivered current summary. It collects
no payment and sends no restaurant order. This work adds no real payment, inventory or
authentication bypass.

## Browser and provider limits

Web Speech recognition is not available in every browser. Its service may require network
access, microphone permission and Urdu support, and may process audio remotely; the UI
discloses that before opt-in. It is not a guaranteed offline wake-word engine. HTTPS or
localhost is required. False activation rates and physical microphone quality need real
device testing. Button and typing fallbacks remain available.

Urdu Whisper is non-streaming; existing VAD/endpointing and provider/network delays remain.
No latency improvement or Pakistani accent/listening score is claimed. The existing
Cartesia voice was retained. Cartesia documents emotion tags as English-only, so this
change uses Urdu wording and punctuation rather than unsupported Urdu emotion tags or
an unmeasured global speed adjustment. Listen with a fluent Urdu speaker before calling
the delivery human-like. Untranslated new catalog labels still require Urdu display labels
for exact Urdu checkout delivery; that existing path fails closed rather than approving
an incomplete summary.

Sources checked against the installed Cartesia plugin 1.8.4:
[Cartesia speed/emotion guidance](https://docs.cartesia.ai/build-with-cartesia/capability-guides/volume-speed-emotion),
[LiveKit Cartesia API](https://docs.livekit.io/reference/python/livekit/plugins/cartesia/index.html),
[browser recognition and remote processing](https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API/Using_the_Web_Speech_API),
[native recognition abort](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition/abort).

## Changed files

Runtime and language:

- `voice-agent/src/foodease_agent/integrated/{agent,policy,runtime,output}.py`
- `voice-agent/src/foodease_agent/{i18n,reference_language}.py`
- `voice-agent/src/foodease_agent/locales/ur.json`
- `voice-agent/src/foodease_agent/speech_text/sanitizer.py`

Browser:

- `website/static/js/{app.js,wake-word.mjs}` and matching `public/static/js` mirrors
- `website/static/css/voice-assistant.css` and its public mirror
- Built `website/static/vendor/food-experience.css` and its public mirror
- `website/templates/index.html`

Verification and records:

- `voice-agent/tests/test_zara_followup.py`
- `voice-agent/tests/test_integrated_conversation.py` (explicit simulated stock loss;
  the currently shipped catalog is fully available)
- `website/tests/{wake-word.test.mjs,browser_server.py,test_app.py}`
- `website/tests/browser/{wake-word.spec.mjs,voice-entry.spec.mjs}`
- `website/docs/voice-audit-evidence/mobile-controls.png` (browser-generated snapshot)
- This review, worker evidence report, `voice-agent/docs/STATUS.md` and ADR-0026.

## Verification

Final executed results and the twenty-scenario coverage map are recorded in
[the worker evidence report](../../voice-agent/evidence/zara-followup-2026-11-08/report.md).
Browser tests use real application authority and the actual SDK/runtime with fake RTC,
recognition and a deterministic local model. They do not measure real-model interpretation,
Urdu STT/TTS, physical echo cancellation or human screen-reader/listening quality.

Restart the existing local launcher/worker to load the changed policy and language code.
No environment changes, dependency installation, provider request, push or deployment was
performed. Live provider and fluent-speaker acceptance remain required.
