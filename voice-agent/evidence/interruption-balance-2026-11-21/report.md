# Balanced Urdu interruption

The user reports repeated interrupted captions and inaudible replies in a quiet
room. This change supersedes ADR-0034's zero-duration Urdu interruption policy.

## Findings and change

The Urdu profile had a zero-duration SDK interruption gate. Independently, the
runtime called `session.interrupt(force=True)` on every raw `user_state_changed`
speech onset, bypassing the SDK's duration and AEC warmup protections. The VAD's
default minimum speech segment was only 50 ms. These application settings explain
why even very brief detected activity could cut playback; they do not prove that
every reported transcript fragment came from noise or echo.

Urdu now uses **0.35 seconds** as the common minimum for both a Silero speech
segment and SDK VAD interruption. The detector gate is essential: in the installed
Silero implementation, published `speech_duration` continues through its trailing
silence window, so merely increasing the SDK duration can still let a tiny sound
grow past it. Prewarm and fallback loading share the same detector factory. Prefix
padding, activation threshold, end-of-speech silence and endpointing are unchanged.

Raw Urdu user-state notifications still track activity but do not force-interrupt
audio or revoke the business turn. SDK-confirmed interruption revokes its owning
turn. All speech handles, including separate `say()` replies, are bound to that
owner; authorization rejects an interrupted handle synchronously, before its done
callback. An old callback cannot revoke a replacement turn. Submitted mutations
remain owned and reconcile once; interrupted reviews cannot authorize checkout or
cart clearing. Real completed input still supersedes the old turn normally.

Urdu remains interruptible without waiting for non-streaming Whisper words:
`mode=vad`, `min_words=0`, interruptions enabled. English's existing profile is
unchanged. Browser echo cancellation and the SDK's default AEC warmup are retained.
Automatic resurrection of old Urdu replies remains disabled to preserve turn and
confirmation ownership. No provider, prompt or shopping workflow was replaced.

The 350 ms value is a configured speech threshold, **not a measured audible-stop
latency**. No physical microphone, speaker path or human listening result is claimed.

## Verification

- Before the fix, the new policy/onset regressions reproduced three failures.
- Focused Urdu/interruption/runtime/recovery/latency tests: **91 passed**.
- Full worker: **552 passed, 1 inherited failure** in
  `test_no_mock_imports_outside_adapters`, which flags unchanged
  `integration/scenarios.py`. This same failure was documented before this change;
  neither the test nor the offending file was edited.
- Changed-file Ruff: passed. Scoped Pyright: 0 errors/warnings.
- Fourteen detector-to-SDK scenarios exercise the installed Silero stream's actual
  smoothing/segmentation and installed `AgentActivity.on_vad_inference_done`, with
  scripted acoustic probabilities and in-memory PCM (no recordings or WAV files).
  Silence, 64/160/256 ms activity and separated short bursts do not interrupt;
  sustained 384/640 ms activity does, for greeting and ordinary reply paths.
  These are deterministic pipeline simulations, not acoustic recognition scores.
- Additional checks cover prewarm/fallback agreement, older Cloud settings,
  in-flight cart ownership, interruption before done callbacks, late old callbacks,
  and no forced greeting interruption on a raw onset.

Cloud's ordinary conversation simulator is not an end-to-end substitute here:
this worker requires a website-bound app/user session and readiness gate. The local
pipeline simulations cover the changed speech boundary without dispatching an
unbound simulated room or claiming live Urdu speech accuracy.

## Deployment

Target: existing FoodEase agent `CA_gibAwTdK3sjn`, dispatch `foodease`, `ap-south`.
Previous version: `z2LN4W7zmMhg`. Code-only deployment preserves provider secrets
and settings and stages only image inputs (92 files, 1,008,833 bytes).
Cloud deployed version **`rX7bpf3xKjrF`** at 2026-11-21 12:16:07 UTC.
After inactivity it was sleeping; a fresh website session woke it successfully.
The post-start status reports **Running**, and startup logs explicitly confirm
`prewarm: silero VAD loaded language=ur`, health listening and worker registration.

The production browser check reached `voice_active` from a sleeping worker in
45.0 seconds, with zero captured failed resources, page errors or closed-connection
errors. This is a cold connection-start check with a synthetic microphone, not
spoken-response latency or a physical false-interruption measurement. The probe
ended its conversation. No Cloud secrets or recording settings were changed.

## Documentation consulted

- [LiveKit interruption options](https://docs.livekit.io/reference/agents/turn-handling-options/)
- [Silero VAD parameters](https://docs.livekit.io/reference/python/livekit/plugins/silero/index.html)
- Installed LiveKit Agents/Silero **1.8.4** source for duration accounting and
  `aec_warmup_duration`; the implementation and tests target that pinned version.
