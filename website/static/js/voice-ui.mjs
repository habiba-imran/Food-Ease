// Presentation is derived from the existing lifecycle owner; this owns no session.
export function voicePresentation({ phase = 'manual', stage = '', agentState = '', microphoneActive = false, cleanupPending = false } = {}) {
  const connecting = ['connecting', 'requesting_permission', 'reconnecting'].includes(phase);
  const active = ['voice_active', 'typed_active', 'choosing_mode', 'paused'].includes(phase);
  const error = phase === 'error' || cleanupPending;
  let label = 'Start Voice Assistant';
  if (error) label = 'Retry Voice Assistant';
  else if (connecting) label = phase === 'reconnecting' ? 'Reconnecting…' : 'Connecting…';
  else if (phase === 'paused') label = 'Assistant paused';
  else if (phase === 'typed_active') label = 'Typed assistance';
  else if (active) label = agentState === 'assistant_speaking' ? 'Assistant Speaking'
    : agentState === 'thinking' ? 'Thinking…' : agentState === 'user_speaking' ? 'Listening to you…' : 'Listening…';
  if (connecting && stage === 'requesting_permission') label = 'Connecting microphone…';
  else if (connecting && stage === 'preparing_session') label = 'Preparing Zara…';
  else if (connecting && stage === 'starting_agent') label = 'Starting Zara…';
  const activity = error ? 'error' : connecting ? stage || 'connecting'
    : phase === 'paused' ? 'paused' : agentState === 'assistant_speaking' && active ? 'speaking'
    : agentState === 'thinking' && active ? 'thinking' : agentState === 'user_speaking' && active ? 'user_speaking' : active ? 'listening' : 'idle';
  return { label, canStart: !active && !connecting, canManage: active || connecting,
    activity,
    microphone: microphoneActive ? 'Microphone on' : 'Microphone off',
    state: error ? 'error' : connecting ? 'connecting' : active ? 'active' : 'inactive' };
}

export function voiceErrorMessage(error) {
  const messages = {
    NotAllowedError: 'Microphone permission is blocked. Allow it in your browser settings, or choose typing or manual ordering.',
    NotFoundError: 'No microphone was found. Connect one, or choose typing or manual ordering.',
    NotReadableError: 'Your microphone may be in use by another app. Close that app and retry, or choose typing.',
    AbortError: 'Voice startup was interrupted. You can retry when ready or continue manually.',
    TypeError: 'We could not reach the voice service. Retry Zara, or use typing while it recovers.',
    UnexpectedConnectionState: 'Zara’s connection closed during setup. Your microphone is off. Retry Zara.',
  };
  return messages[error?.name] || error?.message || 'Voice assistance could not start. You can retry or order manually.';
}
