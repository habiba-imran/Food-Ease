# Architecture Decision Records

Format per entry: **context → decision → evidence → date**.

Newest entries at the top.

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
