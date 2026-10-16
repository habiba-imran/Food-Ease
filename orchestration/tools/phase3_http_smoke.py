"""Two real localhost HTTP services; LiveKit participants/dispatch are explicit fakes.

Use the orchestration interpreter. No .env or paid providers. Starts and stops
only disposable test servers; refuses occupied ports. Does not print JWTs/proofs.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import threading
import time
from pathlib import Path

import httpx
import uvicorn
from phase0_baseline import offline_environment

from foodease_session.app import create_app
from foodease_session.config import Settings
from foodease_session.lifecycle import AssistanceService, HttpShoppingAuthority

ROOT = Path(__file__).resolve().parents[2]


class RehearsalCloud:
    """Fake transport state only; no application/cart implementation."""

    def __init__(self):
        self.people, self.dispatches, self.created, self.deleted = [], [], [], []
        self.fail_delete = False

    async def participants(self, room):
        return self.people

    async def create_dispatch(self, **kwargs):
        self.created.append(kwargs)
        self.dispatches.append({"id": "fake-dispatch", "metadata": kwargs["metadata"]})
        return "fake-dispatch"

    async def list_dispatches(self, room):
        return self.dispatches

    async def delete_dispatch(self, *, dispatch_id, room):
        if self.fail_delete:
            raise RuntimeError("simulated transient failure")
        self.deleted.append(dispatch_id)
        self.dispatches = []

    async def delete_room(self, room):
        if self.fail_delete:
            raise RuntimeError("simulated transient failure")
        self.people = []


def wait_ready(base: str) -> None:
    with httpx.Client(trust_env=False, timeout=0.5) as client:
        for _ in range(100):
            try:
                if client.get(base + "/healthz").status_code == 200:
                    return
            except httpx.TransportError:
                pass
            time.sleep(0.1)
    raise RuntimeError("Disposable HTTP startup timed out")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    for port in (18080, 18090):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                raise RuntimeError(f"Refusing occupied disposable port {port}")
        except OSError:
            pass
    cfg = Settings(
        "wss://example.livekit.cloud",
        "test-key",
        "offline-signing-secret-1234567890",
        900,
        "127.0.0.1",
        18090,
        ("http://127.0.0.1:18080",),
        1000,
        60,
        True,
        "foodease",
        website_base_url="http://127.0.0.1:18080",
    )
    cloud = RehearsalCloud()
    service = AssistanceService(cfg, HttpShoppingAuthority(cfg.website_base_url), cloud)
    app = create_app(cfg, dispatch_client=cloud, assistance_service=service)
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=18090, log_level="error", access_log=False)
    )
    thread = threading.Thread(target=server.run, daemon=True)
    website = subprocess.Popen(
        [
            str(ROOT / "website/.venv/Scripts/python.exe"),
            "-m",
            "uvicorn",
            "foodease_website.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            "18080",
            "--log-level",
            "error",
            "--no-access-log",
        ],
        cwd=ROOT / "website",
        env=offline_environment(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    trace = []
    try:
        wait_ready(cfg.website_base_url)
        thread.start()
        wait_ready("http://127.0.0.1:18090")
        with httpx.Client(base_url=cfg.website_base_url, trust_env=False) as shopper:
            sid = shopper.post("/api/v2/app/sessions", json={}).json()["session_id"]
            shopper.headers["X-FoodEase-Session"] = sid
            owner = shopper.cookies.get("foodease_owner")
            result = shopper.post(
                "/api/app/action",
                json={
                    "action_id": "manual-add",
                    "operation": "cart.add_item",
                    "arguments": {"item_id": "wrap-hot-chicken"},
                    "context_revision": 1,
                },
            )
            assert result.json()["status"] == "success"
            before = shopper.get("/api/v2/app/context").json()
            assert before["cart"]["total"] == 900
            with httpx.Client(
                base_url="http://127.0.0.1:18090",
                trust_env=False,
                cookies={"foodease_owner": owner},
                headers={"X-FoodEase-Session": sid},
            ) as client:
                body = {"request_id": "rehearsal", "consent": True}
                prepared_response = client.post("/v2/assist/start", json=body)
                prepared_response.raise_for_status()
                prepared = prepared_response.json()
                again = client.post("/v2/assist/start", json=body).json()
                assert again["generation"] == prepared["generation"] and not cloud.created
                trace.append({"state": prepared["state"], "dispatch_count": len(cloud.created)})

                def seats(roles):
                    cloud.people = [
                        {
                            "identity": prepared["binding"][f"{role}_identity"],
                            "attributes": {
                                "foodease.role": role,
                                "foodease.session": sid,
                                "foodease.generation": prepared["generation"],
                            },
                        }
                        for role in roles
                    ]

                seats(("app", "user"))
                ready = client.post(
                    "/v2/assist/ready",
                    json={
                        "request_id": "rehearsal",
                        "generation": prepared["generation"],
                        "context_revision": before["revision"],
                        "app_ready": True,
                        "playback_ready": True,
                        "media_ready": True,
                    },
                ).json()
                assert ready["state"] == "waiting_worker" and not ready["greeting_allowed"]
                trace.append({"state": ready["state"], "greeting_allowed": False})
                seats(("app", "user", "agent"))
                proof = json.loads(cloud.created[0]["metadata"])["worker_proof"]
                active = client.post(
                    "/v2/assist/worker-ready",
                    headers={"X-FoodEase-Worker-Proof": proof},
                    json={
                        "session_id": sid,
                        "generation": prepared["generation"],
                        "context_revision": before["revision"],
                        "runtime_ready": True,
                    },
                ).json()
                assert active["greeting_allowed"] and active["state"] == "active"
                trace.append(
                    {"state": active["state"], "runtime": "FAKE readiness acknowledgement"}
                )
                cloud.fail_delete = True
                pending = client.post("/v2/assist/end", json={"request_id": "rehearsal"}).json()
                assert pending["state"] == "cleanup_pending" and not pending["dispatch_deleted"]
                assert (
                    client.post(
                        "/v2/assist/start", json={"request_id": "second", "consent": True}
                    ).status_code
                    == 409
                )
                trace.append({"state": pending["state"], "dispatch_deleted": False})
                cloud.fail_delete = False
                ended = client.post("/v2/assist/end", json={"request_id": "rehearsal"}).json()
                assert ended["state"] == "ended" and ended["room_deleted"]
                assert cloud.deleted == ["fake-dispatch"] and len(cloud.created) == 1
                trace.append(
                    {"state": ended["state"], "dispatch_deleted": True, "room_deleted": True}
                )
                assert shopper.get("/api/v2/app/context").json() == before
                assert client.post("/v1/session", json={"consent": True}).status_code == 410
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(
                {
                    "website_http": "real localhost",
                    "lifecycle_http": "real localhost",
                    "livekit": "fake",
                    "audio": "not exercised",
                    "cart_total_before_and_after": 900,
                    "trace": trace,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(
            "PASS two real localhost HTTP services; fake LiveKit; "
            "cart preserved; failed cleanup reconciled"
        )
    finally:
        server.should_exit = True
        if thread.is_alive():
            thread.join(timeout=15)
        website.terminate()
        website.wait(timeout=10)


if __name__ == "__main__":
    main()
