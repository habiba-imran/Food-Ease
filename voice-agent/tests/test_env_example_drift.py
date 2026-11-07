"""V0.4: every env var read by config.py must appear in `.env.example`."""

from __future__ import annotations

from pathlib import Path

from foodease_agent.config import LLM_REQUIRED_ENV_VARS, REQUIRED_ENV_VARS, RUNTIME_ENV_DEFAULTS

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_EXAMPLE = REPO_ROOT / ".env.example"
DECLARED_KEYS = set(REQUIRED_ENV_VARS) | RUNTIME_ENV_DEFAULTS.keys() | {
    name for fields in LLM_REQUIRED_ENV_VARS.values() for name in fields
}


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
    missing = sorted(DECLARED_KEYS - example_keys)
    assert missing == [], f"Variables read by config.py missing from .env.example: {missing}"


def test_env_example_has_no_extra_unknown_keys() -> None:
    """Allow only the declared config surface in .env.example for Phase 0."""
    example_keys = _keys_in_env_example()
    extras = sorted(example_keys - DECLARED_KEYS)
    assert extras == [], f"Unexpected keys in .env.example: {extras}"
