"""Capacity decisions use fake provider traffic and a shared fake Redis server."""

import asyncio
import json
import threading
from dataclasses import replace

import fakeredis.aioredis
import httpx
import pytest

from foodease_agent.groq_capacity import (
    CapacityConfig,
    CapacityTransport,
    Credential,
    Ledger,
    RedisStore,
    SQLiteStore,
    estimate,
)


def config(**changes):
    return replace(CapacityConfig(), **changes)


def credentials():
    return [Credential(i, f"<key-{i}>", f"approved-account-{i}") for i in range(1, 5)]


@pytest.fixture
def shared():
    server = fakeredis.FakeServer()
    return lambda: RedisStore(fakeredis.aioredis.FakeRedis(server=server))


async def seed(ledger, pool, remaining, *, reset="60s", requests=900):
    ticket = await ledger.reserve([Credential(1, "<fake>", pool)], 100, 100)
    assert ticket is not None
    await ledger.finish(
        ticket,
        {
            "x-ratelimit-remaining-tokens": str(remaining),
            "x-ratelimit-reset-tokens": reset,
            "x-ratelimit-remaining-requests": str(requests),
            "x-ratelimit-reset-requests": "24h",
        },
        usage={"prompt_tokens": 100, "completion_tokens": 100},
    )


async def test_primary_has_capacity(shared):
    ledger = Ledger(shared(), config())
    ticket = await ledger.reserve(credentials(), 1000, 1024)
    assert ticket is not None
    assert ticket.credential.slot == 1


async def test_switches_before_request_without_waiting_for_zero(shared):
    ledger = Ledger(shared(), config())
    await seed(ledger, credentials()[0].pool, 1100)
    ticket = await ledger.reserve(credentials(), 1000, 1024)
    assert ticket is not None
    assert ticket.credential.slot == 2


async def test_selects_next_eligible_in_order(shared):
    ledger = Ledger(shared(), config())
    await seed(ledger, credentials()[0].pool, 300)
    await seed(ledger, credentials()[1].pool, 400)
    ticket = await ledger.reserve(credentials(), 1000, 1024)
    assert ticket is not None and ticket.credential.slot == 3


async def test_two_workers_coordinate_concurrent_reservations(shared):
    workers = [Ledger(shared(), config(tpm=3000)) for _ in range(2)]
    tickets = await asyncio.gather(
        *[workers[i % 2].reserve(credentials(), 1500, 1000) for i in range(4)]
    )
    assert all(t is not None for t in tickets)
    assert sorted(t.credential.slot for t in tickets if t is not None) == [1, 2, 3, 4]
    assert await workers[0].reserve(credentials(), 1500, 1000) is None


async def test_same_organization_keys_do_not_multiply_quota(shared):
    ledger = Ledger(shared(), config(tpm=3000))
    keys = [replace(c, pool="one-organization") for c in credentials()]
    assert await ledger.reserve(keys, 1500, 1000)
    assert await ledger.reserve(keys, 1500, 1000) is None


async def test_reset_and_retry_after_use_provider_periods(shared):
    now = [1000.0]
    store = SQLiteStore(":memory:", clock=lambda: now[0])
    ledger = Ledger(store, config())
    ticket = await ledger.reserve(credentials(), 100, 100)
    assert ticket is not None
    await ledger.finish(ticket, {"retry-after": "125"}, status=429)
    now[0] += 61
    ticket = await ledger.reserve(credentials(), 100, 100)
    assert ticket is not None and ticket.credential.slot == 2
    now[0] += 65
    ticket = await ledger.reserve(credentials(), 100, 100)
    assert ticket is not None and ticket.credential.slot == 1
    await store.aclose()


async def test_unknown_and_stale_headers_never_mean_unlimited(shared):
    now = [1000.0]
    store = SQLiteStore(":memory:", clock=lambda: now[0])
    ledger = Ledger(store, config(tpm=3000))
    key = credentials()[:1]
    ticket = await ledger.reserve(key, 1500, 1000)
    assert ticket is not None
    await ledger.finish(ticket, {}, usage={"prompt_tokens": 1500, "completion_tokens": 1000})
    assert await ledger.reserve(key, 1500, 1000) is None
    now[0] += 61
    assert await ledger.reserve(key, 1500, 1000)
    await store.aclose()


