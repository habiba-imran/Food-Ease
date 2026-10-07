# Tiny orchestration package — implementation plan

## Goal

Treat `orchestration/` as the **official sibling glue package** for the joint Habiba ↔ Zainab phase:

| Lives here | Does **not** live here |
|---|---|
| LiveKit JWT mint (`user` / `app`) | Cart / menu / checkout |
| Consent + agent dispatch | STT / TTS / LLM / dialogue |
| Demo stack bring-up + env example | Website UI / routes |
| Topology + integration evidence pointers | Zainab’s future `website/` tree |

Keeps secrets and session policy out of the browser **and** out of `voice-agent`’s brain.

## Already present (reuse)

- `foodease-session` API (`/v1/session`, `/v1/token`, `/v1/assist/*`)
- `docs/API.md`, `ASSIST_LIFECYCLE.md`, `BRINGUP.md`, `TOPOLOGY.md`
- `tools/topology_up.py`, smoke scripts, `.env.example`

## Remaining for “package” ownership

| # | Deliverable |
|---|---|
| 0 | This plan + `OWNERSHIP.md` |
| 1 | `tools/demo_up.py` — one-shot “bring up demo stack” printout + optional checks |
| 2 | README / `.env.example` framed as the package (not agent, not website) |
| 3 | Root + zainab-pack links to ownership |

## Out of scope

- Spawning long-running processes (Windows-friendly: print commands)
- Moving MockApp or worker into this folder
- Building Zainab’s website
