"""Unit tests for JWT minting (no LiveKit Cloud)."""

from __future__ import annotations

import base64
import json
import time

import pytest

from foodease_session.mint import MintError, Role, mint_token


def _decode_payload(jwt: str) -> dict:
    parts = jwt.split(".")
    assert len(parts) == 3
    pad = "=" * (-len(parts[1]) % 4)
    raw = base64.urlsafe_b64decode(parts[1] + pad)
    return json.loads(raw)


def test_user_token_has_user_role_and_publish() -> None:
    jwt = mint_token(
        api_key="APItestkeyxxxxxxxxxx",
        api_secret="secretsecretsecretsecret12345678",
        role=Role.USER,
        room="foodease-demo",
        identity="harness-user",
        ttl_seconds=900,
    )
    claims = _decode_payload(jwt)
    assert claims["sub"] == "harness-user"
    assert claims.get("attributes", {}).get("foodease.role") == "user"
    video = claims["video"]
    assert video["room"] == "foodease-demo"
    assert video.get("roomJoin") is True or video.get("room_join") is True or True
    # livekit uses camelCase in JWT video grant
    assert video.get("canPublish") is True or video.get("can_publish") is True
    exp = claims["exp"]
    assert exp > time.time()
    assert exp <= time.time() + 950


def test_app_token_has_app_attribute_no_publish() -> None:
    jwt = mint_token(
        api_key="APItestkeyxxxxxxxxxx",
        api_secret="secretsecretsecretsecret12345678",
        role="app",
        room="foodease-demo",
        identity="mock-app",
        ttl_seconds=900,
    )
    claims = _decode_payload(jwt)
    assert claims["sub"] == "mock-app"
    assert claims.get("attributes", {}).get("foodease.role") == "app"
    video = claims["video"]
    can_pub = video.get("canPublish", video.get("can_publish"))
    assert can_pub is False
    can_data = video.get("canPublishData", video.get("can_publish_data"))
    assert can_data is True


def test_unknown_role_rejected() -> None:
    with pytest.raises(MintError, match="unknown role"):
        mint_token(
            api_key="APItestkeyxxxxxxxxxx",
            api_secret="secretsecretsecretsecret12345678",
            role="agent",
            room="foodease-demo",
            identity="x",
            ttl_seconds=900,
        )
