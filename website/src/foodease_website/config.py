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
    path = Path(raw)
    if not path.is_absolute():
        working_root = Path.cwd()
        module_root = Path(__file__).resolve().parents[2]
        root = working_root if (working_root / "pyproject.toml").is_file() else module_root
        path = root / path
    return path.resolve()


def _catalog_seed_path() -> Path:
    configured = os.environ.get("CATALOG_SEED_PATH")
    if configured and configured.strip():
        return _resolve_path(configured.strip())

    module_root = Path(__file__).resolve().parents[2]
    working_root = Path.cwd()
    candidates = (
        module_root.parent / "zainab-pack" / "catalog-seed.json",
        module_root / "zainab-pack" / "catalog-seed.json",
        working_root / "zainab-pack" / "catalog-seed.json",
    )
    return next((path.resolve() for path in candidates if path.is_file()), candidates[0].resolve())


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
    catalog_seed_path = _catalog_seed_path()
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

