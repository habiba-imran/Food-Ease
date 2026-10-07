"""Assist start/end gate tests (fake dispatch — no LiveKit Cloud)."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from foodease_session.app import create_app
from foodease_session.assist import FakeDispatchClient
from foodease_session.config import Settings


def _settings(*, dispatch: bool = True) -> Settings:
    return Settings(
        livekit_url="wss://example.livekit.cloud",
        livekit_api_key="APItestkeyxxxxxxxxxx",
        livekit_api_secret="secretsecretsecretsecret12345678",
        token_ttl_seconds=900,
        host="127.0.0.1",
        port=8090,
        cors_origins=("http://127.0.0.1:8080",),
        rate_limit_requests=1000,
        rate_limit_window_seconds=60,
        livekit_agent_dispatch=dispatch,
        foodease_agent_name="foodease",
    )


def _client(*, dispatch: bool = True) -> tuple[TestClient, FakeDispatchClient]:
    fake = FakeDispatchClient()
    app = create_app(_settings(dispatch=dispatch), dispatch_client=fake)
    return TestClient(app), fake


def test_assist_start_requires_consent() -> None:
    client, fake = _client()
    r = client.post(
        "/v1/assist/start",
        json={"consent": False, "room": "foodease-demo"},
    )
    assert r.status_code == 403
    assert fake.created == []


def test_assist_start_dispatches_and_mints_user() -> None:
    client, fake = _client()
    r = client.post(
        "/v1/assist/start",
        json={
            "consent": True,
            "room": "foodease-demo",
            "user_identity": "harness-user",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["voice_allowed"] is True
    assert body["user"]["role"] == "user"
    assert body["dispatch_enabled"] is True
    assert body["dispatch_id"] == "AD_fake_1"
    assert len(fake.created) == 1
    meta = json.loads(fake.created[0]["metadata"])
    assert meta["foodease.assist"] is True
    assert meta["session_id"] == body["session_id"]


def test_assist_start_dispatch_disabled() -> None:
    client, fake = _client(dispatch=False)
    r = client.post(
        "/v1/assist/start",
        json={"consent": True, "room": "foodease-demo"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["dispatch_id"] is None
    assert body["dispatch_enabled"] is False
    assert body["user"] is not None
    assert fake.created == []


def test_assist_end_preserves_cart_and_deletes_dispatch() -> None:
    client, fake = _client()
    start = client.post(
        "/v1/assist/start",
        json={"consent": True, "room": "foodease-demo"},
    ).json()
    r = client.post(
        "/v1/assist/end",
        json={
            "room": "foodease-demo",
            "dispatch_id": start["dispatch_id"],
            "session_id": start["session_id"],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ended"] is True
    assert body["cart_preserved"] is True
    assert body["dispatch_deleted"] is True
    assert fake.deleted[0]["dispatch_id"] == start["dispatch_id"]


def test_assist_end_idempotent_without_dispatch_id() -> None:
    client, _fake = _client()
    start = client.post(
        "/v1/assist/start",
        json={"consent": True, "room": "foodease-demo"},
    ).json()
    r = client.post(
        "/v1/assist/end",
        json={"room": "foodease-demo", "session_id": start["session_id"]},
    )
    assert r.status_code == 200
    assert r.json()["cart_preserved"] is True
    # Second end still OK
    r2 = client.post(
        "/v1/assist/end",
        json={"room": "foodease-demo", "session_id": start["session_id"]},
    )
    assert r2.status_code == 200
    assert r2.json()["ended"] is True
