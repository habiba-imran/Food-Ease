"""LiveKit worker entrypoint — prewarm; greet only after assist dispatch."""

from __future__ import annotations

import json
import logging
import os

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

from foodease_agent.adapters.dev_wiring import (
    app_transport_mode,
    create_dev_adapter,
    wait_for_livekit_app,
)
from foodease_agent.agent import FoodEaseAgent, apply_speech_speed
from foodease_agent.config import load_config
from foodease_agent.contract.enums import ProductState
from foodease_agent.session import build_session_kwargs

logger = logging.getLogger("foodease_agent.worker")


def prewarm(proc: JobProcess) -> None:
    """Load VAD early so the consented session starts warm (5.2)."""
    proc.userdata["vad"] = silero.VAD.load()
    logger.info("prewarm: silero VAD loaded")


def _job_assist_flag(ctx: JobContext) -> bool:
    """True when dispatch metadata marks an assist session (or metadata absent)."""
    raw = getattr(ctx.job, "metadata", None) or ""
    if not str(raw).strip():
        return True
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return True
    if "foodease.assist" not in data:
        return True
    return bool(data.get("foodease.assist"))


async def entrypoint(ctx: JobContext) -> None:
    """Run after LiveKit dispatches a job (orchestration POST /v1/assist/start)."""
    settings = load_config()
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    transport = app_transport_mode()
    adapter = create_dev_adapter(rtc_room=ctx.room if transport == "livekit" else None)
    agent = FoodEaseAgent(settings, adapter=adapter)
    agent.product_state = ProductState.CONNECTING

    async def _on_shutdown(_reason: str = "") -> None:
        agent.idle.disable()
        agent.product_state = ProductState.ENDED
        logger.info("assist_shutdown reason=%s idle_disabled=true", _reason or "n/a")

    ctx.add_shutdown_callback(_on_shutdown)

    if not _job_assist_flag(ctx):
        logger.warning("job without foodease.assist — skipping greeting/idle")
        agent.product_state = ProductState.OFF_AWAITING_CONSENT
        return

    if transport == "livekit":
        try:
            await wait_for_livekit_app(adapter, timeout_s=15.0)
        except TimeoutError:
            logger.error(
                "FOODEASE_APP_TRANSPORT=livekit but no foodease.role=app in room — "
                "start MockApp with --livekit (or Zainab site) before assist"
            )
            agent.product_state = ProductState.ERROR
            return

    bundle = build_session_kwargs(settings)
    if "vad" in ctx.proc.userdata:
        bundle.session_kwargs["vad"] = ctx.proc.userdata["vad"]

    session = AgentSession(**bundle.session_kwargs)

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
    await agent.proactive_greeting(session)
    await apply_speech_speed(session, agent._tts_speed)


def main() -> None:
    agent_name = (os.environ.get("FOODEASE_AGENT_NAME") or "foodease").strip() or "foodease"
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            agent_name=agent_name,
        )
    )


if __name__ == "__main__":
    main()
