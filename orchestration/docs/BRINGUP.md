# Local bring-up (assist gate + Habiba demo)

Fill `orchestration/.env` or `voice-agent/.env`.  
One-shot command list: `uv run python tools/demo_up.py`  
Boundaries: [`OWNERSHIP.md`](OWNERSHIP.md).

## Terminal A — voice worker

```bash
cd voice-agent
# Optional: FOODEASE_AGENT_NAME=foodease  (must match orchestration)
uv run foodease-worker
```

## Terminal B — MockApp (optional, DEV)

```bash
cd voice-agent
# DEV_MODE=true in .env
uv run python -m mock_app
# GUI navigate / cart on :8765 — survives End assistance
```

## Terminal C — session API

```bash
cd orchestration
uv run foodease-session
# http://127.0.0.1:8090
```

## Terminal D — harness

```bash
cd voice-agent
uv run python harness/token_server.py
# http://127.0.0.1:8080
```

1. Use **GUI navigate** anytime (manual path, no agent).
2. **Start assistance** → `POST /v1/assist/start` → mic + agent greeting.
3. **End assistance** → stops prompts; MockApp cart unchanged.

## Topology rehearsal (livekit) — three seats, one room

See [`TOPOLOGY.md`](TOPOLOGY.md). Quick helper:

```bash
cd orchestration
uv run python tools/topology_up.py
uv run python tools/topology_up.py --check   # needs foodease-session running
```

Worker must use `FOODEASE_APP_TRANSPORT=livekit`. MockApp must use `--livekit`.
Harness **Start assistance** joins the same `foodease-demo` room.
