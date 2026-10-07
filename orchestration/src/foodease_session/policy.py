"""Consent and room naming policy."""

from __future__ import annotations

import re
import uuid

ROOM_PREFIX = "foodease-"
_ROOM_RE = re.compile(r"^foodease-[A-Za-z0-9][A-Za-z0-9_-]{0,62}$")


class PolicyError(ValueError):
    """Invalid session/room policy."""


def new_session_id() -> str:
    return f"sess_{uuid.uuid4().hex[:16]}"


def new_room_name() -> str:
    return f"{ROOM_PREFIX}{uuid.uuid4().hex[:12]}"


def normalize_room(room: str | None) -> str:
    """Return a valid room name; generate one when room is null/empty."""
    if room is None or not str(room).strip():
        return new_room_name()
    name = str(room).strip()
    if not _ROOM_RE.match(name):
        raise PolicyError(
            "room must match foodease-<id> (letters, digits, _-, max 64 chars after prefix rules)"
        )
    return name


def resolve_identity(provided: str | None, *, prefix: str) -> str:
    if provided is None or not str(provided).strip():
        return f"{prefix}-{uuid.uuid4().hex[:10]}"
    ident = str(provided).strip()
    if len(ident) > 64 or not re.match(r"^[A-Za-z0-9._@:/-]+$", ident):
        raise PolicyError("identity contains invalid characters or is too long")
    return ident
