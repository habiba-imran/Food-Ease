# Architecture Decision Records

Format per entry: **context → decision → evidence → date**.

Newest entries at the top.

---

## ADR-0021 — Final stack delivery and evidence-gated acceptance

- **Context:** Habiba authorized completion of final orchestration Phase 9. The
  final website needs reproducible PowerShell launch and shutdown, safe recording
  defaults, and acceptance evidence that cannot confuse offline tests with live
  conversation. The installed worker CLI resolves authentication before job entry.
- **Decision:** Launch the actual website, owner-bound session service and named
  integrated worker on distinct configurable loopback ports. Load worker dotenv
  before CLI resolution; never inspect or print its contents. Manual mode strips
  credentials, disables dotenv/dispatch and starts no worker. Live launch requires
  explicit cost opt-in. Own exact child processes, request graceful shutdown over
  private stdin, and never kill an unknown port owner. Allow a bounded configurable
  startup deadline (180 seconds by default, at most 600) for cold native imports;
  a deadline failure must clean up exact owned processes. Read private control-pipe
  bytes only after readiness polling, using Windows PeekNamedPipe or POSIX select;
  a blocking Python/CRT stdin lock can deadlock NumPy initialization. Support both
  installed Python 3.11 and 3.12. A forced stop fails the launcher. Give public SDK
  job initialization 60 seconds for cold VAD loading. Correlate redacted session,
  generation, turn/action and dispatch log fields with explicit evidence provenance.
  Disable SDK recording with `AgentSession.start(record=False)`, in addition to
  environment defaults, and disable unused RemoteSession hosting with
  `session_host=False`. The custom authenticated thirteen-operation transport
  remains the browser control path; frozen contracts and business authority stay
  unchanged. Prepare all 63 O/W/T scenarios as not run. Evaluate operator-attested
  device/accessibility/fault observations and real audible measurements without
  substituting synthetic browser media or server latency. Retire no waiver without
  its replacement evidence.
