# Architecture Decision Records

Format per entry: **context → decision → evidence → date**.

Newest entries at the top.

---

## ADR-0031 — App-scoped DNS selection with original Redis TLS identity

- **Context:** Actual `.env` Redis preflight failed. Cloudflare/Google and the system
  resolver returned SERVFAIL, including for unrelated `.io` controls. Ordinary Quad9
  resolution enabled successful TCP, certificate/hostname-verified TLS and AUTH/PING
  against the same endpoint. The five-second sequential preflight also timed out
  after DNS was isolated. The user forbids credential/database/TLS changes and deployment.
- **Decision:** Support an optional literal Redis resolver IP using dnspython and a
  small native SSL connection subclass. Preserve original hostname/SNI, full certificate
  verification, credentials, quota ledger and system DNS; respect DNS TTLs and fail
  closed. Set the verified Quad9 resolver only in the local environment. Permit
  bounded cold-connection/preflight time and expose sanitized failure stage/type.
  Do not pin IPs, set checking-disabled DNS flags, purchase services or change Cloud.
- **Evidence:** [Actual connection report](../evidence/redis-connection-2026-11-09/report.md).
  Real final `check-capacity` exit 0, including two-client transaction/reservation
  checks. Focused 49 passed; full suite 521 passed / one inherited failure; lint/types
  passed. Broader replica/failover consistency remains the separate ADR-0030 audit.
- **Date:** 2026-11-09

---

## ADR-0030 — Qualify free shared storage without weakening reservation guarantees

- **Context:** The user requires a $0 datastore, specifically an Upstash Free native
  TCP audit, real concurrency checks, interruption/database-failure coverage and no
  unapproved architecture or deployment change. Upstash documents TCP WATCH/CAS
  support but also eventual consistency and connection-local causal guarantees;
  those documents do not establish the strict failover/no-lost-history contract.
- **Decision:** Preserve the Redis architecture, namespace, quota policy, cart tools
  and deployed worker. Fix conservative aging and incomplete-stream settlement,
  reject TLS verification overrides, and stop ambiguous network-origin WatchError
  admission. Replace the one-client preflight with forced two-client conflicts and
  quota checks. Explicitly separate command compatibility and finite test evidence
  from service-level consistency/durability qualification. Propose free Durable
  Objects or existing-hardware Redis before any architecture replacement; do not
  purchase features, silently accept weaker accounting, or claim Upstash is broken
  based solely on a simulated rollback counterexample.
- **Evidence:** [Audit](../../deployment/ZARA_UPSTASH_FREE_AUDIT.md) and
  [test report](../evidence/upstash-free-2026-11-09/report.md). Four initial adversarial
  failures were reproduced; final full suite 514 passed / one inherited failure;
  scoped lint/types passed. No configured local Redis URL or actual hosted test,
  provisioning, billing change or Cloud rollout occurred.
- **Date:** 2026-11-09

---

## ADR-0029 — Predictive admission against shared, authorized Groq quotas

- **Context:** The user requested capacity selection before every Groq LLM request,
  concurrency across workers, natural Urdu exhaustion recovery and Cloud deployment.
  They reported Groq email approval for separate accounts and will configure Redis
  after receiving a guide. Existing routing, prompts, providers and cart authority
  must survive selection/recovery.
- **Decision:** Admit fully serialized native Groq requests through atomic Redis
  reservations per model/organization. Include prompts/history/tools in conservative
  token predictions and bound output. Default all credentials to one shared pool;
  separate pools require explicit approval configuration. Keep native LiveKit streams
  and one connection pool. Disable both SDK retries; retry only a definitive HTTP 429
  received before any stream output, once per authorized independent pool. Preserve
  uncertain token charges, provider cooldowns and existing no-replay cart guards.
  Use SQLite only for single-host local development, never as a Cloud fallback.
  Require a functioning shared TLS ledger before replacing the existing Cloud worker.
- **Evidence:** [Capacity report](../evidence/groq-capacity-2026-11-08/report.md):
  23 capacity tests passed; full suite 497 passed / one inherited mock-import failure;
  lint/types passed. Cloud deployment stopped at missing Redis preflight; local
  image build failed on Docker Hub DNS. No live quota exhaustion or audio result is
  claimed. [Redis guide](../../deployment/ZARA_REDIS_CAPACITY_SETUP.md) includes exact
  configuration, secure secret upload and rollout commands.
- **Date:** 2026-11-08

---

## ADR-0028 — Fresh page conversations and independent worker lifetime

