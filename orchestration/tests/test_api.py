"""API tests with injected settings (no LiveKit Cloud)."""

from __future__ import annotations

import base64
import json

from fastapi.testclient import TestClient

from foodease_session.app import create_app
from foodease_session.config import Settings


def _settings() -> Settings:
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
        livekit_agent_dispatch=False,
        foodease_agent_name="foodease",
    )


def _client() -> TestClient:
    return TestClient(create_app(_settings()))


def _payload(jwt: str) -> dict:
    part = jwt.split(".")[1]
    pad = "=" * (-len(part) % 4)
    return json.loads(base64.urlsafe_b64decode(part + pad))


def test_healthz() -> None:
    r = _client().get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_session_consent_true_returns_user_and_app() -> None:
    r = _client().post(
        "/v1/session",
        json={
            "consent": True,
            "room": "foodease-demo",
            "include_app_token": True,
            "user_identity": "harness-user",
            "app_identity": "mock-app",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["voice_allowed"] is True
    assert body["user"]["role"] == "user"
    assert body["app"]["role"] == "app"
    assert body["room"] == "foodease-demo"
    assert _payload(body["app"]["token"])["attributes"]["foodease.role"] == "app"


def test_session_consent_false_omits_user_token() -> None:
    r = _client().post(
        "/v1/session",
        json={"consent": False, "room": "foodease-demo", "include_app_token": True},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["voice_allowed"] is False
    assert body["user"] is None
    assert body["app"]["role"] == "app"


def test_token_user_requires_consent() -> None:
    r = _client().post(
        "/v1/token",
        json={"role": "user", "room": "foodease-demo", "consent": False},
    )
    assert r.status_code == 403


def test_token_app_without_consent_ok() -> None:
    r = _client().post(
        "/v1/token",
        json={"role": "app", "room": "foodease-demo", "identity": "mock-app"},
    )
    assert r.status_code == 200
    assert r.json()["participant"]["role"] == "app"


def test_bad_room_rejected() -> None:
    r = _client().post(
        "/v1/session",
        json={"consent": True, "room": "not-allowed"},
    )
    assert r.status_code == 400
