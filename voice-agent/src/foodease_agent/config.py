"""Environment-backed settings. Fail fast; never call providers."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from dotenv import load_dotenv

# Names read by this module — must stay in sync with `.env.example` (see tests).
SECRET_ENV_VARS: tuple[str, ...] = (
    "LIVEKIT_URL",
    "LIVEKIT_API_KEY",
    "LIVEKIT_API_SECRET",
    "DEEPGRAM_API_KEY",
    "CARTESIA_API_KEY",
    "GOOGLE_API_KEY",
)

NON_SECRET_ENV_VARS: tuple[str, ...] = (
    "STT_MODEL",
    "LLM_MODEL",
    "LLM_THINKING_LEVEL",
    "TTS_MODEL",
    "TTS_VOICE_ID",
    "IDLE_PROMPT_1_SECONDS",
    "IDLE_PROMPT_2_SECONDS",
    "RECORD_AUDIO",
    "DEV_MODE",
    "VOICE_PIPELINE_CONFIG",
    "SNAPSHOT_TIMEOUT_SECONDS",
    "PREEMPTIVE_GENERATION",
    "NOISE_CANCELLATION",
    "GREETING_CACHE",
)

REQUIRED_ENV_VARS: tuple[str, ...] = SECRET_ENV_VARS + NON_SECRET_ENV_VARS


class ConfigError(ValueError):
    """Raised when required configuration is missing or invalid."""


def _require(environ: Mapping[str, str], name: str) -> str:
    value = environ.get(name)
    if value is None or value.strip() == "":
        raise ConfigError(f"Missing required environment variable: {name}")
    return value


def _parse_bool(name: str, raw: str) -> bool:
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigError(
        f"Invalid boolean for {name}={raw!r}; expected true/false (or 1/0)"
    )


def _parse_float(name: str, raw: str) -> float:
    try:
        return float(raw.strip())
    except ValueError as exc:
        raise ConfigError(f"Invalid number for {name}={raw!r}") from exc


def _parse_pipeline(name: str, raw: str) -> str:
    normalized = raw.strip().upper()
    if normalized in {"A", "B"}:
        return normalized
    raise ConfigError(f"Invalid {name}={raw!r}; expected A or B")


@dataclass(frozen=True, slots=True)
class Settings:
    livekit_url: str
    livekit_api_key: str
    livekit_api_secret: str
    deepgram_api_key: str
    cartesia_api_key: str
    google_api_key: str
    stt_model: str
    llm_model: str
    llm_thinking_level: str
    tts_model: str
    tts_voice_id: str
    idle_prompt_1_seconds: float
    idle_prompt_2_seconds: float
    record_audio: bool
    dev_mode: bool
    voice_pipeline_config: str  # "A" | "B"
    snapshot_timeout_seconds: float
    preemptive_generation: bool
    noise_cancellation: bool
    greeting_cache: bool


def load_config(
    *,
    environ: Mapping[str, str] | None = None,
    dotenv_path: str | None = None,
) -> Settings:
    """Load settings from the environment.

    When ``environ`` is omitted, optionally loads a ``.env`` file into
    ``os.environ`` (without overriding existing process vars), then reads
    ``os.environ``. Pass an explicit ``environ`` mapping in tests so a local
    ``.env`` cannot mask missing-variable checks.

    Never logs or returns a debug dump of secret values.
    """
    if environ is None:
        load_dotenv(dotenv_path)  # no-op if file missing; does not override existing
        environ = os.environ

    missing = [name for name in REQUIRED_ENV_VARS if not (environ.get(name) or "").strip()]
    if missing:
        # Name every missing var so operators can fix one or many at once.
        raise ConfigError(
            "Missing required environment variable(s): " + ", ".join(missing)
        )

    return Settings(
        livekit_url=_require(environ, "LIVEKIT_URL"),
        livekit_api_key=_require(environ, "LIVEKIT_API_KEY"),
        livekit_api_secret=_require(environ, "LIVEKIT_API_SECRET"),
        deepgram_api_key=_require(environ, "DEEPGRAM_API_KEY"),
        cartesia_api_key=_require(environ, "CARTESIA_API_KEY"),
        google_api_key=_require(environ, "GOOGLE_API_KEY"),
        stt_model=_require(environ, "STT_MODEL"),
        llm_model=_require(environ, "LLM_MODEL"),
        llm_thinking_level=_require(environ, "LLM_THINKING_LEVEL"),
        tts_model=_require(environ, "TTS_MODEL"),
        tts_voice_id=_require(environ, "TTS_VOICE_ID"),
        idle_prompt_1_seconds=_parse_float(
            "IDLE_PROMPT_1_SECONDS", _require(environ, "IDLE_PROMPT_1_SECONDS")
        ),
        idle_prompt_2_seconds=_parse_float(
            "IDLE_PROMPT_2_SECONDS", _require(environ, "IDLE_PROMPT_2_SECONDS")
        ),
        record_audio=_parse_bool("RECORD_AUDIO", _require(environ, "RECORD_AUDIO")),
        dev_mode=_parse_bool("DEV_MODE", _require(environ, "DEV_MODE")),
        voice_pipeline_config=_parse_pipeline(
            "VOICE_PIPELINE_CONFIG", _require(environ, "VOICE_PIPELINE_CONFIG")
        ),
        snapshot_timeout_seconds=_parse_float(
            "SNAPSHOT_TIMEOUT_SECONDS", _require(environ, "SNAPSHOT_TIMEOUT_SECONDS")
        ),
        preemptive_generation=_parse_bool(
            "PREEMPTIVE_GENERATION", _require(environ, "PREEMPTIVE_GENERATION")
        ),
        noise_cancellation=_parse_bool(
            "NOISE_CANCELLATION", _require(environ, "NOISE_CANCELLATION")
        ),
        greeting_cache=_parse_bool("GREETING_CACHE", _require(environ, "GREETING_CACHE")),
    )
