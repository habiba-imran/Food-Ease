# HCI-PROJECT

Sibling folders for Habiba and Zainab (no shared voice/website mix).

| Folder | Owner | Contents |
|---|---|---|
| `voice-agent/` | Habiba | LiveKit voice agent, contract, mock app, evidence |
| `orchestration/` | Habiba | **Glue package:** tokens, assist dispatch, demo bring-up, env |
| `zainab-pack/` | Habiba → Zainab | **Frozen** joint kit — start at `zainab-pack/README.md` |
| *(add later)* `website/` | Zainab | Frontend + app-seat client (not JWT secrets) |

Ownership map: [`orchestration/docs/OWNERSHIP.md`](orchestration/docs/OWNERSHIP.md).

```bash
cd orchestration && uv run python tools/demo_up.py   # print demo stack
cd voice-agent                                       # agent / MockApp work
```
