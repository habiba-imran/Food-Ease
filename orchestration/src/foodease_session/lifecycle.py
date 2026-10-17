"""Shopping-bound assistance generations. State is process-local and bounded.

No shopping writes. Dispatch creation is never blindly retried. Cancellation marks
the generation before awaiting remote I/O; owned tasks survive HTTP cancellation.
Failed/uncertain teardown remains observable and blocks a replacement worker.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx
from foodease_contract.models import ContextSnapshot
from foodease_contract.startup import StartupBinding

from foodease_session.config import Settings
from foodease_session.mint import mint_token

logger = logging.getLogger("foodease.session.lifecycle")


def trace(record: Generation, stage: str, dispatch_id: str | None = None) -> None:
    logger.info(
        "foodease_lifecycle %s",
        json.dumps(
            {
                "source": os.environ.get("FOODEASE_EVIDENCE_KIND", "runtime_unattested"),
                "session_id": record.startup.binding.session_id,
                "request_id": record.startup.request_id,
                "generation": record.startup.generation,
                "stage": stage,
                "dispatch_id": dispatch_id,
            },
            ensure_ascii=True,
            separators=(",", ":"),
        ),
    )


class LifecycleError(Exception):
    def __init__(self, status: int, code: str):
        self.status, self.code = status, code
        super().__init__(code)


class ShoppingAuthority(Protocol):
    async def check(self, owner: str, sid: str, /) -> dict[str, Any]: ...


class RoomCloud(Protocol):
    async def participants(self, room: str) -> list[dict[str, Any]]: ...
    async def create_dispatch(self, *, agent_name: str, room: str, metadata: str) -> str: ...
    async def list_dispatches(self, room: str) -> list[dict[str, Any]]: ...
    async def delete_dispatch(self, *, dispatch_id: str, room: str) -> None: ...
    async def delete_room(self, room: str) -> None: ...


class HttpShoppingAuthority:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def check(self, owner: str, sid: str) -> dict[str, Any]:
        if not owner:
            raise LifecycleError(401, "owner_required")
        try:
            async with httpx.AsyncClient(
                timeout=3, trust_env=False, follow_redirects=False
            ) as client:
                response = await client.get(
                    f"{self.base_url}/api/v2/app/context",
                    headers={"X-FoodEase-Session": sid, "Cookie": f"foodease_owner={owner}"},
                )
            if response.status_code in {401, 403, 410}:
                raise LifecycleError(response.status_code, "shopping_session_unavailable")
            response.raise_for_status()
            snapshot = ContextSnapshot.model_validate(response.json())
            if snapshot.session_id != sid:
                raise ValueError("session mismatch")
            return snapshot.model_dump(mode="json")
        except LifecycleError:
            raise
        except Exception:
            raise LifecycleError(503, "shopping_authority_unavailable") from None


@dataclass
class Generation:
    owner: str
    startup: StartupBinding
    room: str
    created: float
    touched: float
    state: str = "preparing"
    cancelled: bool = False
    dispatch_ids: set[str] = field(default_factory=set)
    create_started: bool = False
    create_known: bool = False
    dispatch_deleted: bool = True
    room_deleted: bool = False
    reason: str | None = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    task: asyncio.Task | None = None


class AssistanceService:
    def __init__(
        self,
        settings: Settings,
        authority: ShoppingAuthority,
        cloud: RoomCloud,
        *,
        clock: Callable[[], float] = time.monotonic,
        startup_ttl: float = 30,
        idle_ttl: float = 1800,
        absolute_ttl: float = 7200,
        max_records: int = 512,
        remote_timeout: float = 5,
    ):
        self.settings, self.authority, self.cloud = settings, authority, cloud
        self.clock, self.startup_ttl = clock, startup_ttl
        self.idle_ttl, self.absolute_ttl = idle_ttl, absolute_ttl
        self.max_records, self.remote_timeout = max_records, remote_timeout
        self.records: dict[tuple[str, str], Generation] = {}
        self.current: dict[str, Generation] = {}

    def _new(self, owner: str, sid: str, request_id: str) -> Generation:
        # No await between checking/admitting a generation (single event loop).
        now = self.clock()
        for key, record in list(self.records.items()):
            if record.state == "ended" and now - record.created >= self.absolute_ttl:
                del self.records[key]
                if self.current.get(key[0]) is record:
                    del self.current[key[0]]
        if len(self.records) >= self.max_records:
            raise LifecycleError(429, "assistance_capacity_reached")
        generation = secrets.token_urlsafe(18)
        startup = StartupBinding.model_validate(
            {
                "schema_version": "2.0",
                "transport": "website",
                "consent": True,
                "generation": generation,
                "request_id": request_id,
                "worker_proof": secrets.token_urlsafe(32),
                "binding": {
                    "session_id": sid,
                    **{
                        f"{role}_identity": f"{role}-{generation}"
                        for role in ("app", "user", "agent")
                    },
                },
            }
        )
        record = Generation(owner, startup, f"foodease-v2-{secrets.token_hex(12)}", now, now)
        self.records[sid, request_id] = record
        trace(record, "prepared")
        return record

    def _owned(
        self, owner: str, sid: str, request_id: str, generation: str | None = None
    ) -> Generation:
        record = self.records.get((sid, request_id))
        if record is None:
            raise LifecycleError(410, "generation_unavailable")
        if not owner or not secrets.compare_digest(owner.encode(), record.owner.encode()):
            raise LifecycleError(403, "session_mismatch")
        if generation is not None and generation != record.startup.generation:
            raise LifecycleError(409, "generation_mismatch")
        return record

    def _expired(self, record: Generation) -> bool:
        now = self.clock()
        return (
            now - record.created >= self.absolute_ttl
            or now - record.touched >= self.idle_ttl
            or record.state in {"preparing", "dispatching", "waiting_worker"}
            and now - record.created >= self.startup_ttl
        )

    def _view(self, record: Generation, *, credentials: bool = False) -> dict[str, Any]:
        result = {
            "schema_version": "2.0",
            "session_id": record.startup.binding.session_id,
            "request_id": record.startup.request_id,
            "generation": record.startup.generation,
            "binding": record.startup.binding.model_dump(mode="json"),
            "room": record.room,
            "state": record.state,
            "reason": record.reason,
            "greeting_allowed": record.state == "active" and not record.cancelled,
            "dispatch_deleted": record.dispatch_deleted,
            "room_deleted": record.room_deleted,
            "cart_preserved": True,
        }
        if credentials and not record.cancelled and record.state != "ended":
            ttl = min(
                self.settings.token_ttl_seconds,
                int(self.absolute_ttl - (self.clock() - record.created)),
            )
            if ttl < 60:
                raise LifecycleError(410, "token_refresh_requires_new_session")
            result.update(
                livekit_url=self.settings.livekit_url,
                ttl_seconds=ttl,
                transport="website",
                tokens={},
            )
            for role in ("app", "user"):
                identity = getattr(record.startup.binding, f"{role}_identity")
                result["tokens"][role] = {
                    "identity": identity,
                    "role": role,
                    "token": mint_token(
                        api_key=self.settings.livekit_api_key,
                        api_secret=self.settings.livekit_api_secret,
                        role=role,
                        room=record.room,
                        identity=identity,
                        ttl_seconds=ttl,
                        session_id=record.startup.binding.session_id,
                        generation=record.startup.generation,
                    ),
                }
        return result

    async def start(self, owner: str, sid: str, request_id: str, *, consent: bool) -> dict:
        if consent is not True:
            raise LifecycleError(403, "consent_required")
        await self.authority.check(owner, sid)
        record = self.records.get((sid, request_id))
        if record is not None:
            record = self._owned(owner, sid, request_id)
            if self._expired(record) and not record.cancelled:
                await self._stop(record, "expired")
            return self._view(record, credentials=True)
        active = self.current.get(sid)
        if active is not None and active.state != "ended":
            raise LifecycleError(409, "assistance_already_exists")
        if not self.settings.livekit_agent_dispatch:
            raise LifecycleError(503, "integrated_dispatch_disabled")
        record = self._new(owner, sid, request_id)
        self.current[sid] = record
        return self._view(record, credentials=True)

    async def _seats(self, record: Generation, *, agent: bool = False) -> None:
        try:
            people = await asyncio.wait_for(
                self.cloud.participants(record.room), self.remote_timeout
            )
        except Exception:
            raise LifecycleError(503, "room_readiness_unavailable") from None
        for role in ["app", "user"] + (["agent"] if agent else []):
            identity = getattr(record.startup.binding, f"{role}_identity")
            matching = [p for p in people if p["identity"] == identity]
            if len(matching) != 1:
                raise LifecycleError(409, f"{role}_seat_missing")
            attrs = matching[0]["attributes"]
            if (
                attrs.get("foodease.role") != role
                or attrs.get("foodease.session") != record.startup.binding.session_id
                or attrs.get("foodease.generation") != record.startup.generation
            ):
                raise LifecycleError(403, "participant_binding_mismatch")

    async def ready(
        self,
        owner: str,
        sid: str,
        request_id: str,
        generation: str,
        revision: int,
        media_ready: bool,
        playback_ready: bool,
        app_ready: bool,
    ) -> dict:
        record = self._owned(owner, sid, request_id, generation)
        snapshot = await self.authority.check(owner, sid)
        if not all(flag is True for flag in (media_ready, playback_ready, app_ready)):
            raise LifecycleError(409, "readiness_required")
        if snapshot["revision"] != revision:
            raise LifecycleError(409, "fresh_context_required")
        if self._expired(record):
            await self._stop(record, "readiness_timeout")
        if record.cancelled:
            return self._view(record)
        await self._seats(record)
        # Seats/authority checks awaited: recheck cancellation before starting I/O.
        if record.cancelled:
            return self._view(record)
        if record.task is None:
            record.task = asyncio.create_task(self._create(record))
        await asyncio.shield(record.task)
        return self._view(record)

    async def _create(self, record: Generation) -> None:
        async with record.lock:
            if record.cancelled or record.create_started:
                return
            record.state, record.create_started = "dispatching", True
            record.dispatch_deleted = False
            try:
                did = await asyncio.wait_for(
                    self.cloud.create_dispatch(
                        agent_name=self.settings.foodease_agent_name,
                        room=record.room,
                        metadata=record.startup.model_dump_json(),
                    ),
                    self.remote_timeout,
                )
                record.dispatch_ids.add(did)
                trace(record, "dispatched", did)
                record.create_known = True
                record.state = "waiting_worker"
            except Exception:
                record.cancelled, record.reason = True, "dispatch_outcome_unknown"
            if record.cancelled:
                await self._cleanup_locked(record)

    async def worker_ready(
        self, sid: str, generation: str, proof: str, revision: int, *, runtime_ready: bool
    ) -> dict:
        record = self.current.get(sid)
        if (
            record is None
            or generation != record.startup.generation
            or not secrets.compare_digest(proof.encode(), record.startup.worker_proof.encode())
        ):
            raise LifecycleError(403, "unauthorized_worker")
        snapshot = await self.authority.check(record.owner, sid)
        if not runtime_ready:
            await self._stop(record, "integrated_runtime_unavailable")
            return self._view(record)
        if self._expired(record):
            await self._stop(record, "readiness_timeout")
        if record.cancelled:
            return self._view(record)
        if record.state not in {"waiting_worker", "active"}:
            raise LifecycleError(409, "dispatch_not_ready")
        if revision != snapshot["revision"]:
            raise LifecycleError(409, "fresh_context_required")
        await self._seats(record, agent=True)
        if not record.cancelled:
            record.state, record.touched = "active", self.clock()
            trace(record, "active")
        return self._view(record)

    async def _cleanup_locked(self, record: Generation) -> None:
        record.state = "cleanup_pending"
        try:
            dispatches = (
                (
                    await asyncio.wait_for(
                        self.cloud.list_dispatches(record.room), self.remote_timeout
                    )
                )
                if record.create_started
                else []
            )
            for item in dispatches:
                if item.get("metadata") == record.startup.model_dump_json():
                    record.dispatch_ids.add(item["id"])
                    record.create_known = True
            # Positive discovery resolves a lost creation response. An empty list
            # alone cannot resolve an unknown create that may still complete later.
            for did in list(record.dispatch_ids):
                if any(item["id"] == did for item in dispatches):
                    await asyncio.wait_for(
                        self.cloud.delete_dispatch(dispatch_id=did, room=record.room),
                        self.remote_timeout,
                    )
                record.dispatch_ids.remove(did)
            record.dispatch_deleted = not record.create_started or record.create_known
        except Exception:
            record.dispatch_deleted = False
        try:
            await asyncio.wait_for(self.cloud.delete_room(record.room), self.remote_timeout)
            record.room_deleted = True
        except Exception:
            record.room_deleted = False
        if record.dispatch_deleted and record.room_deleted:
            record.state = "ended"
        trace(record, record.state)

    async def _stop(self, record: Generation, reason: str) -> None:
        record.cancelled = True
        record.reason = record.reason or reason
        async with record.lock:
            if record.state != "ended":
                await self._cleanup_locked(record)

    async def end(
        self, owner: str, sid: str, request_id: str, generation: str | None = None
    ) -> dict:
        record = self.records.get((sid, request_id))
        if record is None:
            if generation is not None:
                raise LifecycleError(410, "generation_unavailable")
            # Cancel may overtake a slow prepare. Retain a tombstone, so the late
            # prepare cannot create a new generation after manual was selected.
            await self.authority.check(owner, sid)
            record = self.records.get((sid, request_id)) or self._new(owner, sid, request_id)
        record = self._owned(owner, sid, request_id, generation)
        await self._stop(record, "ended_by_user")
        return self._view(record)

    async def status(self, owner: str, sid: str, request_id: str) -> dict:
        record = self._owned(owner, sid, request_id)
        if not record.cancelled:
            try:
                await self.authority.check(owner, sid)
                if self._expired(record):
                    await self._stop(record, "expired")
            except LifecycleError:
                await self._stop(record, "shopping_session_unavailable")
        return self._view(record)

    async def refresh(
        self, owner: str, sid: str, request_id: str, generation: str, *, consent: bool
    ) -> dict:
        record = self._owned(owner, sid, request_id, generation)
        await self.authority.check(owner, sid)
        if consent is not True or record.cancelled or self._expired(record):
            await self._stop(record, "refresh_refused")
            raise LifecycleError(410, "generation_expired")
        record.touched = self.clock()
        return self._view(record, credentials=True)

    async def sweep(self) -> None:
        for record in list(self.records.values()):
            if record.state == "ended":
                continue
            if record.cancelled or self._expired(record):
                await self._stop(record, "expired")
            elif record.state == "active":
                try:
                    await self.authority.check(record.owner, record.startup.binding.session_id)
                    await self._seats(record, agent=True)
                except Exception:
                    await self._stop(record, "seat_disconnected_or_authority_unavailable")

    async def close(self) -> None:
        await asyncio.gather(
            *(self._stop(record, "server_shutdown") for record in list(self.records.values()))
        )
