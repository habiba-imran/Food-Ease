"""Adversarial coordination tests; these do not certify a hosted Redis service."""

import asyncio
import json

import fakeredis.aioredis
import httpx
import pytest
from redis.asyncio.client import Pipeline
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import ResponseError, WatchError

from foodease_agent.groq_capacity import (
    CapacityConfig,
    CapacityTransport,
    Ledger,
    RedisStore,
    SQLiteStore,
    cloud_preflight,
)
from test_groq_capacity import ChunkStream, config, credentials, payload


def clients():
    server = fakeredis.FakeServer()
    return [fakeredis.aioredis.FakeRedis(server=server) for _ in range(2)]


async def test_forced_simultaneous_snapshots_retry_the_watch_conflict(monkeypatch):
    first, second = clients()
    stores = [RedisStore(first), RedisStore(second)]
    original_get = Pipeline.get
    released = asyncio.Event()
    reads = 0

    async def synchronized_get(pipe, name):
        nonlocal reads
        value = await original_get(pipe, name)
        reads += 1
        if reads <= 2:
            if reads == 2:
                released.set()
            await asyncio.wait_for(released.wait(), 1)
        return value

    monkeypatch.setattr(Pipeline, "get", synchronized_get)
    cfg = config(tpm=3000)
    try:
        tickets = await asyncio.gather(
            *[Ledger(store, cfg).reserve(credentials()[:1], 1500, 1000) for store in stores]
        )
        assert sum(ticket is not None for ticket in tickets) == 1
        assert reads >= 3  # A conflicting worker actually read again; no scheduling luck.
        state = json.loads(await first.get(stores[0].name))
        assert len(state[credentials()[0].pool]["events"]) == 1
    finally:
        await asyncio.gather(*(store.aclose() for store in stores))


async def test_old_and_replacement_workers_share_state_and_can_settle_each_others_ticket():
    first, replacement = clients()
    old, new = RedisStore(first), RedisStore(replacement)
    cfg = config(tpm=3000)
    before, after = Ledger(old, cfg), Ledger(new, cfg)
    ticket = await before.reserve(credentials()[:1], 1500, 1000)
    assert ticket is not None
    await old.aclose()
    try:
        assert await after.reserve(credentials()[:1], 1500, 1000) is None
        await after.finish(ticket, {}, usage={"prompt_tokens": 100, "completion_tokens": 100})
        assert await after.reserve(credentials()[:1], 1500, 1000)
    finally:
        await new.aclose()


@pytest.mark.parametrize("failure", ["timeout", "connection", "quota", "oom", "corrupt"])
async def test_database_failure_never_sends_unreserved_request(failure, monkeypatch):
    first, second = clients()
    store = RedisStore(first)

    async def broken_get(pipe, name):
        if failure == "corrupt":
            return b"not JSON"
        errors = {
            "timeout": TimeoutError(),
            "connection": RedisConnectionError("offline"),
            "quota": ResponseError("monthly command quota exceeded"),
            "oom": ResponseError("OOM write refused"),
        }
        raise errors[failure]

    monkeypatch.setattr(Pipeline, "get", broken_get)

    async def provider(request):
        pytest.fail("A provider request escaped failed shared accounting")

    cfg = config()
    transport = CapacityTransport(
        Ledger(store, cfg), credentials(), cfg, inner=httpx.MockTransport(provider)
    )
    try:
        async with httpx.AsyncClient(transport=transport) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions", json=payload()
            )
        assert response.status_code == 429
    finally:
        await second.aclose()


async def test_commit_then_lost_ack_never_allows_provider_or_refunds_the_reservation(monkeypatch):
    first, second = clients()
    store = RedisStore(first)
    original_execute = Pipeline.execute

    async def lost_ack(pipe, *args, **kwargs):
        await original_execute(pipe, *args, **kwargs)
        raise RedisConnectionError("EXEC acknowledgment lost after commit")

    monkeypatch.setattr(Pipeline, "execute", lost_ack)
    with pytest.raises(RedisConnectionError):
        await Ledger(store, config(tpm=3000)).reserve(credentials()[:1], 1500, 1000)
    monkeypatch.setattr(Pipeline, "execute", original_execute)
    try:
        assert (
            await Ledger(RedisStore(second), config(tpm=3000)).reserve(
                credentials()[:1], 1500, 1000
            )
            is None
        )
    finally:
        await first.aclose()
        await second.aclose()


async def test_database_failure_after_response_keeps_charge_without_replaying_provider(monkeypatch):
    first, second = clients()
    store = RedisStore(first)
    original_transact = store.transact
    calls = 0
    provider_calls = 0

    async def only_admission_works(change):
        nonlocal calls
        calls += 1
        if calls > 1:
            raise ResponseError("database command quota exhausted")
        return await original_transact(change)

    monkeypatch.setattr(store, "transact", only_admission_works)

    async def provider(request):
        nonlocal provider_calls
        provider_calls += 1
        return httpx.Response(200, json={"usage": {"prompt_tokens": 1, "completion_tokens": 1}})

    cfg = config(tpm=2000)
    transport = CapacityTransport(
        Ledger(store, cfg), credentials()[:1], cfg, inner=httpx.MockTransport(provider)
    )
    try:
        async with httpx.AsyncClient(transport=transport) as client:
            result = await client.post(
                "https://api.groq.com/openai/v1/chat/completions", json=payload()
            )
            assert result.status_code == 200 and provider_calls == 1
        other = RedisStore(second)
        assert await Ledger(other, cfg).reserve(credentials()[:1], 900, 900) is None
    finally:
        await second.aclose()


