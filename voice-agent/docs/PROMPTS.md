# Paste-ready prompts for Cursor

Use one **fresh chat per phase** (or per sitting). Each prompt is self-contained; the `@` references pull in the right files.
If a `@file` doesn't exist yet (for example `docs/decisions.md` before Phase 0), Cursor will just skip it.

Workflow per phase:
1. `git checkout -b phase-N-<slug>` (the branch name is in each prompt).
2. Paste the phase prompt. Read the agent's 3 to 5 line restatement. Reply **go** (or correct it).
3. Do your [HUMAN] tasks when the agent stops (checklist in `docs/STATUS.md`).
4. Review the diff and `evidence/phase-N/report.md` yourself. Don't just trust "all green".
5. Merge, tag `phase-N-done`, update `docs/STATUS.md`, refresh the graphify graph (after Phase 3).

---

## Phase 0 — Foundations

```
@AGENTS.md @docs/STATUS.md @docs/plan/phase-00.md
Branch: phase-0-foundations.
SPEC sections for this phase (read only these from @docs/SPEC.md): §3 (provider profile) and VA-16 (secrets).
Phase 0 only. Do tasks 0.3, 0.4 and 0.5 only. Skip 0.1 and 0.2 (they are mine). docs/SPEC.md and docs/PLAN.md are already in docs/, so skip the copy step. AGENTS.md, .gitignore, .cursorignore and .graphifyignore already exist: don't overwrite them. Once the scaffold works, fill in the Commands section of AGENTS.md.
Restate the tasks and Gate in 3 to 5 lines, then wait for my "go".
Skip [HUMAN] tasks and tell me exactly what I need to do.
Don't call any provider API in this phase.
Finish by running every Verification item not marked [HUMAN] (list the [HUMAN] ones as pending for me), writing evidence/phase-0/report.md, and updating docs/STATUS.md.
```

## Phase 1 — Provider spikes

```
@AGENTS.md @docs/STATUS.md @docs/decisions.md @docs/plan/phase-01.md
Branch: phase-1-provider-spikes.
SPEC sections for this phase (read only these from @docs/SPEC.md): §3, §7 (quality notes) and VA-04.
Phase 1 only. Write throwaway scripts under spikes/ and raw CSV output under evidence/phase-1/. Before the STT spike, check that fixtures/ground_truth.json exists; if it doesn't, stop and tell me. Stop for the voice audition (1.2) and the read-aloud check (1.3) and wait for my scores. Never open or print .env.
Restate the tasks and Gate in 3 to 5 lines, then wait for my "go".
Skip [HUMAN] tasks and tell me exactly what I need to do.
I approve calls to the provider APIs this phase's tasks need, using the keys in .env. Don't open or print .env, and keep calls to the minimum the tasks require.
Finish by running every Verification item not marked [HUMAN] (list the [HUMAN] ones as pending for me), writing evidence/phase-1/report.md, and updating docs/STATUS.md.
```

## Phase 2 — Contract v1.0

```
@AGENTS.md @docs/STATUS.md @docs/decisions.md @docs/plan/phase-02.md
Branch: phase-2-contract.
SPEC sections for this phase (read only these from @docs/SPEC.md): §6 (VA-10 to VA-14), VA-07, VA-09 and §9 (VA-17).
Phase 2 only. Do tasks 2.1 to 2.4. Stop before 2.5 so I can review the contract against the spec and tag it myself. Skip 2.6.
Restate the tasks and Gate in 3 to 5 lines, then wait for my "go".
Skip [HUMAN] tasks and tell me exactly what I need to do.
Don't call any provider API in this phase.
Finish by running every Verification item not marked [HUMAN] (list the [HUMAN] ones as pending for me), writing evidence/phase-2/report.md, and updating docs/STATUS.md.
```

## Phase 3 — Adapter interface and mock app

```
@AGENTS.md @docs/STATUS.md @docs/decisions.md @docs/plan/phase-03.md
Branch: phase-3-adapters-mock.
SPEC sections for this phase (read only these from @docs/SPEC.md): VA-06, VA-09, VA-14, and tests T08, T09, T13, T14 in §10.
Phase 3 only. Voice code must import only the AppAdapter interface (check V3.5). Include every trap listed in task 3.2.
Restate the tasks and Gate in 3 to 5 lines, then wait for my "go".
Skip [HUMAN] tasks and tell me exactly what I need to do.
Don't call any provider API in this phase.
Finish by running every Verification item not marked [HUMAN] (list the [HUMAN] ones as pending for me), writing evidence/phase-3/report.md, and updating docs/STATUS.md.
```

## Phase 4 — Conversation engine (text mode)

