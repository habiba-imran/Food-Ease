# Manual actions and uninterrupted relevant speech — 2026-11-22

The existing manual-context callback revoked the complete speech turn on every
new page revision. The user approved cooperative speech: unrelated clicks leave
Zara speaking; navigation hands over after the current sentence; changed totals
and reviews stop immediately; stop/pause/end remain immediate.

## Implementation

- New ManualCoexistence tracks output dependencies separately from effect authority.
  A manual context update always revokes the old turn's tool permissions. An
  output-only lease never rebinds its revision or authorizes a later mutation.
- Authored tool replies carry menu/item/cart/review/view scopes from code and
  verified results. Ordinary model replies emit a small private enum marker based
  on the reply's meaning; the output guard strips it before TTS/captions. Actual
  cart/review receipts override a misleading general hint. Missing hints are
  conservative. Marker parsing is structural, not a vocabulary-based intent matcher.
- Authored replies enter a custom, provider-free LLM-node branch of the public
  AgentSession segmented output pipeline. FlushSentinel ends each sentence.
  Model-generated sentences also emit boundaries. A real AudioOutput
  playback_finished event controls navigation interruption; no guessed timer or
  unaligned transcription fragment substitutes for sentence playout.
- After a relevant manual change, a bounded, cancelable follow-up reads current
  authority context without replaying the manual write. It acknowledges the
  latest category/item/view or reads the fresh cart. Failed reads give a generic
  non-outcome invitation. Rapid context changes supersede older notices; new
  user input/stop/pause/end prevent a late follow-up. Output waits while the user
  is speaking. Submitted action tasks stay owned and shielded.
- Changed cart hashes invalidate checkout/clear review receipts immediately.
  A completed review with unchanged facts can still prove delivery after a no-op
  revision, without restoring the old turn's action permissions.
- Manual category navigation now records the actual category in the accepted
  filter operation, so the worker can follow it. The browser still shows all
  categories as requested. Browser assets use zara-34, static/public files match.

## Verification

- Five initial manual-coexistence regressions failed before implementation.
- **12 focused manual/native tests passed**: unrelated menu/greeting/small talk,
  private split markers, old effect rejection, sentence handoff, immediate stale
  total cancellation, rapid clicks, stop/new-input cancellation, old consent
  refusal, unchanged review delivery, and cart-receipt scope override.
- The real SDK test uses synthetic PCM and an explicitly driven AudioOutput.
  It proves that sentence 1 reached the sink, sentence 2 did not, and a fresh
  acknowledgment reached it. Authored speech cannot call a model in this test.
  This is not a human listening or room-acoustics measurement.
- Full worker + website: **632 passed / 1 inherited failure** in unchanged
  integration/scenarios.py, test_no_mock_imports_outside_adapters. All existing
  dialogue/safety tests were included. Initial full run (retained) caught an old
  test requiring complete silence after manual edits; it now specifically forbids
  the stale quantity while permitting a verified current-cart acknowledgment.
- **9 distinct browser checks passed** across targeted runs. A mobile ordinary
  dialogue fixture advanced on optimistic DOM state before SDK reply completion;
  the fixture now waits for the matching completed caption. Mid-speech behavior
  is tested separately through native playout and the hosted audit.
- Scoped Ruff/Pyright passed. **84 JavaScript checks passed**, and frontend build
  and syntax checks passed. Hosted production verification follows below.
- Cloud simulator/debugger was not used: this worker requires the authenticated
  website startup binding and app RPC seat. No recording/authentication setting
  was changed to bypass that gate. Native interaction simulations and the bound
  hosted website exercise the actual permitted path instead.

## Production

Pending source push, code-only Cloud rollout and real-provider hosted interaction audit.
The hosted audit uses a synthetic silent microphone plus recognized text, and
manual DOM clicks during output. It bypasses microphone/STT and does not measure
caller-heard latency or physical acoustic interruption accuracy.

## Sources consulted

- [LiveKit segmented LLM output and FlushSentinel](https://docs.livekit.io/agents/logic/nodes/)
- [AudioOutput public playout events](https://docs.livekit.io/reference/python/livekit/agents/voice/io/)
- Installed LiveKit Agents 1.8.4 generation/forwarding and SpeechHandle behavior.
