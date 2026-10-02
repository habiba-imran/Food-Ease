"""AgentSession factory — configs A (Flux/STT) and B (Nova-3 + VAD + TurnDetector)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from livekit.agents import AgentSession, TurnHandlingOptions, inference
from livekit.plugins import cartesia, deepgram, google, silero

from foodease_agent.config import Settings

PipelineConfig = Literal["A", "B"]


@dataclass(frozen=True)
class SessionBundle:
    session_kwargs: dict[str, Any]
    pipeline: PipelineConfig
    preemptive_enabled: bool


def turn_handling_options(
    *,
    turn_detection: Any,
    endpointing_min: float = 0.45,
    endpointing_max: float = 3.0,
    preemptive_enabled: bool = False,
) -> TurnHandlingOptions:
    """Starting turn-taking values (Phase 5.5); tune in Phase 9."""
    return TurnHandlingOptions(
        turn_detection=turn_detection,
        endpointing={
            "mode": "fixed",
            "min_delay": endpointing_min,
            "max_delay": endpointing_max,
        },
        interruption={
            "mode": "adaptive",
            "min_duration": 0.5,
            "min_words": 0,
            "false_interruption_timeout": 2.0,
            "resume_false_interruption": True,
        },
        # ADR-0008: default off; mutating tools also gated by TurnCommitGate.
        preemptive_generation={"enabled": preemptive_enabled},
    )


def build_stt(settings: Settings, pipeline: PipelineConfig) -> Any:
    if pipeline == "A":
        # Flux via STTv2 + STT-based turn detection (ADR-0005 provisional).
        return deepgram.STTv2(
            model=settings.stt_model or "flux-general-en",
            api_key=settings.deepgram_api_key,
        )
    # Config B: Nova-3
    return deepgram.STT(
        model="nova-3",
        api_key=settings.deepgram_api_key,
        interim_results=True,
        punctuate=True,
    )


def build_tts(settings: Settings) -> cartesia.TTS:
    return cartesia.TTS(
        model=settings.tts_model,
        voice=settings.tts_voice_id,
        api_key=settings.cartesia_api_key,
        word_timestamps=True,
    )


def build_llm(settings: Settings) -> google.LLM:
    return google.LLM(
        model=settings.llm_model,
        api_key=settings.google_api_key,
        thinking_config={"thinking_level": settings.llm_thinking_level},
    )


def build_session_kwargs(
    settings: Settings,
    *,
    pipeline: PipelineConfig | None = None,
) -> SessionBundle:
    """Assemble kwargs for ``AgentSession(**kwargs)`` without starting I/O."""
    chosen: PipelineConfig = pipeline or settings.voice_pipeline_config
    preemptive = settings.preemptive_generation

    stt = build_stt(settings, chosen)
    tts = build_tts(settings)
    llm = build_llm(settings)

    if chosen == "A":
        # Flux owns EOT; endpointing min_delay 0 so STT endpointing dominates.
        turn = turn_handling_options(
            turn_detection="stt",
            endpointing_min=0.0,
            endpointing_max=3.0,
            preemptive_enabled=preemptive,
        )
        vad = silero.VAD.load()  # still needed for interruptions
        kwargs: dict[str, Any] = {
            "stt": stt,
            "llm": llm,
            "tts": tts,
            "vad": vad,
            "turn_handling": turn,
            "use_tts_aligned_transcript": True,
        }
    else:
        vad = silero.VAD.load()
        turn = turn_handling_options(
            turn_detection=inference.TurnDetector(),
            endpointing_min=0.45,
            endpointing_max=3.0,
            preemptive_enabled=preemptive,
        )
        kwargs = {
            "stt": stt,
            "llm": llm,
            "tts": tts,
            "vad": vad,
            "turn_handling": turn,
            "use_tts_aligned_transcript": True,
        }

    return SessionBundle(
        session_kwargs=kwargs,
        pipeline=chosen,
        preemptive_enabled=preemptive,
    )


def create_agent_session(
    settings: Settings,
    *,
    pipeline: PipelineConfig | None = None,
) -> AgentSession:
    bundle = build_session_kwargs(settings, pipeline=pipeline)
    return AgentSession(**bundle.session_kwargs)