```
@AGENTS.md @docs/STATUS.md @docs/decisions.md @docs/plan/phase-04.md
Branch: phase-4-conversation-engine.
SPEC sections for this phase (read only these from @docs/SPEC.md): VA-05, VA-06, VA-08 (typed input), VA-14, VA-15, and tests T05 to T08, T11 to T14, T16, T19.
Phase 4 only. Tests first. Use a scripted fake LLM for the logic tests (V4.1). V4.4 and V4.5 are zero-tolerance. Tiers, confirmation and controls are code, not prompt.
Restate the tasks and Gate in 3 to 5 lines, then wait for my "go".
Skip [HUMAN] tasks and tell me exactly what I need to do.
I approve calls to the provider APIs this phase's tasks need, using the keys in .env. Don't open or print .env, and keep calls to the minimum the tasks require.
Finish by running every Verification item not marked [HUMAN] (list the [HUMAN] ones as pending for me), writing evidence/phase-4/report.md, and updating docs/STATUS.md.
```

## Phase 5 — Real-time voice pipeline

```
@AGENTS.md @docs/STATUS.md @docs/decisions.md @docs/plan/phase-05.md
Branch: phase-5-voice-pipeline.
SPEC sections for this phase (read only these from @docs/SPEC.md): VA-01, VA-02, VA-03, VA-07, and tests T01 to T04, T10, T20.
Phase 5 only. Read the docs for the installed livekit-agents version before coding (R7). Task 5.7 (speculative generation safety) is critical: investigate, then record an ADR. Stop at 5.10 so I can run my 10-minute conversation.
Restate the tasks and Gate in 3 to 5 lines, then wait for my "go".
Skip [HUMAN] tasks and tell me exactly what I need to do.
I approve calls to the provider APIs this phase's tasks need, using the keys in .env. Don't open or print .env, and keep calls to the minimum the tasks require.
Finish by running every Verification item not marked [HUMAN] (list the [HUMAN] ones as pending for me), writing evidence/phase-5/report.md, and updating docs/STATUS.md.
```

## Phase 6, part 1 — Conversation design (6A to 6C)

```
@AGENTS.md @docs/STATUS.md @docs/decisions.md @docs/plan/phase-06.md
Branch: phase-6-conversation-design.
SPEC sections for this phase (read only these from @docs/SPEC.md): VA-04 and VA-05.
Phase 6 only. Do 6A, 6B and 6C only. 6D and 6E need the Phase 5 gate and my voice sessions, so only run V6.1, V6.3, V6.4, V6.5 and V6.8 now and list the rest as pending. Every prompt version goes in prompts/CHANGELOG.md, and every prompt edit re-runs the safety suite (R14).
Restate the tasks and Gate in 3 to 5 lines, then wait for my "go".
Skip [HUMAN] tasks and tell me exactly what I need to do.
I approve calls to the provider APIs this phase's tasks need, using the keys in .env. Don't open or print .env, and keep calls to the minimum the tasks require.
Finish by running every Verification item not marked [HUMAN] (list the [HUMAN] ones as pending for me), writing evidence/phase-6/report.md, and updating docs/STATUS.md.
```

## Phase 6, part 2 — Human checks and panel (6D to 6E)

```
@AGENTS.md @docs/STATUS.md @docs/decisions.md @docs/plan/phase-06.md
Branch: phase-6-conversation-design.
SPEC sections for this phase (read only these from @docs/SPEC.md): VA-04 and VA-05.
Phase 6 only. The Phase 5 gate must have passed (check STATUS.md). Prepare the pronunciation sheet, dogfooding log template and listening-panel materials, then wait for me to run the sessions. When I give you my tagged breakdown list, fix the top issues and re-run the safety and dialogue suites.
Restate the tasks and Gate in 3 to 5 lines, then wait for my "go".
Skip [HUMAN] tasks and tell me exactly what I need to do.
I approve calls to the provider APIs this phase's tasks need, using the keys in .env. Don't open or print .env, and keep calls to the minimum the tasks require.
Finish by running every Verification item not marked [HUMAN] (list the [HUMAN] ones as pending for me), writing evidence/phase-6/report.md, and updating docs/STATUS.md.
```

## Phase 7 — Interfaces, metrics, real transport, inspector harness

```
@AGENTS.md @docs/STATUS.md @docs/decisions.md @docs/plan/phase-07.md
Branch: phase-7-interfaces-transport.
SPEC sections for this phase (read only these from @docs/SPEC.md): VA-07 to VA-13, VA-15, VA-16 and §7 (what must be measured).
Phase 7 only. Task 7.5 (MockApp participant) is P1 but strongly recommended: do it. Dev control endpoints must bind to localhost and require DEV_MODE=true. Validate every outgoing event against the schema.
Restate the tasks and Gate in 3 to 5 lines, then wait for my "go".
Skip [HUMAN] tasks and tell me exactly what I need to do.
I approve calls to the provider APIs this phase's tasks need, using the keys in .env. Don't open or print .env, and keep calls to the minimum the tasks require.
Finish by running every Verification item not marked [HUMAN] (list the [HUMAN] ones as pending for me), writing evidence/phase-7/report.md, and updating docs/STATUS.md.
```

## Phase 8 — Failure, cancellation and recovery hardening

