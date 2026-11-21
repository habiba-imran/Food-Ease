# Urdu speech-onset interruption and worker redeploy

21 November 2026. Requested after the latency improvement in commit `68849ff`.

## Behavior

Urdu sessions now use LiveKit's supported `vad` interruption mode, with interruption
enabled, zero additional minimum-duration delay and no word-count requirement.
Whisper still transcribes the completed utterance; playback interruption does not
wait for that transcription or an adaptive backchannel classification. The existing
Silero speech detector, Urdu STT/TTS/LLM providers, endpointing, microphone ownership
and cart authority remain in place. This Urdu profile takes precedence over older
Cloud interruption duration/word settings. English sessions retain their existing policy.

The runtime also interrupts the greeting and queued speech on user speech onset
when no shopping turn exists yet. A submitted cart operation remains owned and
finishes/reconciles once; its interrupted turn cannot announce a late success.
Interrupted review delivery cannot authorize checkout or clear-cart. Urdu playback
does not automatically resume an older reply after an interruption classified as false.

This favors immediate interruption over backchannel suppression, as requested.
Audible stopping still depends on speech detection, microphone echo cancellation,
network transit and the browser audio buffer. No zero-millisecond or measured
caller-heard interruption claim is made.

## Deployment

- Existing target: `CA_gibAwTdK3sjn`, dispatch `foodease`, `ap-south`.
- Before redeploy: version `BwwtGc8eeGwp`, Cloud status `Sleeping`.
- Rollback target retained: `BwwtGc8eeGwp`.
- Command: `python deployment/cloud.py deploy --code-only`, with `LK_SOURCE=skills`
  set for this execution. The option preserves Cloud secrets/provider settings and
  uploads only staged image inputs; no local `.env` is placed in the build context.
- Staged context: 92 files, 1,007,356 bytes.
- Final deployment: **`XJw3A9BRfgiK`, Running**, Mumbai (`ap-south`), deployed
  at **14:05:44 PKT** on 21 November 2026. Cloud confirmed the new production version.
- Startup logs confirm HTTP health listener on port 8081, two initialized worker
  processes, Silero VAD prewarming and registration as `foodease` at 14:06:24 PKT.
  No startup error appeared in the bounded startup log check.

`deployment/cloud.py` now offers the reusable code-only deployment option, using the
same image staging routine as ordinary deploys. It avoids overwriting a working Cloud
provider configuration with different local environment settings.

## Validation

- New interruption regressions: 4 cases, including greeting and in-flight mutation.
- Code-only deployment guard: 1 case; checks no secrets flags/files and temporary cleanup.
- Focused deployment/interruption: **5 passed**.
- Urdu/latency/recovery focused run: **48 passed**.
- Full worker: **535 passed, one inherited mock-import failure** in unchanged
  `integration/scenarios.py`. The deployment helper test was added after that full
  run and verified separately.
- Changed production/test lint and type checks: passed, zero type errors/warnings.

These are deterministic native runtime/configuration/action tests, not a physical
microphone barge-in measurement. A generic Cloud simulation room does not provide
FoodEase's required bound browser/app seats and session metadata; the production
binding guard was not weakened to run one. No paid speech/model conversation or
human listening result is claimed. Deployment health is recorded separately below.

## Deployment evidence

Redacted observations are retained under `deployment/evidence/interruption-2026-11-21/`.
No credentials or caller recordings are included.

Reconnect the website's existing voice assistant to start a session on the new version.
The prior latency changes from `68849ff` are included in this deployed image.
