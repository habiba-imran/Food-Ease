# FoodEase voice integration — 4 November 2026

The existing LiveKit implementation has been completed at its website entry and
control surfaces, with focused lifecycle and mode-selection fixes. The production
path still uses real LiveKit, Deepgram, Gemini, Cartesia and the real website
authority. No simulated assistant was added to production.

Local verification establishes browser behavior and application integration.
Real speech recognition, provider responses, audible output and physical-device
acceptance remain separate, unperformed live checks.

## What already existed

- FastAPI/Jinja2 website with owner-bound shopping sessions, one serialized action
  queue and authoritative cart/checkout/receipt state.
- Session service that mints short-lived, role-bound app/user/agent LiveKit seats
  and dispatches the named integrated worker after consent/readiness checks.
- Python LiveKit Agents runtime with Deepgram STT, Google Gemini reasoning,
  Cartesia TTS, Silero VAD and supported interruption/turn-taking controls.
  Config A uses Flux turn detection; config B uses Nova-3/VAD/turn detection.
  Provider/model selections remain environment-driven and unchanged.
- Thirteen structured application operations: navigation, menu search/filter,
  selection/details, cart reads/add/remove/quantity, checkout summary/confirmed
  demo submission, undo and context refresh. All changes go through the same
  website authority used by manual ordering.
- Deterministic opening choices and control intents, verified result handling,
  checkout consent bound to a delivered current summary, original-ID recovery,
  canonical captions, single attachment of remote audio, reconnect barriers and
  immediate local media shutdown.
- Explicit recording opt-out in the integrated SDK session (`record=False`),
  and no browser capture before an explicit voice action.

This architecture was reused. Dedicated LiveKit transport and application
contracts were not replaced or expanded.

## Missing/broken behavior and fixes

| Finding | Fix |
| --- | --- |
| Ordering choices were buried under optional features and no persistent voice launcher existed | A visible welcome appears before the existing hero, with manual, spoken welcome and typed choices. A fixed microphone button remains available while browsing and after choosing manual. |
| Existing native shopping dialogs would make a body-level floating button inert | The same launcher moves to a normal inline position in the current shopping/preview dialog. Its control panel uses a native dialog, Escape, explicit close, return focus and existing background scroll locking. |
| No cohesive connecting/listening/speaking/error control surface | Labels derive from the existing lifecycle owner, canonical agent status and its actual microphone tracks. The panel exposes pause/resume, typing, manual and end actions. Significant connection/pause transitions and errors use accessible status messages; speech-state changes are not repeatedly announced as live alerts. |
| Common full-sentence mode choices were not recognized | Added precise, whole-utterance phrases including “I'd like to order using voice” and “I'd like to order manually.” Negated/ambiguous replies remain unselected and receive one clarification. |
| Choosing voice from the spoken chooser could restart a generation or leave browser mode unchanged | The existing control switches the current generation; the worker acknowledges the actual mode through the existing control event. No new contract field or duplicate dispatch is needed. |
| Failed server teardown left no usable explicit retry | A new user-requested start first reconciles pending cleanup, then creates one replacement. Cleanup failure blocks replacement. A later manual/end action cancels that pending start before it can reopen the microphone. |
| An undelivered mode-control request could leave capture active while showing Retry | The failure handler ends any still-active owner before offering retry. A native synthetic-media regression verifies the tracks end. |
| Microphone feedback was not updated immediately after permission completed | The lifecycle emits its connecting state with actual microphone activity before server preparation, and the UI reads tracks owned by that same controller. |
| Permission/device/network errors were hard to interpret | Permission denial, missing/busy devices and unavailable services get concise messages with manual/typing alternatives. Voice remains restricted to HTTPS/localhost. |
| Captions/input inherited pale text or dark backgrounds in light/high-contrast dialogs | Scoped transcript/form styles now follow the existing theme variables. |
| Conversation instructions did not explicitly require missing quantity/customization clarification | The existing policy now asks for missing quantity, resolves ambiguous dishes and offers only customization options actually returned by the application. |

Manual selection stops capture and playback immediately. Its brief acknowledgment
is accessible text/status; the implementation does not hold the microphone open
to synthesize an exit message. The floating button requires another gesture to
restart. Closing only the control panel leaves a deliberately active session
running, with its state still visible on the launcher.

The catalog currently has **no variants or add-ons**. The assistant must describe
a dish as served as listed rather than inventing extras. Menu facts, fees and
cart totals continue to come from the website, never a second voice cart.

## Files changed in this voice pass

- `website/templates/index.html`: welcome, floating launcher, native voice controls
  and inline launcher locations inside existing dialogs.
