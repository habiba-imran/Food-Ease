import { test } from 'node:test';
import assert from 'node:assert/strict';
import { voicePresentation, voiceErrorMessage } from '../static/js/voice-ui.mjs';

test('voice labels derive from lifecycle, speech and actual microphone state', () => {
  assert.equal(voicePresentation({ phase: 'manual' }).label, 'Start Voice Assistant');
  assert.equal(voicePresentation({ phase: 'connecting' }).label, 'Connecting…');
  assert.equal(voicePresentation({ phase: 'voice_active', microphoneActive: true }).label, 'Listening…');
  assert.equal(voicePresentation({ phase: 'voice_active', agentState: 'assistant_speaking' }).label, 'Assistant Speaking');
  assert.equal(voicePresentation({ phase: 'typed_active' }).label, 'Typed assistance');
  assert.equal(voicePresentation({ phase: 'paused' }).label, 'Assistant paused');
  assert.equal(voicePresentation({ phase: 'error' }).label, 'Retry Voice Assistant');
  assert.equal(voicePresentation({ phase: 'manual', cleanupPending: true }).label, 'Retry Voice Assistant');
  assert.equal(voicePresentation({ phase: 'manual', microphoneActive: false }).microphone, 'Microphone off');
  assert.equal(voicePresentation({ phase: 'connecting', microphoneActive: true }).microphone, 'Microphone on');
  assert.equal(voicePresentation({ phase: 'reconnecting' }).canStart, false);
  assert.equal(voicePresentation({ phase: 'choosing_mode' }).canManage, true);
});

test('voice permission and network failures have useful, nontechnical messages', () => {
  assert.match(voiceErrorMessage({ name: 'NotAllowedError' }), /permission.*blocked/i);
  assert.match(voiceErrorMessage({ name: 'NotFoundError' }), /microphone.*found/i);
  assert.match(voiceErrorMessage({ name: 'NotReadableError' }), /microphone.*another app/i);
  assert.match(voiceErrorMessage({ name: 'TypeError', message: 'Failed to fetch' }), /reach.*voice service/i);
  assert.match(voiceErrorMessage(new Error('Audio playback is blocked.')), /playback.*blocked/i);
});
