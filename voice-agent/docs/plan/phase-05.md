## Phase 5 — Real-time voice pipeline on LiveKit (Size L)

**Goal:** the verified brain, now with real speech, turn-taking, barge-in and a proactive greeting.

**Tasks**

- **5.0 [AGENT] Minimal talk client** (`harness/` v0): a bare page that joins the room, publishes the mic, shows agent state and captions, and has a mute button and typed-input box. (Optional quick checks while building: LiveKit's console mode or hosted Agents Playground, if available for your version. Verify.) Phase 7 expands it into the full inspector.
- **5.1 [AGENT] Session assembly.** `AgentSession` with Deepgram (Flux via `STTv2`, `turn_detection="stt"`), Cartesia (chosen model + voice ID), Gemini (explicit `thinking_level`). Two switchable configs via env: **A:** Flux with STT-based turn detection; **B:** Nova-3 + Silero VAD + LiveKit turn-detector model. Both must run; Phase 9 picks the winner with data. Enable aligned word timestamps in the Cartesia plugin if supported, so captions match what was actually spoken.
- **5.2 [AGENT] Worker lifecycle.** Prewarm models; connect providers early; keep resources warm for the consented session. The agent joins only after an explicit user action (harness button now, the website's opt-in later). No listening before consent.
- **5.3 [AGENT] Proactive greeting.** After the room is ready, audio is subscribed and the first context snapshot arrives (**with a short timeout, ~2 s, after which the agent greets generically and requests context**), the agent speaks first. Greeting is short, pre-authored (not LLM-generated), from a pool of 2–3 variants so repeat testers don't hear the identical line, interruptible from its first audible moment, with a shorter "resume" variant when voice returns in the same session. **P1:** synthesize the greeting once at prewarm and play from cache (verify the installed version supports say-with-audio); invalidate the cache when voice/settings change.
- **5.4 [AGENT] Idle prompts (VA-02).** First contextual tip after the idle interval (initial ~12 s), a different second tip later (~30 s), then quiet. Context-aware (menu / item / cart). Cancelled by any user speech, typed input, GUI event, mute, stop, disconnect. Never speaks over the user, never repeats endlessly, never acts. Unit-tested with a fake clock.
- **5.5 [AGENT] Turn-taking config** via `TurnHandlingOptions` (livekit-agents 1.5+; old kwargs are deprecated). Starting values to tune in Phase 9: interruption mode adaptive, `min_duration` ≈ 0.5 s, `min_words` 0–1, false-interruption timeout ≈ 2 s with resume enabled, endpointing min ≈ 0.4–0.5 s and max ≈ 3 s. Starting points, not answers.
- **5.6 [AGENT] Interruption reconciliation.** On a valid barge-in: audio stops, queued speech is discarded, in-flight actions stay pending and are reconciled by `action_id`, `transcript.assistant` is marked `interrupted` and contains only what was actually spoken, chat history is truncated to what the user heard. A result arriving later gets a short relevant status or silence, never duplicate or overlapping replies.
- **5.7 [AGENT] Speculative generation safety. Critical.** Flux's eager end-of-turn and LiveKit's preemptive generation start the LLM before the turn is committed. Determine, from the installed version's docs and behavior, whether a tool can *execute* in a generation later discarded. If yes (or unprovable), disable preemptive generation or gate **all mutating tools** behind a committed-turn check. Record an ADR.
- **5.8 [AGENT] Noise and echo.** Optional LiveKit noise-cancellation toggle (check plan availability) tested under the T18 conditions; document speaker-echo behavior with and without earphones.
- **5.9 [AGENT] Speech controls.** Pause/resume, repeat, slower/faster (via `update_options` per the Phase 1 decision), mute, `agent.control` emission.
- **5.10 [HUMAN]** 10 minutes of free conversation with laptop mic + earphones, then speakers at moderate volume. Note self-interruption from echo, clipped syllables, odd pauses, overlaps.

**Strict guidelines**

- The greeting and every long reply are interruptible; only one assistant utterance is audible at a time.
- "mm-hmm", coughs and background voices are not definite requests.
- Mutating tools run only for committed turns (5.7).
- A fatal provider error sets state `error`, never leaves `ready/listening`.

**Verification**

| ID | Check | Pass condition |
|---|---|---|
| V5.1 | T01: silence → agent greets by itself | Pass |
| V5.2 | T02: silence after greeting | One tip, maybe a second, then quiet; no loop |
| V5.3 | T03: interrupt greeting with "Show burgers" | Audio stops; a valid filter/navigation request emitted |
| V5.4 | T04: hesitation "I want… maybe a spicy… burger", ≥ 10 trials | Mostly not cut off; failures logged with counts |
| V5.5 | T10: Stop / Repeat / Go back / Slower by voice | Handled by fast-path; LLM not invoked (verify in logs) |
| V5.6 | T20: interrupt during a delayed mutation | Audio stops; reconciled by `action_id`; one mutation |
| V5.7 | "Add two… no wait, show burgers" with eager EOT enabled | **0 cart mutations from a discarded generation** |
| V5.8 | Overlap check from the event log | Never two assistant-speaking intervals overlapping |
| V5.9 | False-interruption fixtures (cough, "mm-hmm") | Speech resumes/continues; no lost context |
| V5.10 | Snapshot-timeout test: delay the first snapshot by 5 s | Agent greets within the timeout and recovers when context arrives |
| V5.11 | 20-minute soak with scripted turns | No crash, no memory growth trend, no runaway speech |

**Gate:** V5.1–V5.11 (failures in V5.4/V5.9 documented with counts if not perfect).

---

