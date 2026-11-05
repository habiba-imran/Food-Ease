// Presentation is derived from the existing lifecycle owner; this owns no session.
export function voicePresentation({ phase = 'manual', agentState = '', microphoneActive = false, cleanupPending = false } = {}) {
  const connecting = ['connecting', 'requesting_permission', 'reconnecting'].includes(phase);
  const active = ['voice_active', 'typed_active', 'choosing_mode', 'paused'].includes(phase);
  const error = phase === 'error' || cleanupPending;
  let label = 'Start Voice Assistant';
  if (error) label = 'Retry Voice Assistant';
  else if (connecting) label = phase === 'reconnecting' ? 'Reconnecting…' : 'Connecting…';
  else if (phase === 'paused') label = 'Assistant paused';
  else if (phase === 'typed_active') label = 'Typed assistance';
  else if (active) label = agentState === 'assistant_speaking' ? 'Assistant Speaking'
    : agentState === 'thinking' ? 'Thinking…' : 'Listening…';
  return { label, canStart: !active && !connecting, canManage: active || connecting,
    microphone: microphoneActive ? 'Microphone on' : 'Microphone off',
    state: error ? 'error' : connecting ? 'connecting' : active ? 'active' : 'inactive' };
}

export function voiceErrorMessage(error) {
  const messages = {
    NotAllowedError: 'Microphone permission is blocked. Allow it in your browser settings, or choose typing or manual ordering.',
    NotFoundError: 'No microphone was found. Connect one, or choose typing or manual ordering.',
    NotReadableError: 'Your microphone may be in use by another app. Close that app and retry, or choose typing.',
    AbortError: 'Voice startup was interrupted. You can retry when ready or continue manually.',
    TypeError: 'We could not reach the voice service. Check your connection, or continue with manual ordering.',
  };
  return messages[error?.name] || error?.message || 'Voice assistance could not start. You can retry or order manually.';
}