async def test_actual_usage_reconciles_output_reservation(shared):
    ledger = Ledger(shared(), config(tpm=3000))
    ticket = await ledger.reserve(credentials()[:1], 1000, 1500)
    assert ticket is not None
    await ledger.finish(ticket, {}, usage={"prompt_tokens": 1000, "completion_tokens": 100})
    assert await ledger.reserve(credentials()[:1], 1000, 500)


async def test_request_and_daily_token_limits(shared):
    ledger = Ledger(shared(), config(rpm=1))
    assert await ledger.reserve(credentials()[:1], 100, 100)
    assert await ledger.reserve(credentials()[:1], 100, 100) is None
    ledger = Ledger(shared(), config(tpd=300))
    assert await ledger.reserve(credentials()[1:2], 100, 250) is None


def payload():
    return {
        "model": "openai/gpt-oss-20b",
        "messages": [
            {"role": "system", "content": "You are Zara. Reply in Urdu."},
            {"role": "user", "content": "ایک برگر کارٹ میں شامل کریں"},
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "already-completed",
                        "type": "function",
                        "function": {"name": "cart_add_item", "arguments": '{"quantity":1}'},
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "already-completed", "content": '{"quantity":1}'},
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "get_cart",
                    "description": "Get the real cart",
                    "parameters": {"type": "object"},
                },
            }
        ],
        "stream": True,
        "temperature": 0.4,
        "reasoning_effort": "low",
    }


def test_estimation_counts_system_history_user_and_tool_schemas():
    data = payload()
    full = estimate(data, config())
    assert full > estimate({"messages": data["messages"][-1:]}, config())
    assert full > estimate({"messages": data["messages"]}, config())


async def test_unexpected_429_switches_only_unstarted_request_preserving_body(shared):
    received = []

    async def provider(request):
        received.append((request.headers["authorization"], json.loads(request.content)))
        if len(received) == 1:
            return httpx.Response(429, headers={"retry-after": "60"})
        return httpx.Response(200, json={"usage": {"prompt_tokens": 100, "completion_tokens": 20}})

    transport = CapacityTransport(
        Ledger(shared(), config()), credentials(), config(), inner=httpx.MockTransport(provider)
    )
    original = payload()
    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions", json=original
        )
    assert response.status_code == 200
    assert [key for key, _ in received] == ["Bearer <key-1>", "Bearer <key-2>"]
    assert received[0][1] == received[1][1]
    for name in ("messages", "tools", "temperature", "reasoning_effort"):
        assert received[1][1][name] == original[name]


async def test_all_unavailable_never_calls_provider(shared):
    count = 0

    async def provider(request):
        nonlocal count
        count += 1
        return httpx.Response(200)

    cfg = config(tpm=10)
    transport = CapacityTransport(
        Ledger(shared(), cfg), credentials(), cfg, inner=httpx.MockTransport(provider)
    )
    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions", json=payload()
        )
    assert response.status_code == 429 and count == 0


async def test_sqlite_coordinates_separate_connections(tmp_path):
    path = str(tmp_path / "quota.sqlite3")
    stores = [SQLiteStore(path), SQLiteStore(path)]
    ledgers = [Ledger(s, config(tpm=3000)) for s in stores]
    tickets = await asyncio.gather(
        *[ledger.reserve(credentials()[:1], 1500, 1000) for ledger in ledgers]
    )
    assert sum(t is not None for t in tickets) == 1
    for store in stores:
        await store.aclose()


def test_configuration_requires_provider_approval_and_hides_keys():
    with pytest.raises(ValueError, match="approval"):
        CapacityConfig.from_env({"GROQ_CAPACITY_POOLS": "account1,account2,account3,account4"})
    cfg = CapacityConfig.from_env(
        {
            "GROQ_CAPACITY_POOLS": "account1,account2,account3,account4",
            "GROQ_CAPACITY_INDEPENDENT_APPROVED": "true",
        }
    )
    assert cfg.pools[1] == "account2"
    assert "<key-1>" not in repr(credentials()[0])
    assert "password" not in repr(config(redis_url="rediss://default:password@redis.invalid"))


