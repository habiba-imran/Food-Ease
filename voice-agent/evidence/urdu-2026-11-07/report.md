# Urdu assistant and semantic menu interpretation — 2026-11-07

## Result and scope

The integrated website assistant defaults to Urdu through
`ASSISTANT_LANGUAGE=ur`, including existing installations whose private environment
does not have that setting. No private environment file was read or changed.
The production factory explicitly carries the language into the actual agent and
runtime. Setting `ASSISTANT_LANGUAGE=en` retains the earlier English pipeline.
Historical standalone MockApp/CLI tooling remains the English development harness.

The initial `integrated/menu_queries.py` English shopping parser was removed.
Free-form menu requests now share the streaming LLM/tool path. Instructions ask the
model to interpret paraphrases, synonyms, Urdu and Roman Urdu against actual
category/product data, distinguish broad categories from narrower products, use
canonical catalog search terms, and inspect/reformulate an empty literal search.
There is no menu synonym whitelist. Model interpretation remains dependent on the
selected provider's capacity and quality; offline tests do not prove real-model
paraphrase accuracy.

Existing tools now expose `read_all` for complete returned-list delivery and
`price_exclusive` for strict price ceilings. The strict boundary is calculated in
code. Truncated views remain explicitly disclosed. Tool names, the thirteen
operation allowlist, canonical IDs and wire contracts are preserved. Prices,
availability, cart totals and outcomes still come from correlated website results.

## Urdu pipeline and delivery

- Recognition: existing installed Groq plugin, `whisper-large-v3-turbo`, explicit
  `language=ur`. `URDU_STT_MODEL=whisper-large-v3` is also accepted. Urdu recognition
  requires `GROQ_API_KEY` even when the LLM provider is Gemini; Deepgram's key is
  not required for Urdu. No dependency was added.
- Turn handling: non-streaming Whisper through the SDK's VAD path with Silero;
  legacy Flux/Nova selection does not override Urdu. The English semantic turn
  detector is not constructed for this path.
- Synthesis: existing Sonic 3.6 and configured voice with explicit `language=ur`.
  The installed plugin's unsupported Urdu word timestamps are disabled, and SDK
  generated transcripts remain available for captions. The existing configured
  voice was retained; its Urdu accent has not been assessed.
- Replies: Urdu-only system instructions, Urdu punctuation streaming, Urdu number
  rendering and localized deterministic greetings, controls, cart summaries,
  confirmations, empty results, failures and recovery warnings. English number
  verbalization/pronunciation replacements are bypassed for Urdu. Latin-script
  model output is withheld with an Urdu retry message if it cannot be localized.
- Catalog display names and fixed interface messages are translations in
  `src/foodease_agent/locales/ur.json`. They are presentation data, never rules for
  accepting a user's shopping vocabulary. A coverage test checks all 28 current
  product names. A new untranslated checkout item/fee blocks confirmation instead
  of marking a fallback message as a delivered summary.
- Safety: finite Urdu stop/mode/reference controls remain deterministic. Exact
  Urdu affirmatives are recognized only after a verified summary is completely
  delivered. Corrections, negation and interrupted/undelivered summaries do not
  authorize checkout. The existing output guard also checks common Urdu outcome
  claims against current correlated operation results.

Website layout, catalog business data, cart math, credentials and deployment were
not changed. The assistant's captions are Urdu; website navigation/button labels
remain the existing website UI.

## Documentation consulted before provider changes

- [Cartesia Sonic 3.6](https://docs.cartesia.ai/build-with-cartesia/tts-models/latest):
  native Urdu support, `ur` language selection, existing voice/model compatibility.
- [Groq speech to text](https://console.groq.com/docs/speech-to-text): multilingual
  Whisper models and transcription rather than English translation.
- [LiveKit Groq STT](https://docs.livekit.io/agents/models/stt/groq/): plugin
  construction and explicit language parameter.
- [LiveKit Cartesia TTS](https://docs.livekit.io/agents/models/tts/cartesia/): plugin
  language and synthesis parameters.
- Installed 1.8.4 plugin sources: `groq/services.py`, `openai/stt.py`,
  `cartesia/tts.py`, and the SDK voice activity implementation. Actual constructors
  were also exercised without network requests.

## Verification

Commands were run from `voice-agent/`. Offline asyncio tests used local-socket
access outside the restricted sandbox; no provider API request was made.

```text
.venv/Scripts/python.exe -m pytest tests/test_urdu_assistant.py tests/test_integrated_menu_queries.py -q
32 passed in 9.90s

.venv/Scripts/python.exe -m pytest -q
414 passed, 1 failed in 37.25s
```

The full-suite failure is the previously documented
`tests/test_no_mock_leak.py::test_no_mock_imports_outside_adapters`, reporting the
existing import in `integration/scenarios.py`. That file was not changed. The
final focused run includes the subsequent factory-wiring and price-boundary tests.
The earlier focused safety/conversation/speech/configuration run passed 235 tests.

Changed Python files and new tests passed `ruff check`; scoped `pyright` returned
zero errors and zero warnings. `git diff --check` passed, with only existing Git
LF/CRLF notices. The first new-test run correctly failed on missing Urdu settings;
an intermediate run caught a test's incorrect attribute access on SDK's dictionary
turn options, which was corrected. Initial scoped type errors were resolved.

The tests exercise real website authority with fake media/model turns, actual
provider-client construction without network, factory language propagation,
localized complete captions, list references, strict/inclusive ceilings, unknown
categories, Urdu control handling, consent corrections and missing translations.
They do not measure recognition accuracy, real-model semantic accuracy, audible
latency or naturalness.

## Activation and remaining evidence

Restart the integrated worker and begin a fresh voice session to load this source.
No running process was restarted, pushed or deployed during this follow-up.
Live Urdu microphone recognition, model tool selection, synthesized pronunciation
and a human listening assessment remain unperformed. Existing provider quotas
still apply; moving interpretation back to the LLM does not remove model rate
limits. Existing unrelated working-tree changes were preserved.
