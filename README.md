# HCI-PROJECT

Sibling folders for Habiba and Zainab (no shared voice/website mix).

The final integrated website now runs from the
[delivery runbook](orchestration/docs/FINAL_RUNBOOK.md). Its implementation checks
and live human/device acceptance are separate; see
[Phase 9 evidence](orchestration/evidence/final/phase-09/report.md).

| Folder | Owner | Contents |
|---|---|---|
| `voice-agent/` | Habiba | LiveKit voice agent, contract, mock app, evidence |
| `orchestration/` | Habiba | **Glue package:** tokens, assist dispatch, demo bring-up, env |
| `zainab-pack/` | Habiba → Zainab | **Frozen** joint kit — start at `zainab-pack/README.md` |
| `website/` | Zainab | Shopping authority, UI and bound browser app/user seats (not JWT secrets) |

Ownership map: [`orchestration/docs/OWNERSHIP.md`](orchestration/docs/OWNERSHIP.md).

```powershell
# From this repository root; print final PowerShell launch commands:
.\orchestration\.venv\Scripts\python.exe orchestration/tools/demo_up.py
# Start the real manual website without providers:
.\orchestration\.venv\Scripts\python.exe orchestration/tools/demo_up.py --mode manual --launch
```
