"""MockApp entry — in-process (default) or LiveKit topology rehearsal."""

from __future__ import annotations

import argparse
import asyncio
import os
import time

from dotenv import load_dotenv

from foodease_agent.adapters.transport import InProcessRoom
from mock_app.participant import MockAppParticipant, start_dev_control_server


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="FoodEase MockApp (website stand-in)")
    parser.add_argument(
        "--livekit",
        action="store_true",
        default=os.environ.get("MOCK_APP_LIVEKIT", "").lower() in {"1", "true", "yes", "on"},
        help="Join a real LiveKit room as foodease.role=app",
    )
    parser.add_argument(
        "--room",
        default=os.environ.get("FOODEASE_ROOM", "foodease-demo"),
        help="LiveKit room name (livekit mode)",
    )
    args = parser.parse_args()

    if os.environ.get("DEV_MODE", "false").lower() not in {"1", "true", "yes", "on"}:
        raise SystemExit("Refusing to start MockApp control: set DEV_MODE=true")

    if args.livekit:
        from mock_app.livekit_main import main_livekit

        main_livekit(args.room)
        return

    room = InProcessRoom()
    room.register_participant("agent-worker")
    mock = MockAppParticipant(room)
    asyncio.run(mock.start())
    start_dev_control_server(mock)
    print("MockApp running (in-process room). Ctrl+C to stop.")
    print("Tip: use --livekit for topology rehearsal with foodease-worker.")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("bye")


if __name__ == "__main__":
    main()
