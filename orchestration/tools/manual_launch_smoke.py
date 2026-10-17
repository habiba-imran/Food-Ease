"""Exercise the actual manual launch/HTTP/shutdown path without provider access."""

from __future__ import annotations

import argparse
import json
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import httpx

from foodease_session.bringup import StackPlan, occupied_ports, run_stack

ROOT = Path(__file__).resolve().parents[2]


def smoke() -> dict:
    # Reserve distinct temporary ports together, then let launch refuse any race.
    sockets = [socket.socket() for _ in range(3)]
    try:
        for probe in sockets:
            probe.bind(("127.0.0.1", 0))
        ports = [probe.getsockname()[1] for probe in sockets]
    finally:
        for probe in sockets:
            probe.close()
    plan = StackPlan(ROOT, "manual", *ports)
    with ThreadPoolExecutor(max_workers=1) as pool:
        launched = pool.submit(run_stack, plan, duration=3)
        with httpx.Client(timeout=2, trust_env=False) as client:
            deadline = time.monotonic() + 60
            while True:
                try:
                    if client.get(f"{plan.session_url}/healthz").status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                if launched.done() or time.monotonic() > deadline:
                    launched.result(timeout=5)
                    raise RuntimeError("Owned manual stack did not become healthy")
                time.sleep(0.1)
            created = client.post(f"{plan.website_url}/api/v2/app/sessions", json={})
            created.raise_for_status()
            sid = created.json()["session_id"]
            headers = {"X-FoodEase-Session": sid}
            context = client.get(f"{plan.website_url}/api/v2/app/context", headers=headers).json()
            action = {
                "schema_version": "2.0",
                "session_id": sid,
                "turn_id": "manual-smoke",
                "event_id": uuid4().hex,
                "timestamp": "2026-10-17T12:00:00Z",
                "context_revision": context["revision"],
                "type": "agent.action_request",
                "payload": {
                    "action_id": uuid4().hex,
                    "operation": "cart.add_item",
                    "arguments": {"item_id": "wrap-hot-chicken", "quantity": 1},
                },
            }
            response = client.post(
                f"{plan.website_url}/api/v2/app/action", headers=headers, json=action
            )
            response.raise_for_status()
            assert response.json()["payload"]["status"] == "success"
            assert response.json()["payload"]["verified_state"]["lines"][0]["quantity"] == 1
            check = client.get(f"{plan.website_url}/api/v2/app/context", headers=headers)
            assert check.json()["cart"]["total"] == 900
        assert launched.result(timeout=40) == 0
    remaining = occupied_ports(ports[:2])
    if remaining:
        raise RuntimeError("An owned HTTP process did not release its port")
    return {
        "mode": "offline_manual",
        "services": ["website", "session"],
        "real_http_authority": True,
        "cart_quantity": 1,
        "cart_total_pkr": 900,
        "shutdown_ports_released": True,
        "worker_launched": False,
        "providers": "none",
        "live_acceptance": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    root = ROOT / "orchestration/evidence/final/phase-09"
    if not output.is_relative_to(root) or output == root:
        parser.error("Use a run directory beneath Phase 9 evidence")
    output.mkdir(parents=True, exist_ok=True)
    result = smoke()
    (output / "manual-launch.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