- `website/static/js/app.js`: connects those controls to the existing controller,
  moves the original typed form/transcript into the active control surface,
  presents state/errors and acknowledges manual exit.
- `website/static/js/voice-ui.mjs`: pure, unit-tested state/error presentation.
- `website/static/js/assistance-controller.mjs`: explicit cleanup retry, late-start
  cancellation guard and microphone feedback during connection.
- `website/static/css/voice-assistant.css`, `food-experience.css` and rebuilt
  `static/vendor/food-experience.css`: scoped voice UI styles.
- Matching `website/public/static` copies of the changed browser assets.
- `website/tests/voice-ui.test.mjs`, `tests/opening.test.mjs` and
  `tests/browser/voice-entry.spec.mjs`: presentation, retry/cancellation and nine
  new browser regression scenarios.
- `website/tools/voice-audit.mjs`, the `--voice-audit-only` mode in
  `tools/browser-test.mjs`, and `docs/voice-audit-evidence/`: native
  accessibility snapshots, measured solid-color text pairs and screenshots.
- `voice-agent/src/foodease_agent/integrated/runtime.py`: precise mode phrases,
  welcome wording and acknowledgment of an actual requested mode switch.
- `voice-agent/src/foodease_agent/integrated/agent.py`: the four concise quantity,
  ambiguity and real-customization policy instructions.
- `voice-agent/tests/test_integrated_opening.py`: expanded mode/ambiguity tests.
- Worker status/decision/evidence notes and this handoff.

No private environment file or credential was inspected or changed. No provider,
dependency version, catalog, business-authority or API contract was changed.
Existing manual-interface work and unrelated local changes were preserved.
Nothing was pushed or deployed.

## Executed verification

| Check | Result |
| --- | --- |
| New voice-entry Chromium scenarios | 9 passed: welcome, manual exit, pause/resume, reactivation/current cart, permission retry, same-generation choice/status, failed-control capture cleanup, failed-cleanup retry and mobile dialog access. |
| Complete Chromium regression suite | 80 passed (5.1 minutes). |
| JavaScript unit/transport/lifecycle tests (`npm test`) | 49 passed. |
| Focused integrated worker runtime/opening/conversation/recovery/RPC/output/startup tests | 102 passed. |
| Full worker suite, including safety/dialogue regressions after policy edits | 377 passed, 1 existing failure: `test_no_mock_imports_outside_adapters`. The legacy `integration/scenarios.py` imports a mock adapter; that file and the production website transport were not changed by this pass. |
| Website Python suite | 41 passed; existing Starlette/httpx deprecation warning. |
| Orchestration Python suite | 53 passed, 3 failed acceptance-generator tests. All three require `Zainab_Web_Application_UI_UX_Requirements_Specification (1).md`, already deleted in this checkout before this task. That user change was preserved. No orchestration source changed. |
| Scoped Ruff and pyright for changed Python source/tests | Passed; pyright reported 0 errors and 0 warnings. |
| Browser syntax and `npm run build` | Passed. |
| Source/public assets | Eleven matching asset pairs verified by hash. |
| `npm run test:browser -- --voice-audit-only` | 15 surfaces, 201 solid-color text pairs: zero contrast failures, zero overflow, zero page/console errors. The welcome fits above the fold at 375×812. Controls fit 320/375/768/1440px in light/dark/high-contrast themes. |
| `git diff --check` | Passed. |

The full worker and orchestration suites are therefore **not wholly green**. The
existing failures above are reported separately from the verified new flow.

The browser fixture uses the real website/domain, integrated worker, SDK session
logic and tools with local fake RTC/model services. Native synthetic browser
microphone tracks verify capture lifecycle and ending; prior playback tests use
generated media. Typed inputs in those scenarios exercise the conversation/tool
path, not real STT. This proves neither Deepgram recognition nor Gemini response
quality nor Cartesia/LiveKit audibility. Offline audio-IO warnings and a Windows
fixture connection-reset diagnostic are not reported as provider failures.

Human NVDA/VoiceOver use, physical microphones/speakers, actual vendor responses,
production hosting, naturalness ratings and audible interruption/latency have not
been tested. No latency or call-quality claim is made.

The visual audit is reproducible with `npm run test:browser -- --voice-audit-only`
from `website/`. It starts and stops its own offline fixture and never calls paid
providers. Its computed-color checks exclude images, gradients, partially
transparent text and disabled controls; they are not a complete WCAG audit.

## External configuration still required for live use

Presence and validity of private credentials were not inspected. Required names
are determined from the owning source and existing runbook:

