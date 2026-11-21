# Zara corner widget and startup lifecycle fixes

21 November 2026. The welcome/mode-choice banner and all Hey Zara controls are removed.
The browser no longer instantiates native wake speech recognition. Manual shopping
is immediately available with the microphone off.

The bottom-right microphone icon opens one compact, non-modal card. Start, microphone
permission/setup, session preparation, agent startup, listening, user speech, thinking,
speaking, pause, retry/error and end states appear there. The same card contains the
canonical transcript and optional typed requests. Opening/minimizing the card does
not start/end a conversation; Start Zara explicitly requests microphone access.
Pause and End control the real existing voice session. No separate voice dialog,
backdrop, body scroll lock or second transcript/cart is created.

When a native shopping dialog is open, the same widget is relocated into its existing
accessibility slot so its controls remain usable instead of becoming inert. The
floating cart is positioned beside the voice icon so an expanded card does not cover it.
Escape minimizes the widget, focus returns to its icon when appropriate, and reduced
motion suppresses the connecting/speaking animations. Urdu caption direction is automatic.
Existing providers, worker tools and shopping/checkout rules are unchanged.

## Connection investigation

A fresh synthetic-microphone browser session against the hosted site reached
`voice_active` in approximately 11 seconds before these changes. It recorded no
failed-resource response or uncaught JavaScript exception. The supplied 404 therefore
has not been tied to a particular resource and is not claimed to have a proven cause.
The supplied disconnect messages alone do not demonstrate a bad internet connection.

Three application lifecycle defects were reproduced with deterministic tests:

1. Disconnect started `unpublishTrack` negotiation immediately before closing the
   same peer connection. Teardown now stops capture synchronously and lets room
   disconnection clean up publication, without starting that negotiation.
2. `receive()` invoked async worker control handlers without observing their rejected
   promise. Failures such as `PC manager is closed` could escape as unhandled rejections.
   They are now observed and terminate the owned connection safely when still current.
3. Cancellation could close a peer connection while its join/createOffer was pending.
   The bridge now stops capture immediately but waits for its join promise to settle
   before closing the SDK rooms. Abort is checked before each join/publication step.

The frontend startup deadline and backend startup lease are extended from 30 to 90
seconds for sleeping worker/backend startup. They remain finite; cancellation/end
still stop capture immediately. A timed-out attempt has a specific retry message;
there is no blind dispatch or cart mutation retry. Reload recovery returns to manual
mode, with retained cart and no microphone auto-start.

Visual testing also caught and fixed a reference to the removed legacy pause button
which falsely reported a pause failure after the actual pause succeeded.

These fixes address reproduced application races. They do not prove that every
reported SDK warning had one root cause. No STT/TTS/LLM provider was replaced.

## Verification

- JavaScript suite: **66 passed**, including three shutdown/cancellation regressions.
- Website Python suite: **49 passed**.
- Backend cold-start/lifecycle tests: **18 passed**. The added case permits a worker
  at 45 seconds and expires the same unready generation at 90 seconds.
- Current browser acceptance runs cover the widget at 390/1440px, Urdu/Roman Urdu
  shopping, refresh/BFCache/cleanup recovery and twelve manual ordering/checkout cases.
  **24 distinct cases passed** across the scoped runs: 4 widget, 3 Urdu shopping,
  5 lifecycle/recovery and 12 manual ordering/checkout. Intermediate runs caught
  old recovery-state expectations and a floating-cart overlap; both were corrected.
  Final widget/Urdu run: **7 passed**.
- Browser build, JS syntax and changed backend lint checks passed.

The browser fixture runs real SDK tools/application authority with fake RTC/providers.
Hosted diagnostics use actual RTC startup and a synthetic microphone; they do not
establish physical microphone or human listening quality. Legacy browser specs for
the removed welcome/wake UI are not the acceptance criteria for the new widget.

## Files and activation

- Template, `voice-assistant.css`, `voice-widget.mjs`, `voice-ui.mjs` and `app.js`:
  one widget, state presentation, non-modal controls and no wake onboarding.
- `livekit-bridge.mjs`, `assistance-controller.mjs`, `transcripts.mjs`: safe startup/
  teardown, phase feedback and transcript scrolling without moving keyboard focus.
- `orchestration/src/foodease_session/lifecycle.py`: bounded cold-start lease.
- Matching public JS/CSS copies and the compiled stylesheet are synchronized;
  the template entry and stylesheet query version are `zara-27`.
- `website/tools/inspect-hosted-voice.mjs`: bounded hosted diagnostic, recording only
  failed resource paths, state transitions and connection errors, never tokens/audio.

Evidence is in `deployment/evidence/voice-widget-2026-11-21/`. The worker itself needs
no redeployment for these browser/backend changes. The backend must run the updated
lifecycle code to use its longer startup lease.
