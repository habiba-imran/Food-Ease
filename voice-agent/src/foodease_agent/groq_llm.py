"""Keep LiveKit's native Groq stream and tool parsing with managed HTTP admission."""

from dataclasses import replace

import httpx
import openai
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS
from livekit.plugins import groq

from foodease_agent.groq_capacity import CapacityTransport, Credential, Ledger, make_store


class CapacityGroqLLM(groq.LLM):
    def __init__(self, settings):
        keys = list(settings.groq_api_keys)
        keys[0] = keys[0] or settings.groq_api_key
        config = settings.groq_capacity
        credentials = []
        seen = set()
        for slot, key in enumerate(keys, 1):
            if key and key not in seen:
                seen.add(key)
                credentials.append(Credential(slot, key, config.pools[slot - 1]))
        store = make_store(config, settings.llm_model)
        transport = CapacityTransport(Ledger(store, config), credentials, config)
        self._capacity_client = openai.AsyncOpenAI(
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
            max_retries=0,
            http_client=httpx.AsyncClient(
                transport=transport, follow_redirects=False, timeout=httpx.Timeout(30, connect=10)
            ),
        )
        super().__init__(
            model=settings.llm_model, api_key=settings.groq_api_key, client=self._capacity_client
        )

    def chat(self, *, conn_options=DEFAULT_API_CONNECT_OPTIONS, **kwargs):
        # Only the transport can retry definitive pre-stream rejections. Neither
        # SDK layer may replay a stream, even when a caller supplies retry options.
        return super().chat(conn_options=replace(conn_options, max_retry=0), **kwargs)

    async def aclose(self):
        await super().aclose()
        await self._capacity_client.close()
