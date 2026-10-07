"""Print topology bring-up and optionally check session health.

Does not spawn long-running processes (Windows-friendly). Copy-paste the commands.
"""

from __future__ import annotations

import argparse
import json

import httpx

SESSION_DEFAULT = "http://127.0.0.1:8090"
ROOM_DEFAULT = "foodease-demo"


def print_flow(*, session_api: str, room: str) -> None:
    print(
        """
FoodEase room topology (user + app + agent in ONE LiveKit room)
================================================================
Pass criteria:
  1) Participants: user, mock-app (foodease.role=app), agent
  2) foodease.action round-trip works
  3) foodease.context snapshot non-empty

Bring-up order (four terminals):
"""
    )
    print(
        f"""
Terminal A - worker (livekit transport)
  cd voice-agent
  set FOODEASE_APP_TRANSPORT=livekit
  set FOODEASE_AGENT_NAME=foodease
  uv run foodease-worker

Terminal B - session API
  cd orchestration
  uv run foodease-session
  # {session_api}

Terminal C - MockApp as app seat
  cd voice-agent
  set DEV_MODE=true
  uv run python -m mock_app --livekit --room {room}

Terminal D - harness (user seat)
  cd voice-agent
  uv run python harness/token_server.py
  # Open http://127.0.0.1:8080 -> Start assistance

Docs: orchestration/docs/TOPOLOGY.md
"""
    )


def check_session(session_api: str) -> int:
    base = session_api.rstrip("/")
    try:
        health = httpx.get(f"{base}/healthz", timeout=5.0)
        health.raise_for_status()
        print("PASS healthz:", health.json())
    except Exception as exc:  # noqa: BLE001
        print("FAIL healthz:", exc)
        return 1

    try:
        # Mint-only probe: app token for topology room (no Cloud round-trip required)
        tok = httpx.post(
            f"{base}/v1/token",
            json={"role": "app", "room": ROOM_DEFAULT, "identity": "topology-probe-app"},
            timeout=10.0,
        )
        tok.raise_for_status()
        body = tok.json()
        redacted = {
            **body,
            "participant": {
                **body["participant"],
                "token": "<redacted>",
            },
        }
        print("PASS /v1/token role=app:", json.dumps(redacted, indent=2))
    except Exception as exc:  # noqa: BLE001
        print("FAIL /v1/token:", exc)
        return 1

    print(
        "NOTE: Full room participant check needs LiveKit Cloud + worker + MockApp --livekit.\n"
        "After Start assistance, verify three seats in LiveKit dashboard / agent logs."
    )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="FoodEase topology helper")
    parser.add_argument("--session-api", default=SESSION_DEFAULT)
    parser.add_argument("--room", default=ROOM_DEFAULT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Hit session healthz + mint app token (stack partially up)",
    )
    args = parser.parse_args()
    print_flow(session_api=args.session_api, room=args.room)
    if args.check:
        raise SystemExit(check_session(args.session_api))


if __name__ == "__main__":
    main()