- **Context:** The user requires refresh to restart Zara's conversation while stopping
  assistance must keep the shared worker available. Persisted activation could send
  resume on a fresh page, and overlapping stop/disconnect/restart sent duplicate cleanup.
- **Decision:** Keep conversation activation document-local, preserve only the cart
  attachment and cleanup identity across refresh, and reload persisted BFCache views.
  Coalesce generation teardown and block replacement until confirmed cleanup. An
  explicit manual choice wins over automatic reload recovery. End only that caller's
  room/dispatch; preserve the shared Cloud deployment and production prewarming.
  Cloud plan idle-scaling policy remains external to session teardown; no billing
  upgrade, fake keepalive session or permanently open microphone is introduced.
- **Evidence:** [Lifecycle audit](../../website/docs/ZARA_LIFECYCLE_AUDIT_2026-11-08.md).
  Authenticated status showed the existing worker Running with one replica. JavaScript
  and Chromium fixtures cover refresh, cleanup races and activation boundaries; these
  do not establish production audio acceptance or guaranteed idle hosting.
- **Date:** 2026-11-08

---

## ADR-0027 — Cloud worker with an explicitly hosted shared backend

- **Context:** The user authorized actual FoodEase Cloud deployment and secure Vercel
  integration, superseding the completed historical phase boundaries. The production
  frontend points to localhost; existing cart and assistance stores are in memory.
  The user confirmed no backend exists and will host it on Render.
- **Decision:** Deploy the existing named worker once in Mumbai with locked/nonroot
  Docker inputs and Cloud secrets. Keep the providers and thirteen guarded operations.
  Combine existing cart/session services in one long-running backend process, with
  Vercel as an owner-bound same-origin stateless gateway. Reject Cloud jobs without a
  public HTTPS callback; do not use localhost or a mock. Reuse prewarmed VAD and record
  supported SDK timing fields without transcripts. Require a shared durable store
  before multiple backend processes/replicas or restart recovery can be supported.
  No paid hosting plan, quota upgrade, Git publication or unrelated Cloud agent was changed.
- **Evidence:** [Deployment report](../../deployment/DEPLOYMENT_REPORT_2026-11-08.md).
  Actual Cloud deployment/status/logs and disposable RTC dispatch passed. The live
  provider probe failed explicit-quantity ordering and consecutive turns (Groq 429);
  these are open acceptance issues, not production success. Render/Vercel hosting
  steps and physical audio acceptance are explicitly pending.
- **Date:** 2026-11-08

---

## ADR-0026 — Targeted Zara review and explicit browser wake opt-in

- **Context:** The user requested review and implementation against the current assistant,
  preserving working integrations rather than restarting the completed historical phase plan.
  Urdu providers, actual shopping tools and guarded demo checkout already exist; browser
  wake activation, everyday persona detail and Roman reference validation needed work.
- **Decision:** Keep the existing providers, thirteen wire operations and authority. Add
  a context-driven Urdu persona, verified presentation sorting, finite Roman reference and
  consent validation, speech formatting and additional casual-success guards. Browser wake
  recognition is an explicit per-page manual-mode opt-in, with remote-processing disclosure,
  native-end and lease-release handoff, duplicate latch and no ambient transcript forwarding.
  Disable it while Zara speaks/in active assistance and on manual/end/background. Retain
  gesture-gated welcome and button/typing fallbacks. Cartesia's documented English-only
  emotion tags are not used for Urdu; do not claim measured human-like audio quality.
- **Evidence:** [Review](../../website/docs/ZARA_REVIEW_2026-11-08.md) and
  [verification](../evidence/zara-followup-2026-11-08/report.md). Provider documents were
  checked against installed Cartesia plugin 1.8.4. No dependencies, keys or contracts changed.
- **Date:** 2026-11-08

---

## ADR-0025 — Semantic conversation controls without phrase allowlists

- **Context:** The user explicitly requested natural wording for ending assistance
  and other conversation requests. The Urdu follow-up still routed controls using
  fixed English/Urdu phrases. That user requirement supersedes the original
  phase's lexical fast-path requirement for the integrated website assistant.
- **Decision:** Remove the active control/page phrase routers and the Urdu
  control phrase sets. Add one local `conversation_control` model tool with a
  bounded set of effects. This is not a fourteenth website operation: the thirteen
  business operations and frozen transport stay unchanged. Validate turn/session,
  revision, mode and replay state before any effect. Interpret free-form wording
  in the LLM, including ending, onboarding mode choice and page/list requests.
  During onboarding and pause/mute, expose only this tool and reject shopping
  in code. Restrict onboarding context to ordering modes. Use SDK `StopResponse`
  after a completed control to prevent duplicate acknowledgments/continuations.
  Keep direct UI revocation, correlated business outcomes, reference freshness and
  exact post-summary checkout consent in code. Spoken activity still interrupts
  current output; semantic spoken control completion now depends on the LLM.
