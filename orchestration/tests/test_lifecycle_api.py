"""Bound lifecycle API with the actual Phase 2 shopping store, fake Cloud."""

import base64
import json
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient
from foodease_website.catalog import load_catalog
from foodease_website.sessions import SessionError, SessionStore

from foodease_session.app import create_app
from foodease_session.lifecycle import AssistanceService, LifecycleError
from test_lifecycle import Cloud, settings


def fixture():
    root = Path(__file__).resolve().parents[2]
    store = SessionStore(load_catalog(root / "zainab-pack/catalog-seed.json"))
    owner = store.new_owner()
    sid = store.create(owner).session_id

    class Authority:
        async def check(self, supplied_owner, supplied_sid):
            try:
                return store.context(supplied_owner, supplied_sid)
            except SessionError as exc:
                raise LifecycleError(exc.status, exc.code) from None

    cloud = Cloud()
    cfg = settings()
    service = AssistanceService(cfg, Authority(), cloud)
    client = TestClient(create_app(cfg, dispatch_client=cloud, assistance_service=service))
    client.cookies.set("foodease_owner", owner)
    client.headers["X-FoodEase-Session"] = sid
    return client, (store, owner, sid), service, cloud


def test_actual_shopping_ownership_tokens_and_manual_cart_survive_end():
    client, (store, owner, sid), service, cloud = fixture()
    store.submit(
        owner,
        sid,
        {
            "schema_version": "2.0",
            "session_id": sid,
            "event_id": "manual-add",
            "turn_id": "manual",
            "timestamp": "2026-10-17T12:00:00Z",
            "context_revision": 1,
            "type": "agent.action_request",
            "payload": {
                "action_id": "add",
                "operation": "cart.add_item",
                "arguments": {"item_id": "wrap-hot-chicken"},
            },
        },
    )
    before = store.context(owner, sid)
    assert before["cart"]["total"] == 900
    response = client.post("/v2/assist/start", json={"request_id": "request", "consent": True})
    assert response.status_code == 200, response.text
    prepared = response.json()
    assert prepared["session_id"] == before["session_id"] and not cloud.created
    assert "worker_proof" not in response.text
    for role, token in prepared["tokens"].items():
        encoded = token["token"].split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        assert claims["attributes"]["foodease.session"] == before["session_id"]
        assert claims["attributes"]["foodease.generation"] == prepared["generation"]
        assert claims["video"]["canUpdateOwnMetadata"] is False
        assert claims["video"]["canPublish"] is (role == "user")
    intruder = TestClient(client.app)
    intruder.cookies.set("foodease_owner", "intruder")
    intruder.headers.update(client.headers)
    assert intruder.post("/v2/assist/end", json={"request_id": "request"}).status_code == 403
    assert (
        client.post("/v2/assist/end", json={"request_id": "request", "room": "forged"}).status_code
        == 422
    )
    ended = client.post("/v2/assist/end", json={"request_id": "request"})
    assert ended.json()["state"] == "ended"
    assert store.context(owner, sid) == before
    assert service.current[before["session_id"]].cancelled


def test_legacy_endpoints_disabled_and_cannot_mint_integrated_room_even_in_dev():
    client, _, _, _ = fixture()
    assert client.post("/v1/session", json={"consent": True}).status_code == 410
    cfg = replace(settings(), enable_legacy_api=True)
    legacy = TestClient(create_app(cfg))
    response = legacy.post("/v1/token", json={"role": "app", "room": "foodease-v2-protected"})
    assert response.status_code == 400


def test_v2_strict_inputs_origins_and_refresh_identity():
    client, _, _, _ = fixture()
    for body in (
        {"request_id": "r", "consent": "true"},
        {"request_id": "r", "consent": True, "app_identity": "fake"},
    ):
        assert client.post("/v2/assist/start", json=body).status_code == 422
    assert (
        client.post(
            "/v2/assist/start",
            json={"request_id": "r", "consent": True},
            headers={"Origin": "https://foreign.example"},
        ).status_code
        == 403
    )
    prepared = client.post("/v2/session", json={"request_id": "r", "consent": True}).json()
    body = {"request_id": "r", "generation": prepared["generation"], "consent": True}
    refreshed = client.post("/v2/token", json=body).json()
    assert refreshed["generation"] == prepared["generation"]
    assert refreshed["binding"] == prepared["binding"]
    body["generation"] = "forged"
    assert client.post("/v2/token", json=body).status_code == 409
