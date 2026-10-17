# Final orchestration Phase 6: opening and mode continuity

Habiba authorized Phase 6 only. No conversation-quality expansion, animations,
new shopping operations, provider changes or frozen contract edits are included.

The existing assistance surface now asks the ordering-mode question as text on
load. Manual shopping works immediately. **Enable microphone and spoken welcome**
is explicit consent to capture the answer and play the short question. Direct
voice bypasses that question; direct typing never requests capture. A returning
visitor gets the same activation fallback, even with browser permission already
granted. An optional same-tab, shopping-session-bound marker changes resume copy;
it never starts a connection or reopens capture. Explicit manual selection cannot
be overridden by that marker. Storage being unavailable does not block shopping.

## Admission and wire behavior

The controller records `awaiting_spoken_choice_consent`, `connecting`,
`choosing_mode`, `voice_active`, `typed_active`, `paused`, `reconnecting`, `manual`,
`ended` and `error`. The page exposes that state on the root's
`data-assistance-state`; worker speaking/listening labels cannot authorize startup.

The unchanged v2 Control model already supports these distinctions:

| Browser intent | Existing control | Worker admission |
| --- | --- | --- |
| Spoken choice | `start`, mode `voice` | Internal `choosing`; audio enabled, shopping disabled |
| Direct selection | `switch_mode`, mode `voice` or `typed` | Selected mode, one short invitation |
| Return after activation | `resume`, selected mode | Selected mode, brief welcome back |
| Manual/end | `switch_mode manual` / `end`, or local End | Local revocation and service cleanup |

The opening is emitted only after the authenticated worker-ready/playback gate
and an explicit browser control. It is deduplicated per generation. Choosing
voice continues in the same generation. Phrases such as “manual please”, “I'll
order myself”, “use voice” and “talk me through it” are deterministic controls.
Ambiguity, negatives, mixed choices and food requests during onboarding do not
reach the LLM or broker. One short clarification is available, also after 15
seconds from opening once neither side is speaking; further silence remains quiet.
There is no order from silence.

Switching to manual interrupts speech, disables input/output and tips, stops raw
media tracks, attempts unpublication, detaches/pauses audio and disconnects both
seats. Local shutdown precedes server cleanup. A late permission result is stopped
and cannot revive an older start. Pending committed business tasks retain their
original identity and outcome; speech cancellation does not cancel those tasks.
The application still renders their verified result after assistance ends.
Browser RPC admission is checked again when queued work begins, so unsubmitted
requests cannot enter the authority after their bound assistance owner closes.

Voice to typing can keep the generation, stop/unpublish capture, and detach audio.
Typing to voice requires a fresh explicit Start voice gesture. Other explicit
mode starts use a fully ended generation before creating another; cleanup pending
blocks a replacement. The shopping session, route and cart are independent of
assistance generations. Resumption never replays an order or checkout consent.
Existing mode controls move into the current item/checkout dialog, and typed input
is relocated immediately on mode changes. Switching modes never requires closing
the shopping dialog or changing its route.

Typing is silent by default. **Read typed replies aloud** explicitly enables only
output, using existing mute/unmute controls. Disabling it keeps text available.
It cannot enable microphone input. Pause disables local capture delivery and mutes
attached audio, including newly subscribed audio, while preserving resume controls.

## Verification and limits

Run from the repository root:

```powershell
.\voice-agent\.venv\Scripts\python.exe orchestration/tools/phase6_verify.py --output orchestration/evidence/final/phase-06/run-3
```

The runner strips provider keys, disables dotenv and preserves historical test
artifacts and frozen v1 contracts. See the [report](../evidence/final/phase-06/report.md).
The final JavaScript/browser rerun after dialog/admission review is recorded in
`evidence/final/phase-06/browser-final/`: 29 JavaScript checks and 22 browser tests
passed. The full worker run has 60 focused passing tests.
The browser tests use production browser/worker code and the real website
authority, with local fake RTC, lifecycle and LLM. Full Chromium's native
`getUserMedia` uses a synthetic device; assertions inspect actual
`MediaStreamTrack.readyState`. A real HTML audio element plays a Web Audio
generated stream, and assertions require paused playback, cleared `srcObject`
and stopped capture after manual selection. These checks exceed status-label
assertions, but do not establish a physical microphone, Cloud WebRTC, provider
STT/TTS, audible quality or human listening results. Those remain activation work.

The installed livekit-client 2.15.4 source/declarations were checked for
`publishTrack(MediaStreamTrack)`, `unpublishTrack(track, stopOnUnpublish)`,
`startAudio()` and `canPlaybackAudio`. Current official references:
[LocalParticipant](https://docs.livekit.io/reference/client-sdk-js/classes/LocalParticipant.html),
[getUserMedia](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia)
and [autoplay](https://developer.mozilla.org/en-US/docs/Web/Media/Guides/Autoplay).
The website remains process-local as documented in earlier phases; no persistence
or broad reconnect/reload guarantees have been added. Phase 7 has not started.
