# Consent / dispatch gate — implementation plan

## Goal

Opt-in / opt-out voice assistance (WEB-01 / VA-01) without Zainab’s UI:

1. **Start assistance** → mint mic user JWT **and** dispatch the agent (greeting + idle allowed).
2. **End assistance** → stop prompts; **cart preserved** in the app.
3. Manual browse works with **no** agent.

## Phases

| Phase | Status | Deliverable |
|---|---|---|
| 0 Spec | done | `ASSIST_LIFECYCLE.md` + frozen API |
| 1 Start | done | `POST /v1/assist/start` + CreateAgentDispatch |
| 2 End | done | `POST /v1/assist/end` + DeleteAgentDispatch |
| 3 Worker | done | Shutdown disables idle; agent_name=foodease |
| 4 Harness | done | Start / End assistance buttons |
| 5 Docs | done | API.md + zainab-pack SESSION_API |
| 6 Harden | done | Flags, smoke_assist, tests |

Critical path: 0 → 1 → 2 → 3 → 4.
