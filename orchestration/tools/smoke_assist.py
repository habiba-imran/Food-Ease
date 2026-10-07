"""Smoke assist start/end against a running foodease-session (tokens redacted)."""

from __future__ import annotations

import argparse
import json
import sys

import httpx


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8090")
    parser.add_argument("--show-tokens", action="store_true")
    args = parser.parse_args()

    start = httpx.post(
        f"{args.base}/v1/assist/start",
        json={
            "consent": True,
            "room": "foodease-smoke",
            "user_identity": "smoke-user",
        },
        timeout=30.0,
    )
    start.raise_for_status()
    body = start.json()
    if not args.show_tokens and body.get("user"):
        body["user"] = {**body["user"], "token": "<redacted>"}
    print("assist/start:", json.dumps(body, indent=2))

    end = httpx.post(
        f"{args.base}/v1/assist/end",
        json={
            "room": body["room"],
            "dispatch_id": body.get("dispatch_id"),
            "session_id": body["session_id"],
        },
        timeout=30.0,
    )
    end.raise_for_status()
    print("assist/end:", json.dumps(end.json(), indent=2))
    assert end.json().get("cart_preserved") is True
    print("smoke_assist ok")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"smoke_assist failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
