# Latency audit — 7 November 2026

**Verdict:** The current Urdu assistant does not have a verified caller-heard
latency baseline in the project evidence. The pipeline contains several sources
of noticeable delay, and the older measurement scripts cannot establish its
current response or interruption performance. No runtime settings were changed
during this audit. No credentials, provider calls, recordings, restart or deployment
were used.

## What is actually measured

| Metric for the current Urdu assistant | Measured samples available | Result | Project target |
|---|---:|---|---|
| End of user speech to first audible reply | 0 | Unverified | p50 ≤ 1,200 ms; p95 ≤ 2,500 ms |
| Warm greeting to audible output | 0 | Unverified | p50 ≤ 800 ms; p95 ≤ 1,500 ms |
| Cold join to audible greeting | 0 | Unverified | p50 ≤ 2,000 ms; p95 ≤ 4,000 ms |
| User interruption to audible silence | 0 | Unverified | p95 ≤ 350 ms |
| Completion without restart | 0 current measured attempts | Unverified | ≥95% |

`evidence/phase-9/latency_report.md` explicitly has no sources and n=0 for all
headline metrics. There are no raw JSONL files under that phase's evidence tree.
The final orchestration acceptance evaluation likewise has zero audible samples,
zero ordinary attempts and zero genuine interruptions. The live-measurements CSV
contains its header only. These are missing measurements, not zero latency.

The latest Urdu/semantic-control reports explicitly leave live provider timing
unverified. Runtime/provider metrics may exist outside this checkout, including
LiveKit's account dashboard; those were not accessed. Private environment overrides
and the configuration of any currently running worker were not inspected. The
configuration findings below describe the current source defaults.

## Findings, in priority order

### P1 — Capture the right metrics before making performance claims

The integrated runtime registers no `metrics_collected` or
`conversation_item_added` handlers. Its own `MetricsLogger` is used by legacy
injection scripts, not the active assistant. Thus there is no application-owned,
per-turn breakdown for Urdu STT, model/tool steps, text buffering, synthesis and
playback in these artifacts. SDK internal measurements are distinct from local
export and browser-heard audio.

Use public `ChatMessage.metrics` and provider-stage metrics where available,
correlated by speech/message/turn IDs. The custom `on_user_turn_completed` hook
starts its own reply and raises `StopResponse`: in installed SDK 1.8.4 this returns
before the ordinary `EOUMetrics` event emission. The SDK-created user message does
carry turn metrics into the manually generated reply, so message metrics should
be preserved rather than relying only on that skipped event. Never substitute
missing fields with zero or sum metrics from different model steps.

