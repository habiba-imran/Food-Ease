# Zara voice-only widget and persistent Hey Zara

21 November 2026.

All 28 menu items have a short public description, shown both on their cards and
in the existing item detail window. The ingredient list is removed from that window.
Catalog/tool facts remain available to the worker. Item/cart windows contain no
separate start-assistant or typing controls. The same corner widget remains usable
over native shopping dialogs and holds the single conversation transcript.

Typing buttons, input, submit form and their browser event handlers are removed.
Start Zara in the corner widget is the first microphone action. After a successful
voice activation, the Hey Zara preference is saved in local storage. During a voice
conversation, LiveKit owns capture. When it ends and server cleanup releases the
tab lease, native Urdu wake recognition resumes automatically. A wake hands off
only after native recognition and its lease finish, starts one conversation and
forwards an addressed request once. Ordinary idle recognition endings restart
with a bounded delay rather than disabling the preference after four cycles.

Reload restores the saved wake preference after recovering the previous session;
it never resumes the old conversation or dispatches a new worker without a wake.
Hidden/unloading pages stop capture; a visible page resumes wake listening after
cleanup. Pausing the active conversation keeps both microphones paused. The
widget offers Turn off Hey Zara, and that choice is saved until voice is started
again. Microphone errors no longer advertise the removed typing mode.

Wake listening uses browser speech recognition with `ur-PK`. Browser support,
permission and the browser's speech service remain necessary. Unsupported or
blocked recognition reports an error and retains the Start Zara control. This
does not promise listening while the page is closed or hidden, nor prove real
Urdu wake accuracy. The widget explains browser speech-service audio processing.

## Verification

- JavaScript: 70 passed, including persistent preference, idle restart, delayed
  native release and cancellation during lease acquisition.
- Website Python: 49 passed; changed Python lint and browser build passed.
- Browser: 25 distinct cases passed across scoped runs: 6 widget, 3 Urdu action,
  4 lifecycle/reload and 12 manual ordering/checkout cases. Final widget/Urdu run:
  9 passed. Every item's detail window was inspected at runtime. Wake tests cover
  duplicate wake results, one forwarded Urdu request, shared cart, reload,
  hidden/visible transitions, opt-out, permission failure and no parallel capture.
- Browser RTC/providers and recognized speech are fixtures; these results do not
  establish physical microphone, STT or audible playback quality. After removing
  typing, the old typed-clear test's expected success was inappropriate for the
  fixture's absent TTS. The voice test now verifies that a transcript without
  audio delivery cannot authorize clearing the cart; the cart stays unchanged.
- Source/public JavaScript copies match. Entry assets use `zara-28`.
- After pushing `51e0406` to `origin/main`, a production Chromium check loaded
  `zara-28`, found all 28 short descriptions, zero ingredient/typing controls,
  one wake control and the non-modal widget. Actual LiveKit startup reached
  `voice_active` in 12.8 seconds and saved the wake preference as `on`. It recorded
  zero failed resources, page errors or matched closed-connection console errors.
  This synthetic-microphone check proves startup, not human speech/wake accuracy.

## Worker deployment

The user requested a redeploy even though worker source was unchanged. The existing
FoodEase worker `CA_gibAwTdK3sjn` was redeployed through `deployment/cloud.py deploy
--code-only` with `LK_SOURCE=skills`, preserving Cloud secrets/provider settings.
Image staging uploaded 92 files, 1,007,356 bytes, with no local environment files.
Cloud confirmed production version `z2LN4W7zmMhg`, Running in `ap-south`, deployed
at 2026-11-21 11:43:34 UTC. Previous version: `XJw3A9BRfgiK`.
Startup logs show health listening on port 8081, two initialized processes with
Silero VAD prewarmed, and registration as `foodease` at 11:44:04 UTC.

Evidence: `deployment/evidence/persistent-wake-2026-11-21/`.
