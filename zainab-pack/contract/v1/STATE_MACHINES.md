# Contract v1.0 — State machines

## A. Conversation lifecycle (LiveKit → VA-07 product states)

Product states (VA-07):  
`off/awaiting_consent` · `connecting` · `ready/listening` · `user_speaking` · `thinking` · `assistant_speaking` · `waiting_for_action_result` · `idle` · `muted/paused` · `reconnecting` · `error` · `ended`

| Product state | Typical LiveKit / session meaning (Habiba mapping) |
|---|---|
| `off/awaiting_consent` | No agent session yet; mic/consent not granted |
| `connecting` | Joining room / starting agent worker |
| `ready/listening` | Agent connected; listening for user speech or text |
| `user_speaking` | User turn in progress (VAD / STT interim) |
| `thinking` | End of user turn; LLM / policy running, no TTS yet |
| `assistant_speaking` | TTS playback active |
| `waiting_for_action_result` | `agent.action_request` submitted; awaiting `app.action_result` |
| `idle` | Listening quietly after help prompts; no active speech |
| `muted/paused` | User or app requested mute/pause |
| `reconnecting` | Transport reconnect; do not invent action outcomes |
| `error` | Fatal/recoverable error surfaced as `agent.error` |
| `ended` | Session closed |

Rules:

- Transitions are observable via `agent.status` (and LiveKit-native mirrors).
- A fatal `agent.error` must not leave the UI stuck on `ready/listening`.
- Speech cancel ≠ action cancel: leaving `assistant_speaking` does not imply the in-flight action finished or failed.

```
off/awaiting_consent → connecting → ready/listening
ready/listening → user_speaking → thinking → assistant_speaking → ready/listening|idle
thinking → waiting_for_action_result → thinking|assistant_speaking|ready/listening
* → muted/paused → ready/listening
* → reconnecting → ready/listening|error
* → error → ended|ready/listening
* → ended
```

## B. Action lifecycle

```
created → submitted → success
                     → failed
                     → rejected
                     → stale_context
                     → requires_confirmation
                     → timeout_unknown
```

| State | Meaning |
|---|---|
| `created` | Agent allocated a unique `action_id` and validated allowlist + args locally |
| `submitted` | Request sent to the app (RPC); waiting for correlated result |
| `success` | App verified outcome; agent may speak success **only** for this `action_id` |
| `failed` | App attempted and failed; speak failure reason |
| `rejected` | App refused (policy/validation); speak rejection |
| `stale_context` | `context_revision` no longer current; refresh, do not blind-retry mutation |
| `requires_confirmation` | Needs explicit user confirm bound to current summary/revision |
| `timeout_unknown` | No authoritative result; reconcile (`get_cart` / context), then ask — **never** auto-resubmit mutations |

Idempotency: duplicate `action_id` returns the **prior** outcome with no second mutation.
