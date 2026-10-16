# Installed SDK and API audit — Phase 0

17 October 2026. Inventory and source inspection only; no live room or provider
session was started. Exact installed distributions and callable signatures are in
`run-1/voice-agent-inventory.log` and the independently repeated run-2 inventory.

## Versions

| Component | Observed value | Evidence |
|---|---|---|
| uv | 0.10.6 | Setup command output |
| Agent Python | CPython 3.12.12 | Agent inventory |
| Session-service Python | CPython 3.12.12 | Orchestration inventory |
| Website Python | CPython 3.11.14 | Website inventory; preserves website/.python-version |
| Node | v24.12.0 | node-version.log |
| livekit-agents | 1.8.4 | Agent installed distribution metadata |
| livekit RTC Python | 1.1.20 | Agent installed distribution metadata |
| livekit-api | 1.2.1 | Both Habiba package inventories |
| LiveKit Cartesia/Deepgram/Google/Silero/turn-detector plugins | 1.8.4 each | Agent inventory |
| cartesia | 4.2.0 | Agent inventory |
| deepgram-sdk | 7.12.0 | Agent inventory |
| google-genai | 2.27.0 | Agent inventory |
| livekit-client JavaScript | 2.15.4 referenced by CDN import | voice-agent/harness/app.js; not installed in website |
| Website LiveKit JS runtime | None | website/pyproject.toml and static/js/app.js |

Lockfile SHA-256 values for all three packages are in each run's summary.json.
Existing voice-agent/orchestration locks were not updated. Website received its
first lockfile; the supported Python ranges and application dependencies were
not changed.

## Python APIs checked against installed source

Primary evidence is the installed package source, not an assumption about the
latest website documentation. Callable signatures include source paths and line
numbers in the inventory log.

| Surface | Verified behavior/signature | Integration implication; no fix in Phase 0 |
|---|---|---|
| AgentSession.start | Accepts agent, room and room_options | Existing worker startup arguments are supported |
| AgentSession.say | Accepts text/async text, optional audio, allow_interruptions; returns SpeechHandle | Existing welcome pattern has a supported speech handle; actual playback still needs live evidence |
| AgentSession.interrupt | Takes force keyword; returns asyncio.Future | Wire and observe real interruption later; a local product-state change is insufficient |
| AgentSession.generate_reply | Supports user_input and input_modality, among other parameters | There is a worker-side typed-input entry point to evaluate during Phase 4/5 |
| Agent.on_user_turn_completed | Async callback with turn_ctx and new_message | Supported place for committed-turn policy/context integration |
| room_io.RoomOptions | text_input, participant_identity/kinds, input/output options, close_on_disconnect | Explicitly bind the user seat in a three-participant room in Phase 3/4 |
| Session events | agent_state_changed, user_state_changed, user_input_transcribed, conversation_item_added, speech_created, error exist in voice/events.py | Event names are available; worker event wiring and caption delivery remain unimplemented |
| RTC register_rpc_method | Synchronous method accepting handler; invocation includes caller identity | Browser/app forwarding must validate the bound caller/session later |
| RTC perform_rpc | Async; destination_identity/method/payload/response_timeout | Current adapter keyword names are supported; failure raises RpcError, not just TimeoutError |
| RTC publish_data | Async; payload, reliable, destination_identities, topic | Current call signature is supported; sender/recipient association remains future work |
| RTC set_attributes | Async and requires appropriate metadata permission | Existing LiveKitRoom.register_participant calls it without await; pyright flags this. Record as a pre-existing Phase 3 runtime issue |

Source paths inspected under the agent virtual environment:

- `livekit/agents/voice/agent_session.py`
- `livekit/agents/voice/agent.py`
- `livekit/agents/voice/room_io/types.py`
- `livekit/agents/voice/events.py`
- `livekit/rtc/participant.py`

The current SDK's event documentation corroborates the event families, but the
installed source is the version-specific authority: [LiveKit agent events](https://docs.livekit.io/reference/agents/events/).

## JavaScript reference checked at the exact harness tag

The website has no JS LiveKit installation to inventory. The harness references
2.15.4. Its exact-tag [LocalParticipant source](https://raw.githubusercontent.com/livekit/client-sdk-js/v2.15.4/src/room/participant/LocalParticipant.ts)
confirms `publishData` supports topic/reliable options and `setMicrophoneEnabled`
is supported. Disabling an already published microphone mutes its track; this
alone does not establish release of microphone capture. The local-participant
RPC registration method exists but is deprecated in favor of room registration.
Check the chosen browser dependency again when Phase 5 installs it. No JS
dependency, registration behavior or transport contract was changed here.

Fetching the separate Room/rpc source pages through the web tool failed. Their
uninspected details, including byte-limit behavior, remain a later verification
item; no unsupported numerical transport limit is asserted by this audit.

## What this audit does not prove

No real STT, LLM or TTS request, room connection, dispatch, audio playback,
microphone behavior, interruption latency or conversational quality was tested.
SDK availability and offline construction tests are not activation evidence.