```
@AGENTS.md @docs/STATUS.md @docs/decisions.md @docs/plan/phase-08.md
Branch: phase-8-failure-hardening.
SPEC sections for this phase (read only these from @docs/SPEC.md): VA-17 (§9), VA-14, and tests T08, T11 to T14, T17, T20.
Phase 8 only. Cover every row of the VA-17 table with an automated or documented manual test. Zero tolerance on duplicate mutations and false success.
Restate the tasks and Gate in 3 to 5 lines, then wait for my "go".
Skip [HUMAN] tasks and tell me exactly what I need to do.
I approve calls to the provider APIs this phase's tasks need, using the keys in .env. Don't open or print .env, and keep calls to the minimum the tasks require.
Finish by running every Verification item not marked [HUMAN] (list the [HUMAN] ones as pending for me), writing evidence/phase-8/report.md, and updating docs/STATUS.md.
```

## Phase 9 — Latency tuning and measurement

```
@AGENTS.md @docs/STATUS.md @docs/decisions.md @docs/plan/phase-09.md
Branch: phase-9-latency.
SPEC sections for this phase (read only these from @docs/SPEC.md): §7 (all targets).
Phase 9 only. Change one lever at a time, in the order listed in task 9.3, and log the config hash on every record. Never delete unfavorable runs. Reports are generated by script from raw logs. Label every number Mode 1 or Mode 2. Stop at 9.1 and 9.6 for my setup and live sessions.
Restate the tasks and Gate in 3 to 5 lines, then wait for my "go".
Skip [HUMAN] tasks and tell me exactly what I need to do.
I approve calls to the provider APIs this phase's tasks need, using the keys in .env. Don't open or print .env, and keep calls to the minimum the tasks require.
Finish by running every Verification item not marked [HUMAN] (list the [HUMAN] ones as pending for me), writing evidence/phase-9/report.md, and updating docs/STATUS.md.
```

## Phase 10 — Acceptance testing and usability

```
@AGENTS.md @docs/STATUS.md @docs/decisions.md @docs/plan/phase-10.md
Branch: phase-10-acceptance.
SPEC sections for this phase (read only these from @docs/SPEC.md): §10 (T01 to T20) and VA-15.
Phase 10 only. Do 10.1 and the automatable runs. Stop for 10.2 and 10.3 (mine). Do 10.4 only after I give you the session results.
Restate the tasks and Gate in 3 to 5 lines, then wait for my "go".
Skip [HUMAN] tasks and tell me exactly what I need to do.
I approve calls to the provider APIs this phase's tasks need, using the keys in .env. Don't open or print .env, and keep calls to the minimum the tasks require.
Finish by running every Verification item not marked [HUMAN] (list the [HUMAN] ones as pending for me), writing evidence/phase-10/report.md, and updating docs/STATUS.md.
```

## Phase 11 — Handover package

```
@AGENTS.md @docs/STATUS.md @docs/decisions.md @docs/plan/phase-11.md
Branch: phase-11-handover.
SPEC sections for this phase (read only these from @docs/SPEC.md): §11 (deliverables) and §12 (out of scope).
Phase 11 only. Do tasks 11.1 to 11.5. Stop at 11.6 and 11.7 (mine). The handover must be self-serve: Zainab should not need a meeting.
Restate the tasks and Gate in 3 to 5 lines, then wait for my "go".
Skip [HUMAN] tasks and tell me exactly what I need to do.
Don't call any provider API in this phase.
Finish by running every Verification item not marked [HUMAN] (list the [HUMAN] ones as pending for me), writing evidence/phase-11/report.md, and updating docs/STATUS.md.
```

---

## Utility prompts

### Resume in a new chat (mid-phase)
```
@AGENTS.md @docs/STATUS.md @docs/decisions.md
Read STATUS.md and the current phase file, then tell me in 3 lines: where we are, what's done, what's next.
Don't change any code until I say "go".
```

### Record a [HUMAN] result
```
@AGENTS.md @docs/STATUS.md @docs/decisions.md
I finished [task id, e.g. 1.2 voice audition]. Results: [paste scores / IDs / observations exactly as they are].
Record them in the right place (decisions.md, evidence/phase-N/, STATUS.md). Don't interpret or invent anything I didn't give you.
Tell me whether this unblocks the next agent task.
```

### Pre-merge audit (before you merge a phase branch)
```
@AGENTS.md @docs/plan/phase-NN.md
Audit this branch's diff against rules R1 to R14 and the phase's Verification table.
For each Verification item: show the command you ran and the result, or say it is not done.
List any rule violations, skipped tests or deviations from the plan. Do not fix anything yet.
```

### Edit the policy prompt (R14)
```
@AGENTS.md @prompts/ @.cursor/rules/prompts.mdc
I want to change the policy prompt: [what and why].
Create the next version file, update CHANGELOG.md, then run the safety suite (V4.4, V4.5) and the dialogue suite and show me the results before we accept it.
```

### Docs contradict the plan (R7)
```
@AGENTS.md @docs/decisions.md
The current docs for [provider / version] say [X], but the plan says [Y].
Follow the docs. Write an ADR in docs/decisions.md (context, decision, evidence, date) and list which plan tasks are affected.
```

### Refresh the graphify graph (after each gate, from Phase 3)
Run in Cursor chat: `/graphify . --update`
(Terminal, once: `graphify cursor install`. See START_HERE.md.)