| Component | Required/private configuration |
| --- | --- |
| Worker and session service, same LiveKit project | `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` |
| Worker speech/model credentials | `DEEPGRAM_API_KEY`, `CARTESIA_API_KEY`, `GOOGLE_API_KEY` |
| Worker model/voice settings | `STT_MODEL`, `LLM_MODEL`, `LLM_THINKING_LEVEL`, `TTS_MODEL`, `TTS_VOICE_ID` |
| Worker runtime settings | `VOICE_PIPELINE_CONFIG`, `IDLE_PROMPT_1_SECONDS`, `IDLE_PROMPT_2_SECONDS`, `SNAPSHOT_TIMEOUT_SECONDS` |
| Worker required flags | `RECORD_AUDIO=false`, `DEV_MODE=false`, `PREEMPTIVE_GENERATION=false`, `NOISE_CANCELLATION`, `GREETING_CACHE` |
| Website → session service | `ORCHESTRATION_BASE_URL` (local default `http://127.0.0.1:8090`) |
| Session service → website | `FOODEASE_WEBSITE_URL` (local default `http://127.0.0.1:8080`) |
| Session service/browser admission | `CORS_ORIGINS`, `LIVEKIT_AGENT_DISPATCH`, `FOODEASE_AGENT_NAME`; existing defaults and launcher wiring are documented in the final runbook. |
| Worker transport/routing | `FOODEASE_APP_TRANSPORT=website`, `FOODEASE_SESSION_API`, `FOODEASE_AGENT_NAME`, `FOODEASE_WORKER_PORT`; use the existing launcher to supply matching values. |

The website, session HTTP service and named integrated worker must be running.
LiveKit Cloud and the configured STT/LLM/TTS accounts must be reachable and have
usable models/quotas. Manual ordering needs only the website. Full live voice is
not supplied by a static frontend or website-only deployment.

The existing website/session authority is process-local and in memory. Use one
website process for this demo; independent serverless instances do not share
carts. No backend persistence redesign was included.

## Exact live test steps

1. Follow `orchestration/docs/FINAL_RUNBOOK.md` to install locked dependencies and
   privately configure the required names. Use the existing `.env.example` only
   as a template; do not overwrite existing private files or paste keys into chat.
   Download missing local VAD assets using the documented SDK command if needed.
2. In ordinary PowerShell, launch the existing real stack with explicit provider
   cost opt-in. This command was **not run** during this task:

   ```powershell
   Set-Location -LiteralPath 'C:\HCI-PROJECT'
   .\orchestration\.venv\Scripts\python.exe orchestration/tools/demo_up.py --mode live --launch --allow-live --duration 1800
   ```

3. Wait for all three service health checks and the worker's registered/ready
   state. In Chrome/Edge, open `http://127.0.0.1:8080`. Before choosing voice,
   verify no microphone capture or automatic playback occurs.
4. Choose **Start Voice Assistant** in the welcome. Grant microphone permission
   and verify the spoken welcome is actually audible. Say **I'd like to order
   using voice**. Confirm the session continues without a second greeting/dispatch.
5. Ask for available categories and a real dish's description/price. Try an
   ambiguous request and check that the agent clarifies. Ask for a quantity-less
   dish selection and check that it asks how many. No extras may be invented.
6. In a fresh cart, say **Add two Hot Chicken Wraps**. Verify two wraps, subtotal
   1700 PKR, service fee 50 PKR and total 1750 PKR. Check spoken and visible facts.
   Say **Actually make it one**, then verify one wrap and total 900 PKR. Try
   removal and verify the visible cart updates only after a successful action.
7. Say **I want to order manually**. Check capture/playback actually stop. Make a
   manual cart change. Reactivate with the floating button and ask for the cart;
   the assistant must use that current quantity and total.
8. Ask for checkout. Listen to the actual summary. A refusal, silence or correction
   must not submit. Request a fresh review and explicitly confirm only when ready.
   Verify the existing authority returns a demo receipt; no payment/restaurant
   order is performed.
9. Check pause/resume, End, permission denial/retry, a disconnected worker/session,
   interruptions and browser backgrounding. After End/manual, capture must remain
   stopped until another user gesture. Use Tab/Shift+Tab/Enter/Escape and a real
   screen reader to verify names, announcements and return focus.
10. For phones, use an actual HTTPS deployment reachable by the phone, with a
    matching HTTPS session-service URL/CORS configuration and a session service
    that can reach the website authority. A phone's localhost is not the PC.
    Stop the owned local stack with Ctrl+C or let the bounded run expire.

Keep actual live successes, failures and unmeasured results in a new evidence
directory. Do not substitute local synthetic tests for that acceptance record.
