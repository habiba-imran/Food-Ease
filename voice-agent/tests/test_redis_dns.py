"""An explicit Redis resolver must preserve the URL's TLS identity and credentials."""

import ssl
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from redis.asyncio.connection import SSLConnection
from redis.exceptions import ConnectionError as RedisConnectionError

from foodease_agent.groq_capacity import CapacityConfig, RedisStore, make_store
from foodease_agent.redis_dns import ResolvedSSLConnection


@pytest.mark.parametrize("server", ["9.9.9.9", "2620:fe::fe"])
def test_resolver_setting_accepts_only_literal_addresses(server):
    config = CapacityConfig.from_env({"GROQ_CAPACITY_DNS_SERVER": server})
    assert config.dns_server == server
    with pytest.raises(ValueError, match="DNS_SERVER"):
        CapacityConfig.from_env({"GROQ_CAPACITY_DNS_SERVER": "https://example.invalid/dns"})


async def test_resolved_connection_keeps_original_sni_and_certificate_checks(monkeypatch):
    resolver = SimpleNamespace(
        resolve=AsyncMock(return_value=[SimpleNamespace(address="192.0.2.1")])
    )
    observed = []

    async def connect(connection):
        observed.append(connection._connection_arguments())

    monkeypatch.setattr(SSLConnection, "_connect", connect)
    connection = ResolvedSSLConnection(host="redis.example.invalid", resolver=resolver)
    await connection._connect()
    assert connection.host == "redis.example.invalid"
    assert observed[0]["host"] == "192.0.2.1"
    assert observed[0]["server_hostname"] == "redis.example.invalid"
    assert observed[0]["ssl"].check_hostname is True
    assert connection.check_hostname is True and connection.cert_reqs == ssl.CERT_REQUIRED
    assert connection._resolved_host is None


async def test_dns_failure_fails_closed_without_opening_socket(monkeypatch):
    resolver = SimpleNamespace(resolve=AsyncMock(side_effect=TimeoutError("private details")))
    connect = AsyncMock()
    monkeypatch.setattr(SSLConnection, "_connect", connect)
    connection = ResolvedSSLConnection(host="redis.example.invalid", resolver=resolver)
    with pytest.raises(RedisConnectionError, match="Redis DNS resolution failed") as error:
        await connection._connect()
    assert "private details" not in str(error.value)
    connect.assert_not_awaited()


async def test_store_retains_hostname_and_credentials_and_owns_custom_pool():
    config = replace(
        CapacityConfig(),
        redis_url="rediss://default:mock-secret@redis.example.invalid:6379/0",
        dns_server="9.9.9.9",
    )
    store = make_store(config, "model")
    assert isinstance(store, RedisStore)
    try:
        pool = store.client.connection_pool
        assert pool.connection_class is ResolvedSSLConnection
        assert pool.connection_kwargs["host"] == "redis.example.invalid"
        assert pool.connection_kwargs["password"] == "mock-secret"
        assert store.client.auto_close_connection_pool is True
    finally:
        await store.aclose()


async def test_certificate_failure_never_falls_back_to_another_address(monkeypatch):
    resolver = SimpleNamespace(
        resolve=AsyncMock(
            return_value=[
                SimpleNamespace(address="192.0.2.1"),
                SimpleNamespace(address="192.0.2.2"),
            ]
        )
    )
    connect = AsyncMock(side_effect=ssl.SSLCertVerificationError("mock certificate failure"))
    monkeypatch.setattr(SSLConnection, "_connect", connect)
    connection = ResolvedSSLConnection(host="redis.example.invalid", resolver=resolver)
    with pytest.raises(ssl.SSLCertVerificationError):
        await connection._connect()
    assert connect.await_count == 1
    assert connection._resolved_host is None


def test_explicit_dns_requires_tls_even_in_local_configuration():
    with pytest.raises(ValueError, match="requires TLS"):
        CapacityConfig.from_env(
            {
                "GROQ_CAPACITY_DNS_SERVER": "9.9.9.9",
                "GROQ_CAPACITY_REDIS_URL": "redis://example.invalid",
            }
        )