async def test_cloud_has_no_local_fallback_and_preflight_sanitizes_errors():
    from foodease_agent.groq_capacity import cloud_preflight, make_store

    with pytest.raises(ValueError, match="GROQ_CAPACITY_REDIS_URL"):
        make_store(config(cloud=True), "test")
    with pytest.raises(ValueError, match="GROQ_CAPACITY_REDIS_URL"):
        await cloud_preflight(config(cloud=True), "test")
    with pytest.raises(ValueError, match="TLS"):
        CapacityConfig.from_env(
            {"FOODEASE_CLOUD_RUNTIME": "1", "GROQ_CAPACITY_REDIS_URL": "redis://redis.invalid"}
        )


async def test_request_headers_reduce_capacity_and_cannot_be_reinflated(shared):
    ledger = Ledger(shared(), config())
    await seed(ledger, credentials()[0].pool, 6000, requests=0)
    ticket = await ledger.reserve(credentials(), 100, 100)
    assert ticket is not None and ticket.credential.slot == 2


async def test_expired_snapshot_uses_learned_lower_limit():
    now = [1000.0]
    store = SQLiteStore(":memory:", clock=lambda: now[0])
    ledger = Ledger(store, config())
    ticket = await ledger.reserve(credentials()[:1], 100, 100)
    assert ticket is not None
    await ledger.finish(
        ticket,
        {
            "x-ratelimit-limit-tokens": "1000",
            "x-ratelimit-remaining-tokens": "800",
            "x-ratelimit-reset-tokens": "1s",
        },
    )
    now[0] += 61
    assert await ledger.reserve(credentials()[:1], 1000, 100) is None
    await store.aclose()


class ChunkStream(httpx.AsyncByteStream):
    def __init__(self, chunks, *, fail=False):
        self.chunks, self.fail = chunks, fail

    async def __aiter__(self):
        for chunk in self.chunks:
            yield chunk
        if self.fail:
            raise httpx.ReadError("mock stream interrupted")

    async def aclose(self):
        pass


async def test_streamed_usage_is_reconciled_even_across_split_chunks(shared):
    usage = b'data: {"x_groq":{"usage":{"prompt_tokens":100,"completion_tokens":20}}}\n\n'

    async def provider(request):
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            stream=ChunkStream([usage[:21], usage[21:], b"data: [DONE]\n\n"]),
        )

    cfg = config(tpm=2000)
    ledger = Ledger(shared(), cfg)
    transport = CapacityTransport(
        ledger, credentials()[:1], cfg, inner=httpx.MockTransport(provider)
    )
    async with httpx.AsyncClient(transport=transport) as client:
        result = await client.post(
            "https://api.groq.com/openai/v1/chat/completions", json=payload()
        )
        assert result.content == usage + b"data: [DONE]\n\n"
        assert await ledger.reserve(credentials()[:1], 900, 900)


async def test_partial_stream_is_never_retried_and_keeps_reservation(shared):
    count = 0

    async def provider(request):
        nonlocal count
        count += 1
        return httpx.Response(200, stream=ChunkStream([b'data: {"choices":[]}\n\n'], fail=True))

    cfg = config(tpm=2000)
    ledger = Ledger(shared(), cfg)
    transport = CapacityTransport(ledger, credentials(), cfg, inner=httpx.MockTransport(provider))
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(httpx.ReadError):
            await client.post("https://api.groq.com/openai/v1/chat/completions", json=payload())
        assert count == 1
        assert await ledger.reserve(credentials()[:1], 900, 900) is None


async def test_real_redis_client_coordinates_over_mock_redis_tcp_protocol():
    from foodease_agent.groq_capacity import make_store

    server = fakeredis.TcpFakeServer(("127.0.0.1", 0), server_type="redis")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    cfg = config(redis_url=f"redis://127.0.0.1:{server.server_address[1]}/0", tpm=3000)
    stores = [make_store(cfg, "test-model") for _ in range(2)]
    try:
        results = await asyncio.gather(
            *[Ledger(store, cfg).reserve(credentials()[:1], 1500, 1000) for store in stores]
        )
        assert sum(ticket is not None for ticket in results) == 1
    finally:
        for store in stores:
            await store.aclose()
        await asyncio.to_thread(server.shutdown)
        server.server_close()
        thread.join(timeout=2)


