from dataclasses import replace

from fastapi.testclient import TestClient

from foodease_session.production import create_backend
from test_lifecycle import Cloud, settings


def test_same_origin_gateway_updates_the_real_backend_cart_and_binds_tokens():
    from contextlib import asynccontextmanager
    from datetime import UTC, datetime
    from uuid import uuid4

    import httpx
    from fastapi import FastAPI
    from foodease_website.backend_proxy import BackendProxy

    backend = create_backend(
        settings=replace(settings(), cors_origins=("https://frontend.test",)), cloud=Cloud()
    )

    @asynccontextmanager
    async def lifespan(app):
        async with backend.router.lifespan_context(backend):
            yield

    gateway = FastAPI(lifespan=lifespan)
    gateway.add_middleware(
        BackendProxy, backend_url="https://backend.test", transport=httpx.ASGITransport(app=backend)
    )
    with TestClient(gateway, base_url="https://frontend.test") as client:
        sid = client.post("/api/v2/app/sessions", json={}).json()["session_id"]
        headers = {"X-FoodEase-Session": sid, "Origin": "https://frontend.test"}
        snapshot = client.get("/api/v2/app/context", headers=headers).json()
        response = client.post(
            "/api/v2/app/action",
            headers=headers,
            json={
                "schema_version": "2.0",
                "session_id": sid,
                "event_id": uuid4().hex,
                "turn_id": "manual",
                "type": "agent.action_request",
                "timestamp": datetime.now(UTC).isoformat(),
                "context_revision": snapshot["revision"],
                "payload": {
                    "action_id": "add-once",
                    "operation": "cart.add_item",
                    "arguments": {"item_id": "drink-cola", "quantity": 1},
                },
            },
        )
        assert response.status_code == 200 and response.json()["payload"]["status"] == "success"
        cart = client.get("/api/v2/app/context", headers=headers).json()["cart"]
        assert cart["total"] == 150 and cart["lines"][0]["quantity"] == 1
        prepared = client.post(
            "/assist/v2/assist/start",
            headers=headers,
            json={"request_id": "gateway-voice", "consent": True},
        )
        assert prepared.status_code == 200 and prepared.json()["binding"]["session_id"] == sid


def test_combined_backend_binds_tokens_to_the_actual_cart_and_owner():
    cfg = replace(settings(), cors_origins=("https://food-ease-seven.vercel.app",))
    with TestClient(
        create_backend(settings=cfg, cloud=Cloud()), base_url="https://backend.onrender.com"
    ) as client:
        created = client.post("/api/v2/app/sessions", json={})
        assert created.status_code == 201
        sid = created.json()["session_id"]
        headers = {"X-FoodEase-Session": sid, "Origin": "https://food-ease-seven.vercel.app"}
        prepared = client.post(
            "/assist/v2/assist/start", json={"request_id": "one", "consent": True}, headers=headers
        )
        assert prepared.status_code == 200
        assert prepared.json()["binding"]["session_id"] == sid
        assert "worker_proof" not in prepared.text
        denied = client.post(
            "/assist/v2/assist/start",
            json={"request_id": "two", "consent": True},
            headers={**headers, "Cookie": "foodease_owner=foreign"},
        )
        assert denied.status_code in {401, 403, 410}
        assert client.get("/healthz").json()["session_storage"] == "single_process"
