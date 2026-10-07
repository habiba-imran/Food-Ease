"""Bring-up helper for the FoodEase demo stack (orchestration glue only).

Prints copy-paste commands for the full local stack. Does not spawn
long-running processes (Windows-friendly).

  uv run python tools/demo_up.py
  uv run python tools/demo_up.py --check   # needs foodease-session running
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import httpx

SESSION_DEFAULT = "http://127.0.0.1:8090"
ROOM_DEFAULT = "foodease-demo"
ROOT = Path(__file__).resolve().parents[1]
ENV_EXAMPLE = ROOT / ".env.example"
ENV_FILE = ROOT / ".env"


def print_stack(*, session_api: str, room: str) -> None:
    env_hint = "OK" if ENV_FILE.is_file() else f"missing - copy {ENV_EXAMPLE.name}"
    print(
        f"""
FoodEase demo stack (orchestration-owned glue)
==============================================
Env: orchestration/.env [{env_hint}]
Ownership: docs/OWNERSHIP.md  (tokens/dispatch here; cart in app; brain in voice-agent)

Terminals (start in order):
"""
    )
    print(
        f"""
1) Session API  (this package)
   cd orchestration
   uv sync
   # cp .env.example .env   # once - fill LIVEKIT_*
   uv run foodease-session
   # {session_api}  /docs

2) Voice worker  (sibling voice-agent/)
   cd voice-agent
   uv run foodease-worker

3) MockApp stand-in website  (optional DEV)
   cd voice-agent
   set DEV_MODE=true
   uv run python -m mock_app
   # GUI navigate / cart on :8765 - survives End assistance

4) Harness user seat
   cd voice-agent
   uv run python harness/token_server.py
   # http://127.0.0.1:8080 -> Start assistance

Smoke (with session up):
   uv run python tools/smoke_session.py
   uv run python tools/smoke_assist.py

3-seat LiveKit topology (app + user + agent):
   uv run python tools/topology_up.py
   uv run python tools/topology_up.py --check

Integration checklist (MockApp today):
   cd ../voice-agent && uv run python tools/run_integration.py

Room default: {room}
Docs: docs/BRINGUP.md | docs/TOPOLOGY.md | docs/API.md
"""
    )


def check_stack(session_api: str) -> int:
    base = session_api.rstrip("/")
    try:
        health = httpx.get(f"{base}/healthz", timeout=5.0)
        health.raise_for_status()
        print("PASS healthz:", health.json())
    except Exception as exc:  # noqa: BLE001
        print("FAIL healthz:", exc)
        print("Start terminal 1 first: uv run foodease-session")
        return 1

    try:
        sess = httpx.post(
            f"{base}/v1/session",
            json={"consent": True, "include_app_token": True, "room": ROOM_DEFAULT},
            timeout=10.0,
        )
        sess.raise_for_status()
        body = sess.json()
        redacted = {
            k: v
            for k, v in body.items()
            if k not in {"user", "app"}
        }
        if "user" in body:
            redacted["user"] = {
                **{k: v for k, v in body["user"].items() if k != "token"},
                "token": "<redacted>",
            }
        if body.get("app"):
            redacted["app"] = {
                **{k: v for k, v in body["app"].items() if k != "token"},
                "token": "<redacted>",
            }
        print("PASS /v1/session:", json.dumps(redacted, indent=2))
    except Exception as exc:  # noqa: BLE001
        print("FAIL /v1/session:", exc)
        return 1

    print("Stack glue OK. Start worker + MockApp + harness for a full demo.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="FoodEase demo stack bring-up")
    parser.add_argument("--session-api", default=SESSION_DEFAULT)
    parser.add_argument("--room", default=ROOM_DEFAULT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Hit healthz + /v1/session (session API must be running)",
    )
    args = parser.parse_args()
    print_stack(session_api=args.session_api, room=args.room)
    if args.check:
        raise SystemExit(check_stack(args.session_api))


if __name__ == "__main__":
    main()
