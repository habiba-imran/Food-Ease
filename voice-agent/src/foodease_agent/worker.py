"""LiveKit worker entrypoint — prewarm, consent-gated session start."""

from __future__ import annotations

import logging

from livekit.agents import (
    AgentSession,
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    room_io,
)
from livekit.plugins import silero

from foodease_agent.adapters.dev_wiring import create_dev_adapter
from foodease_agent.agent import FoodEaseAgent, apply_speech_speed
from foodease_agent.config import load_config
from foodease_agent.contract.enums import ProductState
from foodease_agent.session import build_session_kwargs

logger = logging.getLogger("foodease_agent.worker")


def prewarm(proc: JobProcess) -> None:
    """Load VAD early so the consented session starts warm (5.2)."""
    proc.userdata["vad"] = silero.VAD.load()
    logger.info("prewarm: silero VAD loaded")


async def entrypoint(ctx: JobContext) -> None:
    """Join only after the job is dispatched (harness Start button → room)."""
    settings = load_config()
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    agent = FoodEaseAgent(settings, adapter=create_dev_adapter())
    agent.product_state = ProductState.CONNECTING

    bundle = build_session_kwargs(settings)
    # Prefer prewarmed VAD when present.
    if "vad" in ctx.proc.userdata:
        bundle.session_kwargs["vad"] = ctx.proc.userdata["vad"]

    session = AgentSession(**bundle.session_kwargs)

    # Noise cancellation (5.8): env toggle recorded; plugin wiring needs LiveKit NC
    # module when the Cloud plan includes it. Default off — no silent fake enable.
    if settings.noise_cancellation:
        logger.warning(
            "NOISE_CANCELLATION=true but NC module not wired on this tier; "
            "continuing without NC (see evidence/phase-5)"
        )
    room_options = room_io.RoomOptions(
        text_input=True,
        close_on_disconnect=True,
    )

    await session.start(
        agent=agent,
        room=ctx.room,
        room_options=room_options,
    )

    agent.product_state = ProductState.READY_LISTENING
    # Snapshot may arrive later via data/RPC; timeout path still greets (V5.10).
    await agent.proactive_greeting(session)
    await apply_speech_speed(session, agent._tts_speed)


def main() -> None:
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        )
    )


if __name__ == "__main__":
    main()
