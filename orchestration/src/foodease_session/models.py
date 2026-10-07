"""Pydantic request/response models for the session API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ParticipantToken(BaseModel):
    identity: str
    token: str
    role: Literal["user", "app"]


class SessionCreateRequest(BaseModel):
    consent: bool = False
    room: str | None = None
    user_identity: str | None = None
    app_identity: str | None = None
    include_app_token: bool = True


class SessionCreateResponse(BaseModel):
    schema_version: str = "1.0"
    session_id: str
    room: str
    livekit_url: str
    expires_at: str
    ttl_seconds: int
    voice_allowed: bool
    user: ParticipantToken | None = None
    app: ParticipantToken | None = None


class TokenMintRequest(BaseModel):
    role: Literal["user", "app"]
    room: str
    identity: str | None = None
    # Narrow mint for app (MockApp / website) does not require consent.
    # User role requires consent=true to avoid silent mic-capable JWTs.
    consent: bool = False


class TokenMintResponse(BaseModel):
    schema_version: str = "1.0"
    room: str
    livekit_url: str
    expires_at: str
    ttl_seconds: int
    participant: ParticipantToken


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str = "foodease-session"


class ErrorBody(BaseModel):
    error: str
    detail: str | None = None


class AssistStartRequest(BaseModel):
    consent: bool = False
    room: str | None = None
    user_identity: str | None = None
    app_identity: str | None = None
    include_app_token: bool = False


class AssistStartResponse(BaseModel):
    schema_version: str = "1.0"
    session_id: str
    room: str
    livekit_url: str
    expires_at: str
    ttl_seconds: int
    voice_allowed: bool
    dispatch_id: str | None = None
    dispatch_enabled: bool = True
    user: ParticipantToken | None = None
    app: ParticipantToken | None = None


class AssistEndRequest(BaseModel):
    room: str
    dispatch_id: str | None = None
    session_id: str | None = None


class AssistEndResponse(BaseModel):
    schema_version: str = "1.0"
    room: str
    ended: bool = True
    cart_preserved: bool = True
    dispatch_id: str | None = None
    dispatch_deleted: bool = False
