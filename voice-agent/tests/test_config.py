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
        "ASSISTANT_LANGUAGE": "en",
        "LIVEKIT_URL": "wss://example.livekit.cloud",
        "LIVEKIT_API_KEY": "<lk-key>",
        "LIVEKIT_API_SECRET": "<lk-secret>",
        "DEEPGRAM_API_KEY": "<dg-key>",
        "CARTESIA_API_KEY": "<cartesia-key>",
        "GROQ_API_KEY": "<groq-key>",
        "GOOGLE_API_KEY": "<google-key>",
        "STT_MODEL": "flux-general-en",
        "LLM_MODEL": "gemini-3.1-flash-lite",
        "LLM_THINKING_LEVEL": "minimal",
        "TTS_MODEL": "sonic-3.6",
        "TTS_VOICE_ID": "db6b0ed5-d5d3-463d-ae85-518a07d3c2b4",
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
    assert settings.llm_provider == "groq"
    assert settings.llm_model == "openai/gpt-oss-20b"


def test_groq_uses_only_its_own_settings() -> None:
    environ = _complete_environ(GROQ_MODEL="openai/gpt-oss-120b")
    for key in ("GOOGLE_API_KEY", "LLM_MODEL", "LLM_THINKING_LEVEL"):
        del environ[key]
    settings = load_config(environ=environ)
    assert settings.llm_model == "openai/gpt-oss-120b"
    assert settings.groq_api_key == "<groq-key>"


def test_optional_groq_credentials_are_trimmed_and_excluded_from_repr():
    settings = load_config(environ=_complete_environ(GROQ_API_KEY_2=" <second-key> ",
                                                    GROQ_API_KEY_4="<fourth-key>"))
    assert settings.groq_api_keys == ("<groq-key>", "<second-key>", "", "<fourth-key>")
    assert "<second-key>" not in repr(settings)
    assert "<groq-key>" not in repr(settings)


def test_gemini_still_uses_its_existing_settings_without_groq_key() -> None:
    environ = _complete_environ(LLM_PROVIDER="gemini")
    del environ["GROQ_API_KEY"]
    settings = load_config(environ=environ)
    assert settings.llm_provider == "gemini"
    assert settings.llm_model == environ["LLM_MODEL"]
    assert settings.llm_thinking_level == environ["LLM_THINKING_LEVEL"]


def test_missing_groq_key_does_not_fall_back_to_google() -> None:
    with pytest.raises(ConfigError, match="GROQ_API_KEY"):
        load_config(environ=_complete_environ(GROQ_API_KEY=""))


def test_invalid_provider_rejected() -> None:
    with pytest.raises(ConfigError, match="LLM_PROVIDER"):
        load_config(environ=_complete_environ(LLM_PROVIDER="unknown"))


@pytest.mark.parametrize("voice", [None, " ", "invalid-voice-placeholder"])
def test_missing_or_malformed_cartesia_voice_uses_verified_default(voice, caplog):
    environ = _complete_environ()
    if voice is None:
        del environ["TTS_VOICE_ID"]
    else:
        environ["TTS_VOICE_ID"] = voice
    assert load_config(environ=environ).tts_voice_id == "9626c31c-bec5-4cca-baa8-f8ba9e84c8bc"
    assert "invalid-voice-placeholder" not in caplog.text


def test_valid_custom_cartesia_voice_is_preserved() -> None:
    voice = "db6b0ed5-d5d3-463d-ae85-518a07d3c2b4"
    assert load_config(environ=_complete_environ(TTS_VOICE_ID=voice)).tts_voice_id == voice


def test_older_env_uses_documented_runtime_defaults() -> None:
    environ = _complete_environ()
    del environ["VOICE_PIPELINE_CONFIG"]
    del environ["SNAPSHOT_TIMEOUT_SECONDS"]
    del environ["PREEMPTIVE_GENERATION"]
    del environ["NOISE_CANCELLATION"]
    environ["GREETING_CACHE"] = ""
    settings = load_config(environ=environ)
    assert settings.voice_pipeline_config == "A"
    assert settings.snapshot_timeout_seconds == 2
    assert settings.preemptive_generation is False
    assert settings.noise_cancellation is False
    assert settings.greeting_cache is True


@pytest.mark.parametrize("missing", list(REQUIRED_ENV_VARS))
def test_missing_env_var_names_the_variable(missing: str) -> None:
    environ = _complete_environ()
    del environ[missing]
    with pytest.raises(ConfigError, match=missing):
        load_config(environ=environ)


def test_missing_multiple_lists_all_names() -> None:
    environ = _complete_environ(LLM_PROVIDER="gemini")
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
