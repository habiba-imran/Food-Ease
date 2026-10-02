"""Tests for fail-fast configuration loading (Phase 0)."""

from __future__ import annotations

import pytest

from foodease_agent.config import (
    REQUIRED_ENV_VARS,
    ConfigError,
    Settings,
    load_config,
)


def _complete_environ(**overrides: str) -> dict[str, str]:
    # Values stay under the V0.1 secret-grep shape (no long api_key=... literals).
    base = {
        "LIVEKIT_URL": "wss://example.livekit.cloud",
        "LIVEKIT_API_KEY": "<lk-key>",
        "LIVEKIT_API_SECRET": "<lk-secret>",
        "DEEPGRAM_API_KEY": "<dg-key>",
        "CARTESIA_API_KEY": "<cartesia-key>",
        "GOOGLE_API_KEY": "<google-key>",
        "STT_MODEL": "flux-general-en",
        "LLM_MODEL": "gemini-3.1-flash-lite",
        "LLM_THINKING_LEVEL": "minimal",
        "TTS_MODEL": "sonic-3.6",
        "TTS_VOICE_ID": "<voice-id>",
        "IDLE_PROMPT_1_SECONDS": "12",
        "IDLE_PROMPT_2_SECONDS": "30",
        "RECORD_AUDIO": "false",
        "DEV_MODE": "false",
        "VOICE_PIPELINE_CONFIG": "A",
        "SNAPSHOT_TIMEOUT_SECONDS": "2",
        "PREEMPTIVE_GENERATION": "false",
        "NOISE_CANCELLATION": "false",
        "GREETING_CACHE": "true",
    }
    base.update(overrides)
    return base


def test_load_config_success() -> None:
    settings = load_config(environ=_complete_environ())
    assert isinstance(settings, Settings)
    assert settings.stt_model == "flux-general-en"
    assert settings.record_audio is False
    assert settings.dev_mode is False
    assert settings.idle_prompt_1_seconds == 12.0
    assert settings.voice_pipeline_config == "A"
    assert settings.preemptive_generation is False


@pytest.mark.parametrize("missing", list(REQUIRED_ENV_VARS))
def test_missing_env_var_names_the_variable(missing: str) -> None:
    environ = _complete_environ()
    del environ[missing]
    with pytest.raises(ConfigError, match=missing):
        load_config(environ=environ)


def test_missing_multiple_lists_all_names() -> None:
    environ = _complete_environ()
    del environ["LIVEKIT_API_KEY"]
    del environ["GOOGLE_API_KEY"]
    with pytest.raises(ConfigError, match="LIVEKIT_API_KEY") as exc_info:
        load_config(environ=environ)
    assert "GOOGLE_API_KEY" in str(exc_info.value)


def test_blank_value_treated_as_missing() -> None:
    with pytest.raises(ConfigError, match="DEEPGRAM_API_KEY"):
        load_config(environ=_complete_environ(DEEPGRAM_API_KEY="   "))


def test_invalid_bool_rejected() -> None:
    with pytest.raises(ConfigError, match="RECORD_AUDIO"):
        load_config(environ=_complete_environ(RECORD_AUDIO="maybe"))
