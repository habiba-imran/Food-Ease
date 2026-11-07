"""Vercel gateway keeps the existing owner/session contract on one browser origin."""

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from foodease_website.backend_proxy import BackendProxy


def gateway(handler):
    app = FastAPI()
    app.add_middleware(
        BackendProxy,
        backend_url="https://backend.onrender.com",
        transport=httpx.MockTransport(handler),
    )
    return TestClient(app, base_url="https://food-ease-seven.vercel.app")


def test_proxy_preserves_owner_and_action_identity_without_forwarding_other_cookies():
    requests = []

    def backend(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={"result": "verified"},
            headers={
                "set-cookie": "foodease_owner=owner; HttpOnly; Secure; SameSite=strict",
            },
        )

    with gateway(backend) as client:
        response = client.post(
            "/api/v2/app/action",
            content=b'{"payload":{"action_id":"one"}}',
            headers={
                "origin": str(client.base_url).rstrip("/"),
                "cookie": "foodease_owner=owner; vercel_auth=private",
                "X-FoodEase-Session": "shop",
                "X-Forwarded-Host": "evil.test",
            },
        )
    assert response.status_code == 200
    assert requests[0].content == b'{"payload":{"action_id":"one"}}'
    assert requests[0].headers["cookie"] == "foodease_owner=owner"
    assert requests[0].headers["origin"] == "https://backend.onrender.com"
    assert requests[0].headers["X-FoodEase-Session"] == "shop"
    assert "x-forwarded-host" not in requests[0].headers
    assert response.headers["cache-control"] == "no-store"
    assert "HttpOnly" in response.headers["set-cookie"]


def test_proxy_rejects_cross_origin_before_upstream_and_never_retries_a_write():
    requests = []

    def backend(request):
        requests.append(request)
        raise httpx.ConnectError("not reachable")

    with gateway(backend) as client:
        denied = client.post(
            "/assist/v2/assist/start", json={}, headers={"origin": "https://evil.test"}
        )
        assert denied.status_code == 403 and not requests
        failed = client.post("/api/v2/app/action", json={})
        assert failed.status_code == 503 and len(requests) == 1
        assert failed.json()["error"] == "backend_unavailable_check_cart_before_retry"


def test_session_proxy_keeps_the_validated_public_origin_for_cors_and_does_not_follow_redirects():
    def backend(request):
        assert request.headers["origin"] == "https://food-ease-seven.vercel.app"
        return httpx.Response(302, headers={"location": "https://elsewhere.test"})

    with gateway(backend) as client:
        response = client.post(
            "/assist/v2/assist/start",
            json={},
            headers={"origin": "https://food-ease-seven.vercel.app"},
        )
    assert response.status_code == 502


def test_proxy_limits_bodies_and_does_not_proxy_unknown_paths():
    with gateway(lambda _: httpx.Response(200)) as client:
        assert client.post("/api/v2/app/action", content=b"x" * 15000).status_code == 413
        assert client.get("/not-an-api").status_code == 404
