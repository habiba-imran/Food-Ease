# FoodEase Voice Agent — Implementation Plan (Habiba's scope only)

**Version 1.1 (audited) · 02 Oct 2026**
**Source of truth:** *Voice Agent Requirements & Final Deliverables Specification v1.0* (VA-01…VA-17, tests T01–T20, 10 handover deliverables).
**Out of scope:** Zainab's website and the final orchestration layer. Nothing in this plan waits on either (see §0.5).

**End-state goal:** a standalone LiveKit voice agent that is genuinely conversational: it sounds natural and comfortable (Cartesia), talks in short human phrasing, handles vague requests, corrections and interruptions gracefully, responds fast, and never claims an action succeeded unless the app verified it. Demonstrated against a mock app, ready to plug into the real website later.

---

## 0. How to use this plan

### 0.1 Legend

| Tag | Meaning |
|---|---|
| **[AGENT]** | Task for the coding agent (e.g. Claude Code). |
| **[HUMAN]** | Only Habiba can do this (accounts, listening, speaking into a mic, running sessions). The agent stops and waits. |
| **[LATER]** | A decision that needs both Habiba and Zainab. It has a Habiba default, is made at integration time, and **never gates a phase**. |
| **P0 / P1 / P2** | P0 = core for a credible demo (default if untagged). P1 = finish if time allows. P2 = stretch. |
| **Size** | S ≈ half a day, M ≈ 1–2 days, L ≈ 3+ days (rough, agent-assisted). Give me a deadline and I'll convert this to a calendar. |

### 0.2 Gate rule

Every phase ends with a **Gate**. Do not start the next phase until every Gate item passes and evidence is saved in `evidence/phase-N/`. Tag the commit `phase-N-done`. (Phases 6A–6C may run in parallel with Phase 5 once Phase 4 is done; see Phase 6.)

### 0.3 Non-negotiable rules (every phase)

| # | Rule |
|---|---|
| R1 | **Truth.** The agent speaks outcomes only from an `app.action_result` (or mock equivalent) whose `action_id` matches the request. Generated text never implies a completed action without it. |
| R2 | **Allowlist.** Only these 13 operations exist: `navigate`, `search_menu`, `filter_menu`, `select_item`, `get_item_details`, `get_cart`, `cart.add_item`, `cart.set_quantity`, `cart.remove_item`, `checkout.get_summary`, `checkout.submit_demo_order`, `undo_last_reversible_action`, `get_current_context`. Anything else is rejected in code before leaving the agent. |
| R3 | **Facts come from tools.** Prices, totals, fees, stock, ingredients and order status are never taken from model memory. If the data isn't provided, the agent says it doesn't have it. |
| R4 | **No blind retries.** A mutating action that fails or times out is never resubmitted automatically. Outcome `unknown` means reconcile (refresh context / `get_cart`), then ask the user. |
| R5 | **Speech cancel ≠ action cancel.** Interrupting audio never cancels or assumes the result of an in-flight mutation. |
| R6 | **No secrets exposed.** Keys live only in `.env` (git-ignored) and the server. Browser tokens are minted server-side with short TTL. The system prompt and keys never reach the browser, handover docs or recordings. Dev-only control surfaces are off unless `DEV_MODE=true`. |
| R7 | **Docs first.** Before using any LiveKit / Deepgram / Cartesia / Gemini API, read the current docs for the *installed* version. Pin versions in `docs/versions.md`. API names here are as of 02 Oct 2026 and may have moved. If docs contradict this plan, follow the docs, log it in `docs/decisions.md`, tell the human. |
| R8 | **No fabricated metrics.** Every reported number comes from raw logs. Simulated latency is never reported as measured. |
| R9 | **No fake humanness.** No synthetic stutters or repeated fillers. A "still working" line is allowed only after a real wait threshold and only if truthful. |
| R10 | **Scope discipline.** No website UI, auth, database, payments or real inventory. The harness is a dev tool, not product UI. |
| R11 | **Tests or it didn't happen.** A task isn't done without automated tests (logic) and its listed manual checks (audio). Failures and skips are documented. |
| R12 | **Small, traceable commits.** One branch per phase, conventional commits, an evidence report per phase. |
| R13 | **Fictional data only; no recordings by default.** No real personal data in any prompt, fixture or session. Audio/transcript retention is off by default (`RECORD_AUDIO=false`); anything captured needs consent and a deletion plan. |
| R14 | **Prompt changes are regression-tested.** Any edit to the policy prompt re-runs the truthfulness/safety suite (V4.4/V4.5) and the dialogue suite (Phase 6) before it is accepted. |

