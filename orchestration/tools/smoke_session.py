"""Smoke the local session API (redacts tokens by default)."""

from __future__ import annotations

import argparse
import json
import sys

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke foodease-session")
    parser.add_argument("--base", default="http://127.0.0.1:8090")
    parser.add_argument("--show-tokens", action="store_true")
    args = parser.parse_args()

    health = httpx.get(f"{args.base}/healthz", timeout=5.0)
    health.raise_for_status()
    print("healthz:", health.json())

    res = httpx.post(
        f"{args.base}/v1/session",
        json={
            "consent": True,
            "room": "foodease-smoke",
            "include_app_token": True,
            "user_identity": "smoke-user",
            "app_identity": "smoke-app",
        },
        timeout=10.0,
    )
    res.raise_for_status()
    body = res.json()
    if not args.show_tokens:
        if body.get("user"):
            body["user"] = {**body["user"], "token": "<redacted>"}
        if body.get("app"):
            body["app"] = {**body["app"], "token": "<redacted>"}
    print(json.dumps(body, indent=2))
    print("smoke ok")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"smoke failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
