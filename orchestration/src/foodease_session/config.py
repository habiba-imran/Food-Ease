"""Fail-fast env loader for the session service."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


class ConfigError(RuntimeError):
    """Missing or invalid configuration."""


def _load_dotenv_files() -> None:
    """Load orchestration/.env, then fall back to voice-agent/.env if present."""
    root = Path(__file__).resolve().parents[2]
    load_dotenv(root / ".env")
    sibling = root.parent / "voice-agent" / ".env"
    if sibling.is_file():
        load_dotenv(sibling, override=False)


def _parse_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    livekit_url: str
    livekit_api_key: str
    livekit_api_secret: str
    token_ttl_seconds: int
    host: str
    port: int
    cors_origins: tuple[str, ...]
    rate_limit_requests: int
    rate_limit_window_seconds: int
    livekit_agent_dispatch: bool
    foodease_agent_name: str


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigError(f"missing required env var: {name}")
    return value


def load_settings() -> Settings:
    _load_dotenv_files()
    ttl = int(os.environ.get("TOKEN_TTL_SECONDS", "900"))
    if ttl < 60 or ttl > 86_400:
        raise ConfigError("TOKEN_TTL_SECONDS must be between 60 and 86400")
    cors_raw = os.environ.get("CORS_ORIGINS", "http://127.0.0.1:8080").strip()
    origins = tuple(o.strip() for o in cors_raw.split(",") if o.strip())
    return Settings(
        livekit_url=_require("LIVEKIT_URL"),
        livekit_api_key=_require("LIVEKIT_API_KEY"),
        livekit_api_secret=_require("LIVEKIT_API_SECRET"),
        token_ttl_seconds=ttl,
        host=os.environ.get("HOST", "127.0.0.1").strip() or "127.0.0.1",
        port=int(os.environ.get("PORT", "8090")),
        cors_origins=origins,
        rate_limit_requests=int(os.environ.get("RATE_LIMIT_REQUESTS", "60")),
        rate_limit_window_seconds=int(os.environ.get("RATE_LIMIT_WINDOW_SECONDS", "60")),
        livekit_agent_dispatch=_parse_bool("LIVEKIT_AGENT_DISPATCH", True),
        foodease_agent_name=(
            os.environ.get("FOODEASE_AGENT_NAME", "foodease").strip() or "foodease"
        ),
    )
