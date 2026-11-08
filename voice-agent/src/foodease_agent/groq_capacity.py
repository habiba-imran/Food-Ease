"""Predictive admission at the HTTP boundary; never execute/replay application tools.

One serializable ledger per model covers all authorized organization pools. Only
quota counters and random reservation IDs enter storage, never keys or chat data.
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import math
import re
import sqlite3
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import httpx
import tiktoken
from dns.asyncresolver import Resolver
from dns.resolver import Cache
from redis.asyncio import ConnectionPool, Redis
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError
from redis.exceptions import WatchError

from foodease_agent.redis_dns import ResolvedSSLConnection

CAPACITY_ENV_VARS = tuple(
    "GROQ_CAPACITY_" + name
    for name in (
        "REDIS_URL",
        "DNS_SERVER",
        "SQLITE_PATH",
        "NAMESPACE",
        "POOLS",
        "INDEPENDENT_APPROVED",
        "OUTPUT_TOKENS",
        "SAFETY_FACTOR",
        "SAFETY_TOKENS",
        "TPM",
        "RPM",
        "RPD",
        "TPD",
        "ITPM",
        "OTPM",
        "STALE_SECONDS",
    )
)


@dataclass(frozen=True)
class CapacityConfig:
    redis_url: str = field(default="", repr=False)
    dns_server: str = ""
    sqlite_path: str = ".cache/groq-capacity.sqlite3"
    namespace: str = "foodease:groq:v1"
    pools: tuple[str, ...] = ("shared",) * 4
    independent_approved: bool = False
    output_tokens: int = 1024
    safety_factor: float = 1.2
    safety_tokens: int = 128
    tpm: int = 8000
    rpm: int = 30
    rpd: int = 1000
    tpd: int = 200000
    itpm: int = 0
    otpm: int = 0
    stale_seconds: float = 60
    cloud: bool = False

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> CapacityConfig:
        values: dict[str, Any] = {}
        for name in ("output_tokens", "safety_tokens", "tpm", "rpm", "rpd", "tpd", "itpm", "otpm"):
            raw = env.get("GROQ_CAPACITY_" + name.upper())
            if raw:
                try:
                    value = int(raw)
                except ValueError:
                    raise ValueError(f"Invalid GROQ_CAPACITY_{name.upper()}") from None
                if value < (0 if name in {"itpm", "otpm", "safety_tokens"} else 1):
                    raise ValueError(f"Invalid GROQ_CAPACITY_{name.upper()}")
                values[name] = value
        for name in ("safety_factor", "stale_seconds"):
            raw = env.get("GROQ_CAPACITY_" + name.upper())
            if raw:
                try:
                    value = float(raw)
                except ValueError:
                    raise ValueError(f"Invalid GROQ_CAPACITY_{name.upper()}") from None
                if not math.isfinite(value) or value < (1 if name == "safety_factor" else 0.1):
                    raise ValueError(f"Invalid GROQ_CAPACITY_{name.upper()}")
                values[name] = value
        pools = tuple(env.get("GROQ_CAPACITY_POOLS", "shared,shared,shared,shared").split(","))
        if len(pools) != 4 or any(not re.fullmatch(r"[\w-]{1,64}", p) for p in pools):
            raise ValueError("GROQ_CAPACITY_POOLS requires four non-secret organization labels")
        approved = env.get("GROQ_CAPACITY_INDEPENDENT_APPROVED", "false").lower() == "true"
        if env.get("GROQ_CAPACITY_INDEPENDENT_APPROVED", "false").lower() not in {"true", "false"}:
            raise ValueError("GROQ_CAPACITY_INDEPENDENT_APPROVED requires true or false")
        if len(set(pools)) > 1 and not approved:
            raise ValueError("Independent Groq pools require explicit provider approval")
        url = env.get("GROQ_CAPACITY_REDIS_URL", "").strip()
        cloud = env.get("FOODEASE_CLOUD_RUNTIME") == "1"
        if url and (
            not url.startswith(("redis://", "rediss://"))
            or (cloud and not url.startswith("rediss://"))
        ):
            raise ValueError("GROQ_CAPACITY_REDIS_URL requires Redis protocol (TLS in Cloud)")
        validate_tls_url(url)
        dns_server = env.get("GROQ_CAPACITY_DNS_SERVER", "").strip()
        if dns_server:
            try:
                ipaddress.ip_address(dns_server)
            except ValueError:
                raise ValueError("GROQ_CAPACITY_DNS_SERVER must be a resolver IP address") from None
            if url and not url.startswith("rediss://"):
                raise ValueError("An explicit Redis DNS resolver requires TLS (rediss://)")
        return cls(
            redis_url=url,
            dns_server=dns_server,
            pools=pools,
            independent_approved=approved,
            cloud=cloud,
            sqlite_path=env.get("GROQ_CAPACITY_SQLITE_PATH", cls.sqlite_path),
            namespace=env.get("GROQ_CAPACITY_NAMESPACE", cls.namespace),
            **values,
        )


@dataclass(frozen=True)
class Credential:
    slot: int
    key: str = field(repr=False)
    pool: str


@dataclass(frozen=True)
class Ticket:
    credential: Credential
    id: str


class RedisStore:
    def __init__(self, client: Redis, name: str = "foodease:groq:v1:test"):
        self.client, self.name = client, name

    async def transact(self, change: Callable) -> Any:
        async with asyncio.timeout(3):
            return await self._transact(change)

    async def _transact(self, change: Callable) -> Any:
        for _ in range(32):
            async with self.client.pipeline() as pipe:
                try:
                    await pipe.watch(self.name)
                    raw = await pipe.get(self.name)
                    seconds, micros = await pipe.time()
                    state = json.loads(raw) if raw else {}
                    result = change(state, seconds + micros / 1_000_000)
                    pipe.multi()
                    # Survives worker restarts/rolling overlap; retain > daily horizon.
                    pipe.set(self.name, json.dumps(state), ex=172800)
                    await pipe.execute()
                    return result
                except WatchError as error:
                    # redis-py also wraps a lost connection in WatchError. EXEC
                    # may already have committed: do not admit on an ambiguous retry.
                    if isinstance(error.__context__, (RedisConnectionError, RedisTimeoutError)):
                        raise RuntimeError("Redis transaction outcome unknown") from None
                    continue
        raise RuntimeError("Capacity ledger contention")

    async def aclose(self):
        await self.client.aclose()


class SQLiteStore:
    """Single-host local development, shared across processes; never Cloud fallback."""

    def __init__(self, path: str, *, clock: Callable = time.time):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path, check_same_thread=False, timeout=0.5)
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS quota (id INTEGER PRIMARY KEY, data TEXT)"
        )
        self.connection.commit()
        self.lock, self.clock = threading.Lock(), clock

    async def transact(self, change: Callable) -> Any:
        def transaction():
            with self.lock:
                try:
                    self.connection.execute("BEGIN IMMEDIATE")
                    row = self.connection.execute("SELECT data FROM quota WHERE id=1").fetchone()
                    state = json.loads(row[0]) if row else {}
                    result = change(state, self.clock())
                    self.connection.execute(
                        "INSERT OR REPLACE INTO quota VALUES(1, ?)", (json.dumps(state),)
                    )
                    self.connection.commit()
                    return result
                except BaseException:
                    self.connection.rollback()
                    raise

        return await asyncio.to_thread(transaction)

    async def aclose(self):
        self.connection.close()


def validate_tls_url(url: str):
    # redis-py URL query arguments override constructor arguments. Do not let
    # a copied URL silently turn off certificate or hostname verification.
    options = parse_qs(urlsplit(url).query, keep_blank_values=True)
    if {"ssl_cert_reqs", "ssl_check_hostname"} & options.keys():
        raise ValueError("Redis URL must not override TLS verification options")


def make_store(config: CapacityConfig, model: str):
    if config.redis_url:
        validate_tls_url(config.redis_url)
        pool = ConnectionPool.from_url(
            config.redis_url,
            socket_timeout=1,
            socket_connect_timeout=2,
            decode_responses=True,
            retry=Retry(NoBackoff(), 0),
        )
        if config.dns_server:
            if not config.redis_url.startswith("rediss://"):
                raise ValueError("An explicit Redis DNS resolver requires TLS (rediss://)")
            resolver = Resolver(configure=False)
            resolver.nameservers = [str(ipaddress.ip_address(config.dns_server))]
            resolver.cache = Cache()  # Respect authoritative TTLs; never pin an Upstash IP.
            pool.connection_class = ResolvedSSLConnection
            pool.connection_kwargs["resolver"] = resolver
        client = Redis.from_pool(pool)
        return RedisStore(client, config.namespace + ":" + model)
    if config.cloud:
        raise ValueError("Configure GROQ_CAPACITY_REDIS_URL before deploying to Cloud")
    # Separate model databases preserve each model's independent limits.
    path = config.sqlite_path + "." + re.sub(r"[^\w-]", "_", model)
    return SQLiteStore(path)


async def cloud_preflight(config: CapacityConfig, model: str):
    """Exercise two-client conflicts; not a proof of provider failover consistency."""
    if not config.cloud or not config.redis_url:
        raise ValueError("Set GROQ_CAPACITY_REDIS_URL (rediss://) before Cloud deployment")
    stores = [make_store(config, model), make_store(config, model)]
    first, second = stores
    assert isinstance(first, RedisStore) and isinstance(second, RedisStore)
    name = first.name + ":preflight:" + uuid4().hex
    first.name = second.name = name
    failed = False
    stage = "connection/authentication"
    failure_type = "unknown"
    try:
        async with asyncio.timeout(20):
            await first.client.set(name, '{"value":0}', ex=60)
            stage = "WATCH/read"
            async with first.client.pipeline() as pipe:
                await pipe.watch(name)
                if json.loads(await pipe.get(name)) != {"value": 0}:
                    raise ValueError("preflight initial state mismatch")
                await second.client.set(name, '{"value":1}', ex=60)
                stage = "conflicting EXEC"
                pipe.multi()
                pipe.set(name, '{"value":2}', ex=60)
                try:
                    await pipe.execute()
                except WatchError as error:
                    if isinstance(error.__context__, (RedisConnectionError, RedisTimeoutError)):
                        raise RuntimeError("Redis conflict check was interrupted") from None
                else:
                    raise ValueError("preflight WATCH conflict was not detected")
            stage = "cross-client visibility"
            if json.loads(await first.client.get(name)) != {"value": 1}:
                raise ValueError("preflight conflicting write was lost")
            # Positive control: conflicting EXEC must abort, but a fresh
            # transaction on either connection must still be able to commit.
            stage = "fresh transaction"
            await first.transact(lambda state, now: state.update({"value": state["value"] + 1}))
            await second.transact(lambda state, now: state.update({"value": state["value"] + 1}))
            if json.loads(await first.client.get(name)) != {"value": 3}:
                raise ValueError("preflight cross-client updates were lost")
            await first.client.set(name, "{}", ex=60)
            probe_config = replace(config, tpm=3, rpm=100, rpd=100, tpd=100, itpm=0, otpm=0)
            stage = "concurrent reservation"
            tickets = await asyncio.gather(
                *[
                    Ledger(store, probe_config).reserve(
                        [Credential(1, "<preflight>", "probe")], 1, 1
                    )
                    for store in stores
                ]
            )
            if sum(ticket is not None for ticket in tickets) != 1:
                raise ValueError("preflight concurrent reservations oversubscribed or failed")
    except Exception as error:
        failed = True
        failure_type = type(error).__name__
    finally:
        try:
            await first.client.delete(name)
        except Exception as error:
            if not failed:
                stage, failure_type = "probe cleanup", type(error).__name__
            failed = True
        finally:
            for store in stores:
                try:
                    await store.aclose()
                except Exception:
                    failed = True
    if failed:
        raise ValueError(
            f"Shared Redis preflight failed at {stage} ({failure_type}); "
            "verify TLS URL and network access"
        ) from None


def estimate(payload: dict, config: CapacityConfig) -> int:
    # o200k covers GPT-OSS text; JSON envelope plus extra framing deliberately
    # overestimates. Other model tokenizers can differ: this remains an estimate.
    text = json.dumps(
        {k: payload[k] for k in ("messages", "tools", "response_format") if k in payload},
        ensure_ascii=False,
    )
    count = len(tiktoken.get_encoding("o200k_base").encode(text, disallowed_special=()))
    framing = 64 + 12 * len(payload.get("messages", []))
    return math.ceil((count + framing) * config.safety_factor) + config.safety_tokens


def duration(raw: str | None, default: float = 60) -> float:
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        matches = re.findall(r"(\d+(?:\.\d+)?)(ms|s|m|h|d)", raw)
        if not matches or "".join(n + u for n, u in matches) != raw:
            return default
        value = sum(
            float(n) * {"ms": 0.001, "s": 1, "m": 60, "h": 3600, "d": 86400}[u] for n, u in matches
        )
    return value if math.isfinite(value) and value >= 0 else default


class Ledger:
    def __init__(self, store, config: CapacityConfig):
        self.store, self.config = store, config

    async def reserve(
        self, credentials: list[Credential], input_tokens: int, output_tokens: int
    ) -> Ticket | None:
        cfg = self.config

        def reserve(state, now):
            for credential in credentials:
                pool = state.setdefault(credential.pool, {"events": [], "headers": {}})
                events = pool["events"] = [
                    e for e in pool["events"] if now - max(e["at"], e["pending"]) < 86400
                ]
                if pool.get("blocked", 0) > now:
                    continue
                total = input_tokens + output_tokens
                limits = pool.get("limits", {})
                windows = [
                    (60, min(cfg.tpm, limits.get("tokens", cfg.tpm)), "tokens", total),
                    (60, cfg.rpm, "requests", 1),
                    (86400, min(cfg.rpd, limits.get("requests", cfg.rpd)), "requests", 1),
                    (86400, cfg.tpd, "tokens", total),
                    (60, cfg.itpm, "input", input_tokens),
                    (60, cfg.otpm, "output", output_tokens),
                ]
                if any(
                    limit
                    and sum(e[field] for e in events if now - max(e["at"], e["pending"]) < period)
                    + needed
                    > limit
                    for period, limit, field, needed in windows
                ):
                    continue
                headers = pool["headers"]
                if (
                    not headers
                    or any(now - h["seen"] > cfg.stale_seconds for h in headers.values())
                ) and any(e["pending"] > now for e in events):
                    # Cold/stale organizations get only one bounded observation
                    # request in flight, rather than a burst against unknown usage.
                    continue
                # Expired/stale snapshots fall back to bounded rolling usage,
                # never to an optimistic assumption of unlimited capacity.
                active = {k: h for k, h in headers.items() if h["reset"] > now}
                if any(h["remaining"] < (total if k == "tokens" else 1) for k, h in active.items()):
                    continue
                for k, h in active.items():
                    h["remaining"] -= total if k == "tokens" else 1
                ticket = Ticket(credential, uuid4().hex)
                events.append(
                    {
                        "id": ticket.id,
                        "at": now,
                        "started": now,
                        "pending": now + 180,
                        "tokens": total,
                        "input": input_tokens,
                        "output": output_tokens,
                        "requests": 1,
                    }
                )
                return ticket
            return None

        return await self.store.transact(reserve)

    async def finish(
        self,
        ticket: Ticket,
        headers: Mapping[str, str],
        *,
        usage: dict | None = None,
        status: int = 200,
        final: bool = True,
    ):
        headers = {k.lower(): v for k, v in headers.items()}

        def finish(state, now):
            pool = state.get(ticket.credential.pool)
            if pool is None:
                return
            event = next((e for e in pool["events"] if e["id"] == ticket.id), None)
            if event is None:
                return
            if final and status < 500:
                event["pending"] = 0
                # Charge the whole completion from settlement, conservatively
                # covering output generated after the admission minute elapsed.
                event["at"] = now
            if usage:
                event["input"] = max(0, int(usage.get("prompt_tokens", event["input"])))
                event["output"] = max(0, int(usage.get("completion_tokens", event["output"])))
                event["tokens"] = event["input"] + event["output"]
            # A definitive rejection consumed no completion tokens; keep the
            # request charge. Network/cancellation/partial streams retain budget.
            elif status in {400, 401, 403, 429}:
                event["tokens"] = event["input"] = event["output"] = 0
            for kind, horizon in (("tokens", 60), ("requests", 86400)):
                try:
                    reported_limit = int(headers["x-ratelimit-limit-" + kind])
                    if reported_limit > 0:
                        pool.setdefault("limits", {})[kind] = reported_limit
                except (KeyError, ValueError):
                    pass
                try:
                    remaining = int(headers["x-ratelimit-remaining-" + kind])
                except (KeyError, ValueError):
                    continue
                period = duration(headers.get("x-ratelimit-reset-" + kind), horizon)
                # A response snapshot may predate other in-flight admissions.
                # Deduct their entire budgets, and never raise a live ceiling
                # from out-of-order responses. This favors safety over utilization.
                pending = sum(
                    e[kind]
                    for e in pool["events"]
                    if e["id"] != ticket.id
                    and (e["pending"] > now or e["started"] >= event["started"])
                )
                remaining = max(0, remaining - pending)
                old = pool["headers"].get(kind)
                if old and old["reset"] > now:
                    remaining = min(remaining, old["remaining"])
                    period = max(period, old["reset"] - now)
                pool["headers"][kind] = {"remaining": remaining, "reset": now + period, "seen": now}
            if status == 429:
                raw = headers.get("retry-after")
                wait = duration(raw)
                if raw:
                    try:
                        wait = max(0, parsedate_to_datetime(raw).timestamp() - now)
                    except (ValueError, TypeError, OverflowError):
                        pass
                # No hint about which limit triggered? Do not probe this same
                # organization again for a full minute (or the longer hint).
                pool["blocked"] = max(pool.get("blocked", 0), now + max(1, wait))
            if status in {401, 403}:
                pool["blocked"] = max(pool.get("blocked", 0), now + 300)

        await self.store.transact(finish)


def unavailable() -> httpx.Response:
    # A normal SDK 429 activates the existing localized, nonfatal recovery path.
    return httpx.Response(
        429,
        headers={"retry-after": "60"},
        json={
            "error": {
                "message": "Zara capacity temporarily unavailable",
                "type": "rate_limit_error",
            }
        },
    )


class UsageStream(httpx.AsyncByteStream):
    def __init__(self, stream, complete, *, streaming: bool):
        self.stream, self.complete, self.streaming = stream, complete, streaming
        self.buffer = b""
        self.usage = None
        self.closed = False
        self.completed = False

    def parse(self, data: bytes):
        try:
            item = json.loads(data)
            usage = item.get("usage") or (item.get("x_groq") or {}).get("usage")
            if usage:
                self.usage = usage
        except (ValueError, AttributeError):
            pass

    async def __aiter__(self):
        # Bound live reservations even if a provider never finishes the stream.
        async with asyncio.timeout(120):
            async for chunk in self.stream:
                self.buffer += chunk
                if self.streaming:
                    while b"\n" in self.buffer:
                        line, self.buffer = self.buffer.split(b"\n", 1)
                        if line.startswith(b"data: "):
                            if line[6:].strip() == b"[DONE]":
                                # OpenAI/LiveKit stops consuming at the protocol
                                # terminator and need not request physical EOF.
                                self.completed = True
                            else:
                                self.parse(line[6:])
                if len(self.buffer) > 2_000_000:
                    self.buffer = b""  # memory bound; keep prediction if usage unavailable
                yield chunk
            if not self.streaming:
                self.parse(self.buffer)
            self.completed = True

    async def aclose(self):
        if not self.closed:
            self.closed = True
            try:
                await self.stream.aclose()
            finally:
                # Cancellation must not release tokens as if none were consumed.
                await asyncio.shield(
                    self.complete(self.usage if self.completed else None, completed=self.completed)
                )


class CapacityTransport(httpx.AsyncBaseTransport):
    def __init__(
        self,
        ledger: Ledger,
        credentials: list[Credential],
        config: CapacityConfig,
        *,
        inner: httpx.AsyncBaseTransport | None = None,
    ):
        self.ledger, self.credentials, self.config = ledger, credentials, config
        self.inner = inner or httpx.AsyncHTTPTransport(
            retries=0,
            limits=httpx.Limits(
                max_connections=50, max_keepalive_connections=50, keepalive_expiry=120
            ),
        )

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        # Never forward credentials to a different host (including redirects).
        if request.url.host != "api.groq.com" or request.url.scheme != "https":
            return httpx.Response(403)
        if request.url.path != "/openai/v1/chat/completions":
            return await self.inner.handle_async_request(request)
        data = json.loads(await request.aread())
        output = data.get("max_completion_tokens") or data.get("max_tokens")
        if output is None:
            output = self.config.output_tokens
            data["max_completion_tokens"] = output
        predicted = estimate(data, self.config)
        body = json.dumps(data, ensure_ascii=False).encode()
        eligible = self.credentials[:]
        while eligible:
            try:
                ticket = await self.ledger.reserve(eligible, predicted, int(output))
            except Exception:
                # Redis failures fail closed and never reveal connection credentials.
                return unavailable()
            if ticket is None:
                return unavailable()
            selected = ticket.credential
            eligible = [c for c in eligible if c.pool != selected.pool]
            headers = httpx.Headers(request.headers)
            headers["authorization"] = "Bearer " + selected.key
            headers["content-length"] = str(len(body))
            forwarded = httpx.Request(
                request.method,
                request.url,
                headers=headers,
                content=body,
                extensions=request.extensions,
            )
            try:
                response = await self.inner.handle_async_request(forwarded)
            except BaseException:
                await self._finish(ticket, {}, status=599)
                raise
            if response.status_code == 429:
                await response.aclose()
                await self._finish(ticket, response.headers, status=429)
                # Only retry a rejected HTTP request, before any output/tool delta.
                continue
            if response.status_code >= 400:
                await self._finish(ticket, response.headers, status=response.status_code)
                return response
            await self._finish(ticket, response.headers, final=False)

            async def complete(usage, *, completed, ticket=ticket, response=response):
                await self._finish(
                    ticket, response.headers, usage=usage, status=200 if completed else 599
                )

            response.stream = UsageStream(
                response.stream, complete, streaming=bool(data.get("stream"))
            )
            return response
        return unavailable()

    async def _finish(self, ticket, headers, **kwargs):
        try:
            await self.ledger.finish(ticket, headers, **kwargs)
        except Exception:
            # The durable reservation remains charged until its windows expire.
            # Never retry a completion just because accounting is unavailable.
            pass

    async def aclose(self):
        await self.inner.aclose()
        await self.ledger.store.aclose()
