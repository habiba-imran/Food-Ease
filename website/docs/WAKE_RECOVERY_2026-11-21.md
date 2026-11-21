# Hey Zara after a conversation ends

The user confirmed the ignored wake calls happened after ending the conversation,
with Wake microphone on displayed. This is the browser recognition path; the
worker is disconnected until wake succeeds. A bounded Cloud log inspection
showed no worker warning/error entries. Browser-native error/transcript history
for the user's earlier attempt was not retained, so its exact trigger is unknown.

## Reproduced gaps and fix

- Reproduced a stale indicator: a native recognition error stopped wake listening
  while the widget kept displaying Wake microphone on. Every wake state change
  now refreshes the full microphone presentation; reconnecting/error states no
  longer retain the old active indication.
- Persistent wake retries native network failures at most three times with
  0.7/1.4/2.8 second backoff. It waits for native end, releases the old tab lease,
  reacquires it, and cancels safely on manual startup, disabling, or page hiding.
  Missing native end stays blocked; permission/service errors never auto-retry.
- Accept Urdu address/name forms including ہائے زارا, ہیلو زارہ, ہے زرا and
  punctuation such as Hey, Zara, while retaining word/start boundaries. Bare
  ذرا/زرا and mid-sentence mentions remain rejected. Diacritics are normalized.
  Check up to three final browser alternatives, never interim speech.
- Existing one-shot wake latching and command handoff remain. No ambient
  transcript logging, worker recording, providers, voice interruption or endpoint
  settings changed. Static/public assets match; cache keys are zara-33,
  persistent-wake wake-3 and wake-word wake-4.

## Verification

- Before implementation, four new JavaScript cases failed and the browser
  indicator regression displayed Wake microphone on after permission failure.
- Final JavaScript suite: **84 passed**. Browser build and syntax checks passed.
- **7 distinct browser checks passed** across targeted runs: corner widget on
  desktop/mobile, wake re-arm/reload, category menu preservation on desktop/mobile,
  truthful error indicator, and network recovery with an Urdu command applied
  exactly once. The intermediate network test failed only during cleanup because
  the widget correctly collapsed after wake; cleanup now opens it first, and
  both new browser cases passed on rerun.
- Additional cases cover pending lease cancellation, missing native end, late
  failing-recognizer callbacks, bounded retries and blocked permissions. An added
  regression reproduced an aborted callback cancelling a deliberate recovery
  close; expected aborted events while stopping are now ignored, and final
  unit/browser/hosted fixtures include that callback.
- These tests synthesize recognition, audio and RTC/model responses; they prove
  lifecycle/command mechanics, not native Urdu recognition accuracy on a real mic.
- Website Python: **49 passed**, with the existing Starlette dependency warning.
- Initial hosted `zara-32` check completed the real RTC/worker/TTS end→wake→new
  session flow exactly once with zero errors, using synthetic native wake events
  and a silent microphone. `hosted-before-abort-guard.json` retains it. The
  strengthened final hosted check includes the deliberate aborted callback and
  follows publication of `zara-33`.
- The original native recognition service's behavior and the user's physical
  microphone accuracy cannot be reconstructed from worker logs.

## Sources checked

- [SpeechRecognition alternatives](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition/maxAlternatives)
- [Recognition error codes](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognitionErrorEvent/error)
- [Recognition end event](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition/end_event)
