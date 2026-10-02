"""V0.4: every env var read by config.py must appear in `.env.example`."""

from __future__ import annotations

from pathlib import Path

from foodease_agent.config import REQUIRED_ENV_VARS

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_EXAMPLE = REPO_ROOT / ".env.example"


def _keys_in_env_example() -> set[str]:
    keys: set[str] = set()
    for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        keys.add(stripped.split("=", 1)[0].strip())
    return keys


def test_env_example_covers_all_config_vars() -> None:
    example_keys = _keys_in_env_example()
    missing = [name for name in REQUIRED_ENV_VARS if name not in example_keys]
    assert missing == [], f"Variables read by config.py missing from .env.example: {missing}"


def test_env_example_has_no_extra_unknown_keys() -> None:
    """Allow only the declared config surface in .env.example for Phase 0."""
    example_keys = _keys_in_env_example()
    required = set(REQUIRED_ENV_VARS)
    extras = sorted(example_keys - required)
    assert extras == [], f"Unexpected keys in .env.example: {extras}"