- **Evidence:** Installed 1.8.4 and current official SDK docs for function tools,
  tool restriction and `StopResponse`; native SDK scripted-tool test; full offline
  suite and catalog-extension test in the
  [report](../evidence/semantic-controls-2026-11-07/report.md). Live paraphrase
  classification and audible stop timing were not evaluated. The legacy standalone
  English harness retains its earlier control matcher.
- **Date:** 2026-11-07

---

## ADR-0024 — Urdu integrated assistant and semantic menu interpretation

- **Context:** The requested Urdu assistant needs recognition, synthesis, delivery
  and consent in the same language. The initial menu repair special-cased a few
  English words, which does not provide general interpretation of paraphrases or
  translated requests. This follow-up explicitly authorizes Urdu beyond the
  original English-only phase plan; the read-only plan files remain untouched.
- **Decision:** Remove the shopping keyword parser. Use the existing LLM/tool
  path with real category/product context for free-form shopping language, and
  code-owned price boundaries/full-result presentation. Default the integrated
  website runtime to Urdu. Reuse the installed Groq Whisper plugin, explicit
  `language=ur`, and Silero VAD; do not use English Flux or the English semantic
  turn detector for Urdu. Reuse Sonic 3.6 with explicit Urdu and disable word
  timestamps unsupported by the installed plugin for this language. Localize
  deterministic messages, catalog display names, numbers and exact checkout
  summaries. Keep finite stop/mode/reference/consent controls in code. A missing
  checkout item/fee translation blocks confirmation rather than marking an
  incomplete summary delivered. No new dependency or wire-contract field is used.
- **Evidence:** Installed LiveKit plugins 1.8.4 signatures and capabilities;
  current official Cartesia/Groq/LiveKit documentation; offline regression
  results and limits in the [follow-up report](../evidence/urdu-2026-11-07/report.md).
  Provider recognition, model paraphrase quality, accent and audible latency have
  not been measured in this follow-up. Existing provider quota limits still apply.
- **Date:** 2026-11-07

---

## ADR-0023 — Default to Groq and validate Cartesia voice configuration

- **Context** FoodEase encountered intermittent Gemini 503s, and Cartesia rejected
  a malformed local voice ID. The default voice from the environment template
  synthesized audio successfully through the locked LiveKit Cartesia plugin.
- **Decision** Default to Groq GPT-OSS 20B and retain Gemini as an explicit
  selection. Import the Groq plugin on the worker's main thread before Windows
  job threads start. Use the tested Cartesia voice for blank or malformed IDs
  and keep valid custom UUIDs.
- **Evidence** The live Chromium test received the greeting and the reply to a
  synthetic spoken menu question. A second request in the same session hit
  Groq's 8,000-token-per-minute free-tier limit. The worker regression suite and
  dependency lock check passed.
- **Date** 2026-11-06

---

## ADR-0022 — Accessible website entry on the existing integrated voice owner

- **Context:** The integrated provider/runtime and shared website authority were
  present, but visible welcome/reactivation controls were missing, full-sentence
  choices could fail deterministic matching, and failed teardown had no useful
  explicit retry. Native shopping dialogs also make body-level controls inert.
- **Decision:** Reuse the existing AssistanceController and bound LiveKit seats.
  Derive presentation from its lifecycle, actual media tracks and canonical agent
  status. Move one launcher into active shopping dialogs and reuse the original
  typed form/transcript in a native voice control panel. No capture/autoplay is
  attempted before a gesture. A requested retry reconciles the old server owner
  before replacement; a later manual/end intent revokes a pending retry. Match
  clear full-utterance mode phrases, retain ambiguity/negation refusal, and echo
  an actual mode switch through the existing control event. Keep structured
  application tools and confirmation unchanged. Ask for missing quantity and
  offer only actual returned customizations. Preserve all provider/model choices.
- **Evidence:** Regression results and precise live limitations in the
  [follow-up report](../evidence/voice-entry-2026-11-04/report.md). No new SDK API,
  wire field, dependency or private configuration was introduced. Human/provider
  evidence remains open; synthetic capture and fixture model turns do not close it.
- **Date:** 2026-11-04

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