async def test_predictive_http_selection_sends_only_to_next_eligible_key(shared):
    cfg = config()
    ledger = Ledger(shared(), cfg)
    await seed(ledger, credentials()[0].pool, 100)
    seen = []

    async def provider(request):
        seen.append(request.headers["authorization"])
        return httpx.Response(200, json={"usage": {"prompt_tokens": 100, "completion_tokens": 20}})

    transport = CapacityTransport(ledger, credentials(), cfg, inner=httpx.MockTransport(provider))
    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions", json=payload()
        )
    assert response.status_code == 200
    assert seen == ["Bearer <key-2>"]  # Primary receives no HTTP request and no 429.


async def test_redis_outage_blocks_without_provider_request(shared):
    store = shared()

    async def broken(change):
        raise ConnectionError("must not expose connection details")

    store.transact = broken

    async def provider(request):
        pytest.fail("A request was sent without a reservation")

    cfg = config()
    transport = CapacityTransport(
        Ledger(store, cfg), credentials(), cfg, inner=httpx.MockTransport(provider)
    )
    async with httpx.AsyncClient(transport=transport) as client:
        result = await client.post(
            "https://api.groq.com/openai/v1/chat/completions", json=payload()
        )
        assert result.status_code == 429
        assert "connection details" not in result.text


async def test_actual_livekit_stream_keeps_context_and_uses_next_key(shared, monkeypatch):
    from livekit.agents import llm
    from livekit.agents.types import APIConnectOptions

    from foodease_agent import groq_llm
    from test_phase5_voice import _settings

    received = []

    async def provider(request):
        received.append(request.headers["authorization"])
        if len(received) == 1:
            return httpx.Response(
                429,
                json={"error": {"message": "mock quota exhausted"}},
                headers={"retry-after": "10"},
            )
        chunks = [
            b'data: {"id":"test","choices":[{"index":0,"delta":{"content":"Hello"},'
            b'"finish_reason":null}]}\n\n',
            b'data: {"id":"test","choices":[],"usage":{"prompt_tokens":100,'
            b'"completion_tokens":1,"total_tokens":101}}\n\n',
            b"data: [DONE]\n\n",
        ]
        return httpx.Response(
            200, headers={"content-type": "text/event-stream"}, stream=ChunkStream(chunks)
        )

    cfg = config(pools=tuple(c.pool for c in credentials()), independent_approved=True)
    monkeypatch.setattr(groq_llm, "make_store", lambda config, model: shared())
    monkeypatch.setattr(
        groq_llm,
        "CapacityTransport",
        lambda ledger, keys, config: CapacityTransport(
            ledger, keys, config, inner=httpx.MockTransport(provider)
        ),
    )
    model = groq_llm.CapacityGroqLLM(
        _settings(
            llm_provider="groq",
            llm_model="openai/gpt-oss-20b",
            groq_api_key="<key-1>",
            groq_api_keys=tuple(c.key for c in credentials()),
            groq_capacity=cfg,
        )
    )
    context = llm.ChatContext()
    context.add_message(role="system", content="You are Zara.")
    context.add_message(role="user", content="The cart action has already completed.")
    before = context.to_dict()
    try:
        async with model.chat(
            chat_ctx=context, conn_options=APIConnectOptions(max_retry=3)
        ) as stream:
            chunks = [chunk async for chunk in stream]
        assert "".join(c.delta.content or "" for c in chunks if c.delta) == "Hello"
        assert chunks[-1].usage is not None and chunks[-1].usage.total_tokens == 101
        assert received == ["Bearer <key-1>", "Bearer <key-2>"]
        assert context.to_dict() == before
        reader = shared()
        try:
            state = json.loads(await reader.client.get(reader.name))
            event = state[credentials()[1].pool]["events"][0]
            assert event["tokens"] == 101 and event["pending"] == 0
        finally:
            await reader.aclose()
    finally:
        await model.aclose()
