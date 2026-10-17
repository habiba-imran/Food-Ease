"""Prepare the actual streaming session without output before worker-ready ACK."""

from __future__ import annotations

from dataclasses import replace

from livekit.agents import AgentSession

from foodease_agent.adapters.integrated import IntegratedRpcAdapter
from foodease_agent.config import load_config
from foodease_agent.idle import IdlePromptController
from foodease_agent.integrated.agent import IntegratedFoodEaseAgent
from foodease_agent.integrated.runtime import LiveConversationRuntime
from foodease_agent.session import build_session_kwargs


async def create_integrated_runtime(ctx, startup, gate) -> LiveConversationRuntime:
    # Never let an environment override enable speculative tool execution here.
    settings = replace(load_config(), preemptive_generation=False)
    adapter = IntegratedRpcAdapter(gate)
    # Verify the real application before constructing paid-provider clients.
    snapshot = await adapter.get_snapshot()
    bundle = build_session_kwargs(settings)
    if "vad" in ctx.proc.userdata:
        bundle.session_kwargs["vad"] = ctx.proc.userdata["vad"]
    session = AgentSession(**bundle.session_kwargs, max_tool_steps=8)
    runtime = LiveConversationRuntime(
        IntegratedFoodEaseAgent(),
        session,
        adapter,
        gate=gate,
        idle=IdlePromptController(settings.idle_prompt_1_seconds, settings.idle_prompt_2_seconds),
        speech_controls=frozenset({"speed", "volume"})
        if settings.tts_model.startswith("sonic-3")
        else frozenset(),
    )
    runtime.snapshot = snapshot
    try:
        await runtime.prepare()
    except BaseException:
        await runtime.close()
        raise
    return runtime