async def test_cancellation_during_commit_keeps_durable_charge(monkeypatch):
    first, second = clients()
    store = RedisStore(first)
    committed = asyncio.Event()
    original_execute = Pipeline.execute

    async def cancel_after_commit(pipe, *args, **kwargs):
        result = await original_execute(pipe, *args, **kwargs)
        committed.set()
        await asyncio.Event().wait()
        return result

    monkeypatch.setattr(Pipeline, "execute", cancel_after_commit)
    task = asyncio.create_task(
        Ledger(store, config(tpm=3000)).reserve(credentials()[:1], 1500, 1000)
    )
    await asyncio.wait_for(committed.wait(), 1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    monkeypatch.setattr(Pipeline, "execute", original_execute)
    try:
        assert (
            await Ledger(RedisStore(second), config(tpm=3000)).reserve(
                credentials()[:1], 1500, 1000
            )
            is None
        )
    finally:
        await first.aclose()
        await second.aclose()


async def test_redis_connection_watch_error_is_not_retried_as_a_confirmed_conflict(monkeypatch):
    first, second = clients()
    store = RedisStore(first)
    original_execute = Pipeline.execute
    calls = 0

    async def ambiguous_commit(pipe, *args, **kwargs):
        nonlocal calls
        calls += 1
        result = await original_execute(pipe, *args, **kwargs)
        if calls == 1:
            try:
                raise RedisConnectionError("lost reply")
            except RedisConnectionError as error:
                # redis-py uses WatchError for connection failures as well as
                # actual null EXEC conflict replies. Only the latter is safe to retry.
                raise WatchError("A ConnectionError occurred while watching") from error
        return result

    monkeypatch.setattr(Pipeline, "execute", ambiguous_commit)
    try:
        with pytest.raises(RuntimeError, match="unknown"):
            await Ledger(store, config(tpm=3000)).reserve(credentials()[:1], 1500, 1000)
        assert calls == 1
        state = json.loads(await second.get(store.name))
        assert len(state[credentials()[0].pool]["events"]) == 1
    finally:
        await first.aclose()
        await second.aclose()


async def test_storage_rollback_counterexample_is_not_detectable_by_connection_checks():
    """Model lost acknowledged state; this is not an observed Upstash failure."""
    first, second = clients()
    cfg = config(tpm=3000)
    old, new = RedisStore(first), RedisStore(second)
    try:
        earlier = await Ledger(old, cfg).reserve(credentials()[:1], 1500, 1000)
        assert earlier is not None
        await first.set(old.name, "{}")  # Simulate a server reverting acknowledged data.
        later = await Ledger(new, cfg).reserve(credentials()[:1], 1500, 1000)
        assert later is not None  # Over-admission: a service consistency guarantee is required.
        assert earlier.id != later.id
    finally:
        await first.aclose()
        await second.aclose()


async def test_orphan_reservation_holds_a_full_window_after_its_inflight_deadline():
    now = [1000.0]
    store = SQLiteStore(":memory:", clock=lambda: now[0])
    ledger = Ledger(store, config(tpm=3000))
    try:
        assert await ledger.reserve(credentials()[:1], 1500, 1000)
        now[0] += 181  # Simulate the reserving worker disappearing without settlement.
        assert await ledger.reserve(credentials()[:1], 1500, 1000) is None
        now[0] += 60
        assert await ledger.reserve(credentials()[:1], 1500, 1000)
    finally:
        await store.aclose()


async def test_interrupted_stream_does_not_credit_reported_usage_from_an_incomplete_response():
    now = [1000.0]
    store = SQLiteStore(":memory:", clock=lambda: now[0])
    cfg = config(tpm=2000)
    ledger = Ledger(store, cfg)

    async def provider(request):
        usage = b'data: {"usage":{"prompt_tokens":1,"completion_tokens":1}}\n\n'
        return httpx.Response(200, stream=ChunkStream([usage], fail=True))

    transport = CapacityTransport(
        ledger, credentials()[:1], cfg, inner=httpx.MockTransport(provider)
    )
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(httpx.ReadError):
            await client.post("https://api.groq.com/openai/v1/chat/completions", json=payload())
        now[0] += 61
        assert await ledger.reserve(credentials()[:1], 900, 900) is None


def test_tls_verification_cannot_be_disabled_with_a_url_query():
    for query in ("ssl_cert_reqs=none", "ssl_check_hostname=false"):
        with pytest.raises(ValueError, match="verification"):
            CapacityConfig.from_env(
                {
                    "FOODEASE_CLOUD_RUNTIME": "1",
                    "GROQ_CAPACITY_REDIS_URL": f"rediss://host.invalid?{query}",
                }
            )


async def test_preflight_demonstrates_conflict_abort_and_successful_retry(monkeypatch):
    from foodease_agent import groq_capacity

    first, second = clients()
    made = []

    def make_store(cfg, model):
        client = [first, second][len(made)]
        store = RedisStore(client)
        made.append(store)
        return store

    monkeypatch.setattr(groq_capacity, "make_store", make_store)
    await cloud_preflight(config(cloud=True, redis_url="rediss://mock.invalid"), "model")
    assert len(made) == 2  # A one-client PING/SET roundtrip cannot establish this.


async def test_preflight_rejects_an_endpoint_which_ignores_watch(monkeypatch):
    from foodease_agent import groq_capacity

    first, second = clients()
    made = []

    def make_store(cfg, model):
        store = RedisStore([first, second][len(made)])
        made.append(store)
        return store

    async def ignored_watch(pipe, *names):
        pipe.watching = True  # Client believes WATCH succeeded; server did not watch.
        return True

    monkeypatch.setattr(groq_capacity, "make_store", make_store)
    monkeypatch.setattr(Pipeline, "watch", ignored_watch)
    with pytest.raises(ValueError, match="preflight failed"):
        await cloud_preflight(config(cloud=True, redis_url="rediss://mock.invalid"), "model")