Measure browser/audio onset separately: SDK room playback timing reports when
frames are forwarded to the track and does not establish actual client speaker
playback. Source: installed `chat_context.MetricsReport` and official
[LiveKit data hooks](https://docs.livekit.io/testing/observability/data/).

### P1 — Urdu recognition is batched after speech ends

`session.py:62` selects Groq Whisper. The installed Groq plugin explicitly uses
`use_realtime=False`. SDK `stt/stream_adapter.py` waits for VAD END_OF_SPEECH,
merges the captured utterance, then calls remote recognition. No text is available
to the model until that request completes.

The code calls `silero.VAD.load()` without options. Installed 1.8.4 defaults to
**550 ms of silence** before ending a speech segment. This is a configured waiting
period, not a measured user-facing percentile. A remote transcription request,
model work and synthesis follow it. The 450 ms endpointing minimum overlaps the
elapsed silence/recognition time; do **not** add 550+450 ms as a guaranteed 1-second
delay. The SDK subtracts already-elapsed time before any extra endpointing sleep.

Highest-impact candidate: evaluate a genuinely streaming Urdu recognizer with
actual Urdu/menu utterances, then tune VAD/end-of-turn waits against natural pauses.
Changing a language code on the English-only recognizer is not a substitute.
Recognition quality and false turn cuts must remain acceptance criteria.

### P1 — Semantic requests add sequential model/tool/network work

The actual SDK offline test confirms a normal `get_cart` request needs **two model
steps**: choose the tool, then formulate the reply from its result. The local
conversation-control test uses **one** model step and suppresses a continuation.
Those are execution counts, not live latency measurements.

The broker performs fresh-context → requested action → fresh-context. The offline
probe confirms **two context reads plus one requested action** for a successful
`get_cart`. The production adapter implements each as a LiveKit RPC, so this is
**three serial application RPC round trips** per successful tool action. A
clear-search plus filter sequence can require two broker operations.

Evaluate revision-safe reuse of correlated results/context and avoid unnecessary
model continuations where runtime speech already contains the verified answer.
Do not remove freshness checks or parallelize dependent cart writes blindly.
Keep semantic interpretation; reintroducing keyword rules would not satisfy the
user's requirements.

### P2 — First-token speed is not first-speech speed

`integrated/output.py:78` buffers model text until `. ! ? ۔ ؟`, end-of-stream or
the 1,200-character bound. It forwards tool chunks while withholding text content.
The offline Urdu probe releases the first text only after chunk 3, which contains
the sentence punctuation. No time was simulated or claimed by that probe.

There may be further segmentation before the TTS provider receives text. Measure
first token, first safe text release, first TTS sentence and first audio byte
separately. A fast model TTFT alone will hide sentence-generation/buffering delay.
Prefer a short substantive first sentence and evaluate safe early release; do not
stream unverified outcome fragments or add canned filler to disguise silence.

### P2 — Model request size and quotas can dominate repeat turns

The offline empty-cart/home-page probe measures 6,653 policy characters, 5,278
current-context characters and 5,979 tool-schema characters across 14 tools.
These are exact text/JSON character counts, **not tokens**, and exclude chat history,
role framing and preceding tool results. The model context includes up to 25 menu
rows. Onboarding context is already reduced to 88 characters and its control tool.

The prior provider follow-up documents Groq 429 responses. That history is not a
current quota measurement, but lower network latency cannot repair exhausted
capacity. The installed GPT-OSS plugin already defaults to low reasoning; it is
not an unbounded thinking configuration. The current LLM path allows one retry;
timeout/retry tails and all failed turns must appear in a live campaign.

### P2 — The legacy latency runner does not measure the advertised quantities

`tools/inject_live.py` sends legacy raw data messages, not Urdu microphone audio
or the current bound v2 user-input route. It starts the audio listener after the
send and watches new track-subscription events rather than reliably observing the
existing audio track for every turn. It can miss audio or attribute old audio to
new turns.

Most seriously, the barge-in branch puts **time until audio onset** into
`barge_in_stop_ms`. It neither injects the requested interruption nor measures
audible silence. Its proposed greeting/cold labels also do not establish real
cold joins. `tools/inject.py --wav` is a dry-run placeholder rather than a real
audio measurement path. Do not run these scripts unchanged and label their output
as acceptance evidence for the current Urdu assistant.

`latency_report.reliability_rate` also treats a missing success/completion field as
success. The offline assertion confirms a row with neither outcome field becomes
1/1 completed. Unknown outcomes must be separate from completed turns.

### P3 — Cold-start optimizations are partly nominal

The worker prewarms VAD, but `build_session_kwargs` constructs another VAD before
the integrated factory replaces it with the prewarmed instance. This is an
avoidable load attempt during setup, not measured warm-turn lag. Also,
`GREETING_CACHE=true` is a legacy setting; the integrated factory/runtime never
uses `GreetingCache`. The older frozen configuration describes English pipeline A
and is not a frozen baseline for today's Urdu pipeline.

## Historical component timings, correctly labelled

These saved Phase 1 measurements predate the present configuration. They are not
current Urdu, Groq LLM or browser-heard measurements and must not be summed into
an end-to-end estimate.

| Historical sample | n | p50 | p95 | Actual quantity |
|---|---:|---:|---:|---|
| Gemini Flash-Lite, minimal thinking | 30 | 1,033 ms | 3,784 ms | Entire non-streaming model completion |
| Gemini Flash-Lite, low thinking | 30 | 1,696 ms | 4,542 ms | Entire non-streaming model completion |
| Cartesia Jacqueline, English | 10 | 259 ms | 349 ms | Completed `/tts/bytes` HTTP request |

The LLM CSV's `ttft_ms` deliberately equals total completion time. The TTS spike
uses blocking `client.post` and stops the clock after the body is downloaded, so
its `ttfb_ms` field is not streaming first-byte time. TTS timing rows omit status/
success fields. The other three voice summaries are in `audit.json`.

## Measurement and optimization order

1. Add redacted, bounded per-stage/turn telemetry and a browser/audio onset and
   silence measurement path. Separate cold/warm, text/audio, controls/shopping,
   model step counts, failures and interruptions. Do not log keys or raw audio.
2. Record an actual Urdu baseline: at least 30 ordinary turns and 10 genuine
   interruptions, with device/network/voice/model/settings provenance. Report p50,
   p95 and completion/error counts. A small exploratory sample can find faults,
   but cannot certify the final tail-latency target.
3. Compare a streaming Urdu STT candidate and VAD/endpointing settings one change
   at a time. Preserve natural pauses and correction handling.
4. Reduce repeated model context, duplicate verified reads and unnecessary second
   model steps. Measure provider rate limits and retries alongside success timing.
5. Evaluate shorter first-sentence delivery and avoid the duplicate VAD load. Keep
   interruption/revision/outcome guards intact. Increasing speaking speed does not
   reduce waiting for the first reply.

The project targets above are acceptance goals, not current achievements. A
responsive experience requires reducing the complete audible path, including
network/playback, rather than promising zero latency or quoting provider TTFT.

## Reproduction and scope

```text
From voice-agent/:
.venv/Scripts/python.exe evidence/latency-audit-2026-11-07/collect_audit.py
.venv/Scripts/python.exe -m pytest tests/test_integrated_runtime.py::test_actual_sdk_streaming_llm_and_tool_continuation_use_current_context tests/test_semantic_controls.py::test_real_sdk_invokes_control_tool_and_stops_without_followup_generation -q
2 passed in 7.66s
```

`collect_audit.py` passed lint and generated `audit.json`. It reads saved component
CSVs and exercises the actual runtime/SDK wrappers with local test doubles. Windows
asyncio needed local-socket access outside the restricted sandbox. No model,
STT/TTS or LiveKit provider request occurred. All runtime changes from earlier
work were preserved; this audit adds evidence only. Paid live campaigns and human
listening remain unperformed. This audit cannot certify the speed of a running
deployment or private environment that was not inspected.