- **Evidence:** Installed agents 1.8.4 public `AgentSession.start()` signature and
  recording/default-host logic; official [session API](https://docs.livekit.io/reference/python/livekit/agents/index.html),
  [recording options](https://docs.livekit.io/reference/agents/session-recording-options/)
  and [startup modes](https://docs.livekit.io/agents/server/startup-modes/).
  A worker-entrypoint regression first failed because `record` was absent, then
  passed with explicit recording/hosting flags. A configured-stack attempt exposed
  the fixed 60-second cold-import limit; timeout/cleanup regressions failed before
  implementing the configurable deadline. A held-open stdin probe reproduced the
  import deadlock; a child-process regression for buffer inspection and graceful
  stop now passes on both installed Python interpreters. A transient use of Windows
  os.set_blocking was rejected because the website runs Python 3.11; the final
  readiness probe uses [documented PeekNamedPipe](https://learn.microsoft.com/windows/win32/api/namedpipeapi/nf-namedpipeapi-peeknamedpipe).
  See the
  [final runbook](../../orchestration/docs/FINAL_RUNBOOK.md) and
  [Phase 9 report](../../orchestration/evidence/final/phase-09/report.md) for observed
  test results and open live/human checks. No provider or listening result is inferred
  from the offline verifier.
- **Date:** 2026-10-18

---

## ADR-0020 — Recovery barriers and honest retained outcomes

- **Context:** Habiba authorized final orchestration Phase 8. Transport loss, exhausted
  providers and reload needed explicit runtime behavior without changing the v2
  schema, retrying business writes or reopening microphones without current consent.
- **Decision:** Handle public SDK provider errors in the production runtime: exhausted
  speech dependencies degrade to silent typing; model failure leaves manual mode.
  Revoke old turn/confirmation/reference authority before recovery, reconcile only
  original action IDs, fetch fresh session state even at an unchanged revision and
  correlate the resume acknowledgment through the existing optional turn ID.
  Browser reconnection waits for both seats and stops after 15 seconds; already
  paused/undecided modes do not become voice. Backgrounding and credential expiry
  end locally and require another gesture. Persist minimal cleanup identity without
  credentials; hold a Web Lock where supported and retain server generation admission.
  `not_seen` does not prove a delayed request cannot arrive. Expired records remain
  explicitly unverifiable. Preserve owned writes through speech cancellation/shutdown.
- **Evidence:** [Phase 8 handoff](../../orchestration/docs/PHASE_08_RECOVERY.md) and
  [offline results and live limitations](../../orchestration/evidence/final/phase-08/report.md).
  Installed agents 1.8.4 emits provider errors before its close decision; public
  recoverable flags preserve the healthy text lane. Local provider subclasses test
  actual SDK forwarding. Native browser media tests use synthetic capture, while
  RTC/lifecycle/provider outages are local substitutes. No vendor-outage or audible
  barge-in measurements are claimed; these and Phase 7 listener validation stay open.
- **Date:** 2026-10-17

---

## ADR-0019 — Semantic conversation and completed-output references

- **Context:** Habiba authorized final orchestration Phase 7. The integrated model
  had raw snapshots, but references were populated from all returned search rows
  before output, filters lacked granular refinement, and multi-step writes needed
  bounded duplicate/failure admission.
- **Decision:** Add a bounded semantic page with current actions and verified
  details. Exact page/list/button commands use the existing broker; natural
  recommendation/comparison/paraphrases retain the actual model path. Build ordinal
  references from completed SDK output in delivered name order, including overlapping
  names and pronunciation variants. Invalidate them on manual changes. Merge filter
  arguments after fresh-state serialization, retain explicit clear controls, cap
  turn operations and reject repeated normalized mutations or writes after a failed
  step. Keep the thirteen operations and checkout authorization unchanged. Apply
  existing speech shaping at streaming sentence boundaries before audio/caption
  branching, fixing fractional digit preservation. Declare production speech-control
  capability from the configured supported Sonic model and invoke public SDK options.
- **Evidence:** Installed LiveKit Agents/Cartesia/Google 1.8.4 source/declarations,
  official node/provider references, Phase 7 worker/browser checks and the separately
  prepared real-model campaign. Real-model and human listening gates remain open;
  local fake-model and legacy scripted metrics cannot pass them. No provider key was
  loaded, no paid calls or human ratings were produced, and no next phase was started.
- **Date:** 2026-10-17

---

## ADR-0018 — Consent-gated opening and explicit mode continuity

- **Context:** Habiba authorized final orchestration Phase 6. The existing worker
  required a selected mode, and the browser needed a safe spoken chooser without
  treating its answer as a food request or reopening capture after manual choice.
- **Decision:** Reuse frozen v2 Control intents: start/voice opens a deterministic
  chooser; switch_mode selects directly; resume with a mode gives a brief return.
  Only clear mode/help/exit input is admitted while choosing, with one bounded
  clarification and no model or shopping execution. Deduplicate the opening per
  generation. Use explicit browser states and gesture-based startup for every
  visit, including returning visitors; a session-bound resume marker changes copy
  only. Manual revokes local media/output before remote cleanup while owned
  committed writes retain their outcome. Voice to typing stops capture in place;
  returning to voice requires explicit activation. Typed audio is silent by default
  and separately enabled without capture. Test native Chromium synthetic capture
  and generated HTML media playback; do not equate this with physical devices,
  provider audio, Cloud signaling or conversational listening evidence.
- **Evidence:** `../../orchestration/docs/PHASE_06_OPENING_MODES.md`, installed
  livekit-client 2.15.4 public declarations/source, official references in that
  handoff and `../../orchestration/evidence/final/phase-06/report.md`. Headless shell
  returned NotSupported for native capture; full Chromium's synthetic device is
  used for the media lifecycle tests. Contracts remain unchanged.
- **Date:** 2026-10-17

---

## ADR-0017 — Versioned browser seats, one renderer and canonical captions

- **Context:** Habiba authorized final orchestration Phase 5 only. The page still
  used mock assistant handlers and display-only filters, while the integrated
  worker and shared contract already required bound v2 RPCs and delivery receipts.
- **Decision:** Use a pinned, locally bundled livekit-client 2.15.4 and the existing
  lifecycle controller. Connect distinct app/user seats, verify binding/caller
  roles and preserve original action envelopes. Serialize manual/worker operations
  through the website authority and one revision-aware renderer; publish context
  only after rendering. Reconcile unknown original actions read-only and preserve
  pending identity metadata across reload without storing checkout tokens. Use the
  frozen `foodease.events.v2` channel for status/captions/control, display each
  utterance once, and retain native LiveKit audio as the only audio source. Admit
  typed input only after lifecycle activation; early SDK listening cannot unlock
  it. Reuse the existing transcript/form inside active typed dialogs and acknowledge
  the exact current summary only after visible rendering. Keep the opening chooser
  in Phase 6. A real-browser fixture uses real website/worker/SDK logic with local
  fake RTC/lifecycle/LLM; it does not establish Cloud or provider/audio activation.
- **Evidence:** `../../orchestration/docs/PHASE_05_BROWSER_INTEGRATION.md` and
  `../../orchestration/evidence/final/phase-05/report.md`, installed JS/Python public
  SDK declarations/source and official references linked from the browser handoff.
- **Date:** 2026-10-17

---

## ADR-0016 — One integrated SDK runtime with owned actions and delivered consent

- **Context:** Habiba authorized final orchestration Phase 4 only. The legacy live
  worker registered ten tools, used a global commit flag, lacked current context
  injection and did not attach delivered checkout consent to the website authority.
- **Decision:** Attach a separate v2 SDK agent through the Phase 3 startup factory.
  Reuse deterministic confirmation, reference, preferences, idle and interruption
  components in one shared runtime for actual live tools and text-driven tests.
  Keep the streaming providers and public SDK nodes; force preemptive generation
  off. Bind each reply handle to an exact committed message/epoch, validate fresh
  context and all thirteen operations, and own shielded action tasks before send.
  Lookup unknown outcomes without write retry. Queue the exact checkout summary
  without awaiting its parent tool's speech; accept only uninterrupted successful
  delivery with an audio sink, or an exact app-seat post-render receipt for typed
  checkout. Consume exact affirmative consent in code, never from model arguments.
  Initial mode remains unset until explicit selection. Browser wiring and opening
  flow remain Phases 5/6. Guarantees are process-local; live activation is unverified.
- **Evidence:** `../../orchestration/docs/PHASE_04_LIVE_CONVERSATION_RUNTIME.md`,
  Phase 4 verification report, installed LiveKit 1.8.4 public source and official
  turn/tool/audio/Python documentation linked from the runtime document.
- **Date:** 2026-10-17

---

## ADR-0015 — Bound preparation, generation ownership and honest cleanup

- **Context:** Habiba authorized final orchestration Phase 3 only. The old API
  dispatched immediately and accepted client room/dispatch IDs. Failed deletion
  could be forgotten. Installed LiveKit API 1.2.1 also requires a different
  delete_dispatch call signature than the existing wrapper used.
- **Decision:** Add owner-verified v2 lifecycle routes using the real shopping
  authority. Separate credentials/preparation from app/media/playback/context
  readiness, one owned dispatch task and authenticated worker acknowledgement.
  Retain cancellation tombstones and uncertain cleanup; no blind create retry,
  guessed deletion success, arbitrary app destination or mock fallback. Disable
  unbound v1 routes by default and reserve integrated rooms even in legacy dev
  mode. Correct the installed SDK deletion call. Keep browser lifecycle ownership
  as a tested injectable controller; page/SDK wiring is Phase 5. The actual worker
  gate exposes a runtime attachment point; absence of Phase 4's v2 runtime is an
  explicit unavailable/cleanup outcome, never a v1 substitution. Coordination is
  process-local, without durability or Cloud restart-cleanup guarantees.
- **Evidence:** `../../orchestration/docs/PHASE_03_ASSISTANCE_LIFECYCLE.md`, installed
  SDK source, official LiveKit Python API docs, and Phase 3 verification report.
- **Date:** 2026-10-17

---

## ADR-0014 — Shared pure contract and process-local application authority

- **Context:** Habiba authorized final orchestration Phase 2 only. The website
  must enforce the frozen v2 contract without installing the voice stack, and
  manual actions and future app-seat forwarding must use one business authority.
- **Decision:** Extract pure v2 models into the sibling `foodease-contract`
  package while preserving the agent import path. Replace the website singleton
  with bounded anonymous-owner sessions; execute on a copy under a session lock,
  validate output and commit state/revision/result together. Retain accepted
  action outcomes for the session lifetime, reject admission at capacity, bind
  one-use checkout approval to the session/cart/summary, and retain receipts.
  In-memory state requires one process and honest expiry/restart reporting.
  Keep Phase 1 examples hash-pinned as historical captures; current authority
  conformance runs through actual API tests and localhost HTTP checks. No v1
  artifact changes or LiveKit lifecycle/worker activation.
- **Evidence:** `../../orchestration/evidence/final/phase-02/report.md` and
  `../../orchestration/docs/PHASE_02_APPLICATION_AUTHORITY.md`.
- **Date:** 2026-10-17

---

## ADR-0013 — Final integration contract 2.0, opt-in only

- **Context:** Actual website results contain lines/line_total, complete filter
  state is absent from snapshots, live filter arguments mismatch v1, and action
  requests omit expected revision. Mandatory app-side checkout token/summary
  binding would break frozen v1's optional-token promise. Habiba requested only
  final orchestration Phase 1 after the recorded Phase 0 baseline.
- **Decision:** Publish separate v2 executable models, explicit projections,
  schemas/examples and a mirrored handoff. Keep all thirteen semantic operations
  and event names; version transport channels to prevent accidental mixing.
  Define strict metadata/correlation, sender binding, result/status shapes,
  confirmation and read-only reconciliation. Preserve both original v1 trees;
  defer activation and storage/transport enforcement to Phases 2–5.
- **Evidence:** `tests/test_contract_v2.py` reproduces original real-domain
  incompatibilities, then validates all thirteen projected operations. See
  `../../orchestration/docs/PHASE_01_CONTRACT_FREEZE.md` and Phase 1 evidence.
- **Date:** 2026-10-17

---

## ADR-0012 — Phase 10 live audio / usability waived

- **Context:** Phase 10.2 requires live audio runs (≥3 each) for T01–T04, T09, T10, T15, T17, T18, T20. Phase 10.3 is optional usability with fresh participants. Habiba asks to skip and start Phase 11.
- **Decision:**
  1. **10.2 and 10.3 waived** (not failed). No fabricated live or usability scores (R8).
  2. Keep **10.1** automated acceptance record (`evidence/phase-10/acceptance.md`): 18 automated pass; T04/T18 remain `pending_human` / known-limitation under this ADR.
  3. **10.4** deferred (no session breakdowns to fix). Dialogue/safety suites stay as last automated green run.
  4. Close Phase 10 automated gate; proceed to Phase 11 handover. Live must-pass items in V10.2 that need audio stay **documented limitations**, not claimed passes.
- **Evidence:** Habiba instruction 2026-10-02 (“SKIP AND START 11”); checklist empty of live runs.
- **Date:** 2026-10-02

---

## ADR-0011 — Phase 9 live Mode 1 / Mode 2 campaign waived

- **Context:** Phase 9 requires Mode 1 injection (≥30 turns + ≥10 interruptions) and Mode 2 live sessions across multiple devices/conditions (built-in mic, earphones, household noise, venue network). Habiba cannot run that multi-device campaign now and asks to skip and proceed.
- **Decision:**
  1. **Live Mode 1 / Mode 2 measurement and V9.3–V9.4 live sample sizes are waived** (not failed). No fabricated §7 p50/p95 numbers (R8).
  2. Keep Phase 9 **tooling** (campaign manifest, `inject_live`, report generator, interruption fixture sweep, tuning env knobs, V9.5 regression hook). Empty/placeholder latency tables stay labelled incomplete.
  3. Close Phase 9 gate as **waived for live campaign**; proceed to Phase 10. Optional: run Mode 1/2 later before final handover demos if time allows.
- **Evidence:** Habiba instruction 2026-10-02 (“skip… multiple devices… proceed to next”); no Mode 1/2 JSONL with measured timings.
- **Date:** 2026-10-02

---

## ADR-0010 — Phase 6 V6.2 attested; V6.6 / V6.7 waived

- **Context:** Habiba listened to the pronunciation sheet audio and reported all lines OK, but did not fill the markdown herself; asked the agent to record it. Formal dogfooding (10+5 sessions) and listening panel (≥5 listeners, 12 clips, means) were not run — no time / not written.
- **Decision:**
  1. **V6.2 Pass** by human attestation (0 price/qty misreads, 0 dish misreads); sheet filled under `evidence/phase-6/human/pronunciation_sheet.md`.
  2. **V6.6 and V6.7 waived** (not failed, not fabricated). No invented panel means or dogfood tag counts (R8). Delivery stays emotion-off / default pace (6C.2) until a real panel exists.
  3. Close Phase 6 automated+attested gate; proceed when human starts Phase 7.
- **Evidence:** Habiba chat 2026-10-02 (“all are okay… write yourself”); no panel/dogfood raw logs.
- **Date:** 2026-10-02

---

## ADR-0009 — Phase 5 task 5.10 waived (no live conversation)

- **Context:** Task 5.10 asks for ~10 minutes of free conversation (earphones, then speakers) to note echo self-interruption, clipped syllables, odd pauses, and overlaps. The human has no time and accepts the deviation.
- **Decision:** **5.10 is waived** (not failed). No live-session observations exist yet. Echo, clipping, overlap, and false-interruption behavior are **UNTESTED with a real voice and mic**. They **must be tested before Phase 9**. Do not mark any V5 verification that requires live audio as passed. Those items stay **pending**, not waived.
- **Evidence:** Human instruction 2026-10-02; no `evidence/phase-5` live notes or session logs.
- **Date:** 2026-10-02

---

## ADR-0008 — Speculative / preemptive generation safety (Phase 5.7)

- **Context:** Flux eager EOT and LiveKit `preemptive_generation` can start the LLM before the user turn is committed. Task 5.7 requires determining whether a tool can *execute* in a generation later discarded; V5.7 requires **0 cart mutations** from discarded generations.
- **Investigation (livekit-agents 1.8.4):** In `AgentActivity` pipeline reply, LLM may run early, but `perform_tool_executions` is started only **after** `speech_handle._wait_for_authorization()` / play authorization (`agent_activity.py` ~3642–3728: “start to execute tools (only after play())”). Maintainers also state tools run after generation is authorized (livekit/agents#3414). Function *call objects* can be created before authorization; execution is gated by the framework — but races and future SDK changes make this **not a hard product guarantee** for cart mutations.
- **Decision:**
  1. Default **`PREEMPTIVE_GENERATION=false`** (disable speculative LLM) for FoodEase until Phase 9 explicitly re-enables it after live V5.7 proof.
  2. **Belt-and-suspenders:** `TurnCommitGate` refuses mutating / navigation ops until `on_user_turn_completed` marks the turn committed; discarded generations clear the gate.
  3. Pure read tools (`get_cart`, `get_item_details`, `get_current_context`, `checkout.get_summary`) remain allowed without commit.
- **Evidence:** Installed SDK source 1.8.4; unit tests `test_v57_zero_mutations_on_discarded_generation`, `test_agent_tool_blocked_until_committed`.
- **Date:** 2026-10-02

---

## ADR-0007 — Phase 4 V4.2 real-LLM campaign deferred

- **Context:** V4.2 asks for ≥40 real-LLM utterances. Gemini free tier already returned 429 in Phase 1; Phase 4 logic is covered by a scripted fake LLM (V4.1) and RulePlanner acceptance traces.
- **Decision:** Gate Phase 4 on V4.1 + V4.3–V4.8 with the fake/scripted planners. Treat V4.2 as **deferred** to Phase 5/6 when voice+LLM are exercised live (or when quota allows). No fabricated tool-accuracy %.
- **Evidence:** Phase 1 429 logs; Phase 4 test suite 93 passed without live Gemini calls.
- **Date:** 2026-10-02

---

## ADR-0006 — Phase 1 closed early; provisional TTS/LLM choices

- **Context:** Human asked to complete Phase 1 quickly and skip remaining spike work (not mandatory). Full audition scoring, LLM tool/sample campaign, and extra TTS timing were cut. Gemini free tier returned **429 RESOURCE_EXHAUSTED** during latency runs.
- **Decision (provisional, refine in Phase 5/9 from live data):**
  1. **TTS:** Cartesia **`sonic-3.6`**. Primary voice **Jacqueline** (`9626c31c-bec5-4cca-baa8-f8ba9e84c8bc`). Backup **Katie** (`f786b574-daa5-4673-aa0c-cbe3e8534c02`).
  2. **LLM:** **`gemini-3.1-flash-lite`** with **`thinking_level=minimal`**. Fallback **`gemini-2.5-flash-lite`**.
  3. **Speed/volume:** Treated as **available** on sonic-3.6 for now (API accepted `generation_config` in the TTS spike). If live demos disagree, prefer honest “not available” messaging (plan option b).
  4. **Waived (not failed):** V1.3 ear review, V1.4 audition scorecard, V1.5 tool-accuracy ≥90%, remaining LLM/TTS spike volume. Partial evidence kept under `evidence/phase-1/` (TTS CSV + partial LLM CSV). No fabricated metrics.
- **Evidence:** Health checks PASS; `tts.csv` / `tts_meta.json`; `llm.csv` (30+30 latency, 3 tools); human skip instruction 2026-10-02; Cartesia credits used 2524/8000.
- **Date:** 2026-10-02

---

## ADR-0005 — STT fixtures skipped; provisional Flux + STT turn detection

- **Context:** Phase 1 task 1.1 requires ~72 recorded STT fixtures + `fixtures/ground_truth.json`. The human has no time to record and accepts the deviation.
- **Decision:**
  1. **Do not run** the STT spike. A script may exist under `spikes/` but must not be executed without fixtures.
  2. **Provisional STT choice:** Deepgram **Flux English** with **STT-based turn detection** (config A).
  3. **Config B** (Nova-3 + Silero VAD + LiveKit turn detector) remains runnable per plan task 5.1; the **final** STT/turn choice is made from **live-session data in Phase 5/9**, not from fabricated WER numbers.
  4. Verification **V1.1 / V1.2 are waived for the STT portion** (not failed). No invented STT accuracy, WER, or number/price accuracy metrics.
- **Evidence:** Human instruction, Phase 1 session, 2026-10-02.
- **Date:** 2026-10-02

---

## ADR-0004 — Repo layout: Habiba voice agent in `voice-agent/`

- **Context:** Habiba owns the voice agent; Zainab owns frontend/backend. They must not share one mixed tree.
- **Decision:** All Habiba Phase work lives under `HCI-PROJECT/voice-agent/` (this package). Zainab adds a **sibling** folder later (e.g. `website/`). Root `HCI-PROJECT/README.md` only describes the boundary. Open `voice-agent/` as the Cursor workspace for agent phases.
- **Evidence:** Human instruction at Phase 0 close, 2026-10-02.
- **Date:** 2026-10-02

---

## ADR-0003 — LiveKit Cloud region (Phase 0 human decision)

- **Context:** Plan task 0.2 asks for the LiveKit Cloud region closest to test/demo.
- **Decision:** Region remains **auto-routed** on the free plan; region pinning is Scale-only and unavailable for this project tier.
- **Evidence:** Human report, 02 Oct 2026 (Phase 0 kickoff update).
- **Date:** 2026-10-02

---

## ADR-0002 — livekit-agents install deferred to Phase 1

- **Context:** Plan architecture cites `livekit-agents ~1.5`. Phase 0 is foundations only ("nothing voice-related yet"). PyPI current line as of this scaffold is `1.8.x` (requires Python `>=3.10,<3.15`).
- **Decision:** Do **not** install `livekit-agents` in Phase 0. Record candidates in `docs/versions.md`. Phase 1 will pin the exact SDK after reading docs for the installed version (R7); if the pin is not `~1.5`, add a follow-up ADR.
- **Evidence:** Phase 0 scope; PyPI `livekit-agents` info version `1.8.4` checked 2026-10-02.
- **Date:** 2026-10-02

---

## ADR-0001 — Type checker is pyright

- **Context:** Phase 0 allows `pyright` or `mypy`.
- **Decision:** Use **pyright** (`uv run pyright`) for the scaffold.
- **Evidence:** Chosen at Phase 0 scaffold; recorded in `AGENTS.md` Commands.
- **Date:** 2026-10-02
