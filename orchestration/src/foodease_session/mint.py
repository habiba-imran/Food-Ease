"""LiveKit JWT minting for user vs app roles."""

from __future__ import annotations

from datetime import timedelta
from enum import StrEnum
from typing import Any

from livekit.api import AccessToken, VideoGrants


class Role(StrEnum):
    USER = "user"
    APP = "app"


class MintError(ValueError):
    """Invalid mint request."""


def _grants_for_role(role: Role, room: str) -> VideoGrants:
    if role is Role.USER:
        return VideoGrants(
            room_join=True,
            room=room,
            can_publish=True,
            can_subscribe=True,
            can_publish_data=True,
        )
    # App: data + subscribe; no mic publish required for the website stand-in
    return VideoGrants(
        room_join=True,
        room=room,
        can_publish=False,
        can_subscribe=True,
        can_publish_data=True,
    )


def _attributes_for_role(role: Role) -> dict[str, str]:
    if role is Role.APP:
        return {"foodease.role": "app"}
    return {"foodease.role": "user"}


def mint_token(
    *,
    api_key: str,
    api_secret: str,
    role: Role | str,
    room: str,
    identity: str,
    ttl_seconds: int,
    name: str | None = None,
    session_id: str | None = None,
    generation: str | None = None,
) -> str:
    """Return a short-lived LiveKit access JWT for the given role."""
    try:
        role_enum = role if isinstance(role, Role) else Role(str(role))
    except ValueError as exc:
        raise MintError(f"unknown role: {role!r}; expected 'user' or 'app'") from exc
    if not room or not identity:
        raise MintError("room and identity are required")
    if ttl_seconds < 60:
        raise MintError("ttl_seconds must be >= 60")

    attributes = _attributes_for_role(role_enum)
    grants = _grants_for_role(role_enum, room)
    if session_id is not None and generation is not None:
        attributes.update({"foodease.session": session_id, "foodease.generation": generation})
        grants.can_update_own_metadata = False
        if role_enum is Role.USER:
            grants.can_publish_sources = ["microphone"]
    token = (
        AccessToken(api_key, api_secret)
        .with_identity(identity)
        .with_name(name or identity)
        .with_ttl(timedelta(seconds=ttl_seconds))
        .with_attributes(attributes)
        .with_grants(grants)
    )
    return token.to_jwt()


def mint_pair(
    *,
    api_key: str,
    api_secret: str,
    room: str,
    user_identity: str,
    app_identity: str,
    ttl_seconds: int,
    include_user: bool,
    include_app: bool,
) -> dict[str, Any]:
    """Mint user and/or app tokens for one room."""
    out: dict[str, Any] = {}
    if include_user:
        out["user"] = {
            "identity": user_identity,
            "token": mint_token(
                api_key=api_key,
                api_secret=api_secret,
                role=Role.USER,
                room=room,
                identity=user_identity,
                ttl_seconds=ttl_seconds,
            ),
            "role": Role.USER.value,
        }
    if include_app:
        out["app"] = {
            "identity": app_identity,
            "token": mint_token(
                api_key=api_key,
                api_secret=api_secret,
                role=Role.APP,
                room=room,
                identity=app_identity,
                ttl_seconds=ttl_seconds,
            ),
            "role": Role.APP.value,
        }
    return out
