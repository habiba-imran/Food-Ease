"""Exercise the installed plugin's chat setup, where the production failure occurred."""

import asyncio

import pytest
from livekit.agents import llm
from livekit.plugins import google
from livekit.plugins.google.llm import LLMStream

from foodease_agent.session import build_llm
from test_phase5_voice import _settings


@pytest.mark.parametrize("model,budget", [
    ("gemini-2.5-flash", 0), ("gemini-2.5-flash-lite", 0), ("gemini-2.5-pro", 128),
])
async def test_gemini_25_chat_setup_uses_supported_budget(monkeypatch, model, budget):
    async def no_network(self):
        await asyncio.sleep(0)

    monkeypatch.setattr(LLMStream, "_run", no_network)
    client = build_llm(_settings(llm_model=model))
    assert isinstance(client, google.LLM)
    try:
        # Constructor-only tests missed the error: validation happens in chat().
        stream = client.chat(chat_ctx=llm.ChatContext())
        try:
            assert client._opts.thinking_config == {"thinking_budget": budget}
        finally:
            await stream.aclose()
    finally:
        await client.aclose()


async def test_available_flash_lite_chat_setup_uses_minimal_level(monkeypatch):
    async def no_network(self):
        await asyncio.sleep(0)

    monkeypatch.setattr(LLMStream, "_run", no_network)
    client = build_llm(_settings(llm_model="gemini-3.5-flash-lite"))
    assert isinstance(client, google.LLM)
    try:
        stream = client.chat(chat_ctx=llm.ChatContext())
        try:
            assert client._opts.thinking_config == {"thinking_level": "minimal"}
        finally:
            await stream.aclose()
    finally:
        await client.aclose()
