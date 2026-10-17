"""Print or launch the final real-website stack; manual mode is the safe default."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from foodease_session.bringup import StackPlan, check_stack, powershell_commands, run_stack

ROOT = Path(__file__).resolve().parents[2]


def print_stack(*, session_api: str = "http://127.0.0.1:8090", room: str = "") -> None:
    print(powershell_commands(StackPlan(ROOT)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["manual", "live"], default="manual")
    parser.add_argument(
        "--integrated",
        action="store_true",
        help="Compatibility alias; final path is always integrated",
    )
    parser.add_argument("--website-port", type=int, default=8080)
    parser.add_argument("--session-port", type=int, default=8090)
    parser.add_argument("--worker-port", type=int, default=8081)
    parser.add_argument(
        "--launch", action="store_true", help="Own foreground processes until Ctrl+C"
    )
    parser.add_argument(
        "--allow-live", action="store_true", help="Explicit Cloud/provider cost opt-in"
    )
    parser.add_argument(
        "--check", action="store_true", help="Read health only; no token or dispatch"
    )
    parser.add_argument("--duration", type=float, help="Bound local smoke lifetime in seconds")
    parser.add_argument(
        "--startup-timeout", type=float, default=180,
        help="Per-service cold-start deadline in seconds (default 180, maximum 600)",
    )
    args = parser.parse_args()
    try:
        if args.duration is not None and (
            not math.isfinite(args.duration) or args.duration <= 0 or args.duration > 3600
        ):
            raise ValueError("Duration must be between 0 and 3600 seconds")
        plan = StackPlan(ROOT, args.mode, args.website_port, args.session_port, args.worker_port)
        if args.launch and args.check:
            raise ValueError("Choose --launch or --check")
        if args.launch:
            raise SystemExit(
                run_stack(
                    plan,
                    allow_live=args.allow_live,
                    duration=args.duration,
                    startup_timeout=args.startup_timeout,
                )
            )
        if args.check:
            checks = check_stack(plan)
            print(json.dumps({"health_only": True, "services": checks, "live_acceptance": False}))
            raise SystemExit(0 if all(checks.values()) else 1)
        print(powershell_commands(plan))
    except (ValueError, RuntimeError) as error:
        parser.exit(2, f"{error}\n")


if __name__ == "__main__":
    main()