### 0.4 Coding-agent operating protocol (every session)

1. Read `docs/SPEC.md` (copy of the requirements spec), this plan's current phase (`docs/PLAN.md`), `docs/decisions.md` and the contract.
2. Restate the phase's tasks and Gate in 3–5 lines before coding.
3. For logic-type work, write tests first.
4. When finished, run every Verification item and write `evidence/phase-N/report.md` (commands, results, redacted logs).
5. Stop at every **[HUMAN]** step. Never invent human results (listening scores, spoken tests, quotas).
6. Never print, log or commit secrets. Never claim a check passed without running it.

**Kickoff prompt template (per phase):**
> "Read `docs/SPEC.md`, `docs/PLAN.md` Phase N, `docs/decisions.md`. Follow rules R1–R14 and the operating protocol. Restate the tasks and Gate, then implement Phase N only. Stop at any [HUMAN] step. Finish by writing `evidence/phase-N/report.md`."

### 0.5 Independence principle (Zainab is never a blocker)

Zainab's spec is already with her and she starts next month. This plan therefore treats her work as **future input, never a prerequisite**:

1. **You own and freeze the contract.** Contract v1.0 = the names and fields already in the spec (§6), completed with sensible defaults where the spec is silent. You freeze it yourself in Phase 2.
2. **The agent has its own canonical domain model** behind the `AppAdapter` interface. The wire format (RPC method names, topics, payload shapes) is handled *only* in `LiveKitRpcAdapter`. If Zainab's implementation differs, you change that adapter (and bump the contract minor version), never the conversation logic.
3. **Everything not in the spec is optional on the wire.** In particular, the checkout `confirmation_token` is optional: the agent enforces confirmation itself (bound to summary hash + cart revision) whether or not the app issues a token.
4. **Open joint questions** are listed in Phase 11 as **[LATER]** items with your default. If she reviews early, fold her feedback in as a minor version; if not, nothing stops.
5. **Self-serve handover.** A quick-start page for the frontend is written so she can integrate without a meeting.
6. **You rehearse the integration yourself** with a mock app that uses the *real* transport (Phase 7), so a later swap is "register these methods on the website".

---

## 1. Architecture at a glance

```
Browser client (harness now, Zainab's website later)  ← user mic + captions
        ⇅  LiveKit room: audio, transcription streams, agent state, RPC, data topic
Agent worker (Python, livekit-agents ~1.5)
 ├─ AgentSession: STT (Deepgram) → turn detection → LLM (Gemini) → TTS (Cartesia)
 ├─ Control fast-path  (stop / repeat / slower / pause … handled in code, no LLM)
 ├─ Conversation policy + context injection (bounded snapshot, revision-checked)
 ├─ Interaction-risk tiers + confirmation machine (code, not prompt)
 ├─ ActionBroker  (validate → action_id → submit → await → verified outcome)
 ├─ AppAdapter interface
 │     ├─ MockAdapter (in-process; unit tests, text CLI)
 │     └─ LiveKitRpcAdapter (real transport; talks to MockApp now, the website later)
 ├─ EventBus  (versioned envelope events)
 └─ Metrics logger  (per-turn JSONL)
MockApp participant (separate Python process, dev only) — plays "the website" over RPC
```

**Key design decision:** voice logic depends only on `AppAdapter`. Replacing the mock with the website changes only who answers the RPC calls.

**Suggested repo layout**

```
foodease-voice-agent/
  src/foodease_agent/
    config.py  session.py  agent.py  broker.py  confirmation.py  controls.py  idle.py
    speech_text/            # sanitizer, verbalizer, pronunciation, chunking
    adapters/  base.py  mock.py  livekit_rpc.py
    events.py  metrics.py
  mock_app/                 # MockApp participant (dev only)
  contract/v1/              # JSON Schemas, examples, DECISIONS.md
  prompts/                  # agent_policy.vN.md + CHANGELOG.md
  harness/                  # browser client + token server (dev only)
  tools/                    # injection test client, report scripts
  spikes/  tests/  evidence/  docs/
  .env.example
```

---

