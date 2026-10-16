"""Configuration for the FoodEase website."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


class ConfigError(RuntimeError):
    """Missing or invalid website configuration."""


def _load_dotenv_file() -> None:
    root = Path(__file__).resolve().parents[2]
    load_dotenv(root / ".env")


def _parse_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_path(raw: str) -> Path:
    root = Path(__file__).resolve().parents[2]
    path = Path(raw)
    if not path.is_absolute():
        path = root / path
    return path.resolve()


@dataclass(frozen=True)
class Settings:
    app_name: str
    host: str
    port: int
    orchestration_base_url: str
    catalog_seed_path: Path
    enable_mock_agent: bool
    enable_3d: bool
    enable_ar: bool


def load_settings() -> Settings:
    _load_dotenv_file()
    port = int(os.environ.get("PORT", "8080"))
    if port < 1 or port > 65535:
        raise ConfigError("PORT must be between 1 and 65535")
    catalog_seed_path = _resolve_path(
        os.environ.get("CATALOG_SEED_PATH", "../zainab-pack/catalog-seed.json")
    )
    if not catalog_seed_path.is_file():
        raise ConfigError(f"catalog seed not found: {catalog_seed_path}")
    return Settings(
        app_name=os.environ.get("APP_NAME", "FoodEase").strip() or "FoodEase",
        host=os.environ.get("HOST", "127.0.0.1").strip() or "127.0.0.1",
        port=port,
        orchestration_base_url=(
            os.environ.get("ORCHESTRATION_BASE_URL", "http://127.0.0.1:8090").strip()
            or "http://127.0.0.1:8090"
        ),
        catalog_seed_path=catalog_seed_path,
        enable_mock_agent=_parse_bool("ENABLE_MOCK_AGENT", True),
        enable_3d=_parse_bool("ENABLE_3D", True),
        enable_ar=_parse_bool("ENABLE_AR", False),
    )

