"""Environment-backed settings. Fail fast; never call providers."""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID

from dotenv import load_dotenv

logger = logging.getLogger(__name__)
DEFAULT_CARTESIA_VOICE_ID = "9626c31c-bec5-4cca-baa8-f8ba9e84c8bc"

# Names read by this module — must stay in sync with `.env.example` (see tests).
SECRET_ENV_VARS: tuple[str, ...] = (
    "LIVEKIT_URL",
    "LIVEKIT_API_KEY",
    "LIVEKIT_API_SECRET",
    "DEEPGRAM_API_KEY",
    "CARTESIA_API_KEY",
)

NON_SECRET_ENV_VARS: tuple[str, ...] = (
    "STT_MODEL",
    "TTS_MODEL",
    "IDLE_PROMPT_1_SECONDS",
    "IDLE_PROMPT_2_SECONDS",
    "RECORD_AUDIO",
    "DEV_MODE",
)

# Defaults from .env.example for existing installations created before these knobs.
RUNTIME_ENV_DEFAULTS = {
    "ASSISTANT_LANGUAGE": "ur",
    "URDU_STT_MODEL": "whisper-large-v3-turbo",
    "LLM_PROVIDER": "groq",
    "GROQ_MODEL": "openai/gpt-oss-20b",
    "TTS_VOICE_ID": DEFAULT_CARTESIA_VOICE_ID,
    "VOICE_PIPELINE_CONFIG": "A",
    "SNAPSHOT_TIMEOUT_SECONDS": "2",
    "PREEMPTIVE_GENERATION": "false",
    "NOISE_CANCELLATION": "false",
    "GREETING_CACHE": "true",
}

# Optional Phase 9 tuning (defaults applied when unset).
OPTIONAL_TUNING_ENV_VARS: tuple[str, ...] = (
    "INTERRUPTION_MIN_DURATION",
    "INTERRUPTION_MIN_WORDS",
    "INTERRUPTION_FALSE_TIMEOUT",
    "ENDPOINTING_MIN",
    "ENDPOINTING_MAX",
)

REQUIRED_ENV_VARS: tuple[str, ...] = SECRET_ENV_VARS + NON_SECRET_ENV_VARS
LLM_REQUIRED_ENV_VARS = {
    "groq": ("GROQ_API_KEY",),
    "gemini": ("GOOGLE_API_KEY", "LLM_MODEL", "LLM_THINKING_LEVEL"),
}


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


def _optional_float(environ: Mapping[str, str], name: str, default: float) -> float:
    raw = environ.get(name)
    if raw is None or not raw.strip():
        return default
    return _parse_float(name, raw)


def _optional_int(environ: Mapping[str, str], name: str, default: int) -> int:
    raw = environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw.strip())
    except ValueError as exc:
        raise ConfigError(f"Invalid integer for {name}={raw!r}") from exc


def _parse_pipeline(name: str, raw: str) -> str:
    normalized = raw.strip().upper()
    if normalized in {"A", "B"}:
        return normalized
    raise ConfigError(f"Invalid {name}={raw!r}; expected A or B")


def _cartesia_voice_id(raw: str) -> str:
    try:
        return str(UUID(raw.strip()))
    except ValueError:
        logger.warning(
            "TTS_VOICE_ID must be a Cartesia voice UUID. Using the FoodEase default voice."
        )
        return DEFAULT_CARTESIA_VOICE_ID


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
    interruption_min_duration: float
    interruption_min_words: int
    interruption_false_timeout: float
    endpointing_min: float
    endpointing_max: float
    llm_provider: str = "groq"
    groq_api_key: str = ""
    assistant_language: str = "en"
    urdu_stt_model: str = "whisper-large-v3-turbo"


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

    environ = {
        **environ,
        **{
            name: default for name, default in RUNTIME_ENV_DEFAULTS.items()
            if not environ.get(name, "").strip()
        },
    }
    llm_provider = environ["LLM_PROVIDER"].strip().lower()
    language = environ["ASSISTANT_LANGUAGE"].strip().lower()
    if language not in {"ur", "en"}:
        raise ConfigError("Invalid ASSISTANT_LANGUAGE. Expected ur or en.")
    if language == "ur" and environ["URDU_STT_MODEL"] not in {
        "whisper-large-v3", "whisper-large-v3-turbo",
    }:
        raise ConfigError("URDU_STT_MODEL must be a multilingual Whisper model.")
    if llm_provider not in LLM_REQUIRED_ENV_VARS:
        raise ConfigError("Invalid LLM_PROVIDER. Expected groq or gemini.")
    required = REQUIRED_ENV_VARS + LLM_REQUIRED_ENV_VARS[llm_provider]
    if language == "ur":
        required = tuple(name for name in required if name != "DEEPGRAM_API_KEY")
        required += ("GROQ_API_KEY",)
    missing = [name for name in required if not (environ.get(name) or "").strip()]
    if missing:
        # Name every missing var so operators can fix one or many at once.
        raise ConfigError(
            "Missing required environment variable(s): " + ", ".join(missing)
        )

    using_gemini = llm_provider == "gemini"
    return Settings(
        livekit_url=_require(environ, "LIVEKIT_URL"),
        livekit_api_key=_require(environ, "LIVEKIT_API_KEY"),
        livekit_api_secret=_require(environ, "LIVEKIT_API_SECRET"),
        deepgram_api_key=environ.get("DEEPGRAM_API_KEY", "") if language == "ur"
        else _require(environ, "DEEPGRAM_API_KEY"),
        cartesia_api_key=_require(environ, "CARTESIA_API_KEY"),
        google_api_key=_require(environ, "GOOGLE_API_KEY") if using_gemini else "",
        stt_model=_require(environ, "STT_MODEL"),
        llm_model=_require(environ, "LLM_MODEL" if using_gemini else "GROQ_MODEL").strip(),
        llm_thinking_level=_require(environ, "LLM_THINKING_LEVEL") if using_gemini else "",
        tts_model=_require(environ, "TTS_MODEL"),
        tts_voice_id=_cartesia_voice_id(environ["TTS_VOICE_ID"]),
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
        interruption_min_duration=_optional_float(environ, "INTERRUPTION_MIN_DURATION", 0.5),
        interruption_min_words=_optional_int(environ, "INTERRUPTION_MIN_WORDS", 0),
        interruption_false_timeout=_optional_float(
            environ, "INTERRUPTION_FALSE_TIMEOUT", 2.0
        ),
        endpointing_min=_optional_float(environ, "ENDPOINTING_MIN", 0.45),
        endpointing_max=_optional_float(environ, "ENDPOINTING_MAX", 3.0),
        llm_provider=llm_provider,
        groq_api_key=_require(environ, "GROQ_API_KEY")
        if not using_gemini or language == "ur" else "",
        assistant_language=language,
        urdu_stt_model=environ["URDU_STT_MODEL"],
    )
