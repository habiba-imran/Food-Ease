"""Final Phase 3 lifecycle tests. No Cloud or providers."""

from __future__ import annotations

import asyncio
import json

import pytest

from foodease_session.config import Settings
from foodease_session.lifecycle import AssistanceService, LifecycleError


class Authority:
    def __init__(self):
        self.rev = 1
        self.expired = False

    async def check(self, owner, sid):
        if owner != "owner" or sid != "shop":
            raise LifecycleError(403, "session_mismatch")
        if self.expired:
            raise LifecycleError(410, "session_expired")
        return {"session_id": sid, "revision": self.rev}


class Cloud:
    def __init__(self):
        self.created = []
        self.deleted = []
        self.rooms_deleted = []
        self.people = []
        self.dispatches = []
        self.fail_delete = False
        self.fail_create = False
        self.create_entered = asyncio.Event()
        self.release_create: asyncio.Event | None = None

    async def participants(self, room):
        return self.people

    async def create_dispatch(self, **kwargs):
        self.created.append(kwargs)
        self.create_entered.set()
        if self.release_create:
            await self.release_create.wait()
        self.dispatches.append({"id": "dispatch-1", "metadata": kwargs["metadata"]})
        if self.fail_create:
            raise RuntimeError("response lost after server create")
        return "dispatch-1"

    async def list_dispatches(self, room):
        return self.dispatches

    async def delete_dispatch(self, *, dispatch_id, room):
        if self.fail_delete:
            raise RuntimeError("transient delete failure")
        self.deleted.append(dispatch_id)
        self.dispatches = [d for d in self.dispatches if d["id"] != dispatch_id]

    async def delete_room(self, room):
        if self.fail_delete:
            raise RuntimeError("transient room failure")
        self.rooms_deleted.append(room)
        self.people = []


def settings():
    return Settings(
        "wss://example.livekit.cloud",
        "test-key",
        "test-secret-for-offline-signing-123456",
        900,
        "127.0.0.1",
        8090,
        ("http://127.0.0.1:8080",),
        1000,
        60,
        True,
        "foodease",
    )


def service():
    now = [0.0]
    authority, cloud = Authority(), Cloud()
    svc = AssistanceService(
        settings(),
        authority,
        cloud,
        clock=lambda: now[0],
        startup_ttl=10,
        idle_ttl=20,
        absolute_ttl=400,
    )
    return svc, authority, cloud, now


def seats(cloud, prepared, *, agent=False):
    roles = ["app", "user"] + (["agent"] if agent else [])
    cloud.people = [
        {
            "identity": prepared["binding"][f"{role}_identity"],
            "attributes": {
                "foodease.role": role,
                "foodease.session": "shop",
                "foodease.generation": prepared["generation"],
            },
        }
        for role in roles
    ]


def run(coro):
    return asyncio.run(coro)


def test_prepare_idempotent_one_generation_and_no_dispatch_before_readiness():
    async def case():
        svc, _, cloud, _ = service()
        first, second = await asyncio.gather(
            svc.start("owner", "shop", "request", consent=True),
            svc.start("owner", "shop", "request", consent=True),
        )
        assert first["generation"] == second["generation"]
        assert first["binding"] == second["binding"] and cloud.created == []
        assert (
            len(
                set(
                    first["binding"][key]
                    for key in ("user_identity", "app_identity", "agent_identity")
                )
            )
            == 3
        )
        with pytest.raises(LifecycleError):
            await svc.start("owner", "shop", "different", consent=True)
        with pytest.raises(LifecycleError):
            await svc.start("owner", "shop", "request", consent=False)

    run(case())


def test_readiness_requires_roles_media_playback_context_then_one_dispatch_and_worker():
    async def case():
        svc, _, cloud, _ = service()
        p = await svc.start("owner", "shop", "request", consent=True)
        for flags in ((False, True, True), (True, False, True), (True, True, False)):
            with pytest.raises(LifecycleError):
                await svc.ready("owner", "shop", "request", p["generation"], 1, *flags)
        with pytest.raises(LifecycleError):
            await svc.ready("owner", "shop", "request", p["generation"], 1, True, True, True)
        seats(cloud, p)
        ready = await svc.ready("owner", "shop", "request", p["generation"], 1, True, True, True)
        assert ready["state"] == "waiting_worker" and not ready["greeting_allowed"]
        await svc.ready("owner", "shop", "request", p["generation"], 1, True, True, True)
        assert len(cloud.created) == 1
        meta = json.loads(cloud.created[0]["metadata"])
        assert meta["transport"] == "website" and meta["binding"] == p["binding"]
        seats(cloud, p, agent=True)
        active = await svc.worker_ready(
            "shop", p["generation"], meta["worker_proof"], 1, runtime_ready=True
        )
        assert active["state"] == "active" and active["greeting_allowed"]
        ended = await svc.end("owner", "shop", "request", p["generation"])
        assert ended["state"] == "ended" and ended["dispatch_deleted"]
        assert ended["room_deleted"] and not ended["greeting_allowed"]
        assert (await svc.end("owner", "shop", "request", p["generation"])) == ended

    run(case())


def test_cancellation_before_prepare_and_during_dispatch_cannot_orphan():
    async def case():
        svc, _, cloud, _ = service()
        await svc.end("owner", "shop", "early")
        assert (await svc.start("owner", "shop", "early", consent=True))["state"] == "ended"
        assert not cloud.created
        p = await svc.start("owner", "shop", "later", consent=True)
        seats(cloud, p)
        cloud.release_create = asyncio.Event()
        pending = asyncio.create_task(
            svc.ready("owner", "shop", "later", p["generation"], 1, True, True, True)
        )
        await cloud.create_entered.wait()
        ending = asyncio.create_task(svc.end("owner", "shop", "later", p["generation"]))
        await asyncio.sleep(0)
        cloud.release_create.set()
        await pending
        assert (await ending)["state"] == "ended"
        assert cloud.deleted == ["dispatch-1"]

    run(case())


def test_failed_teardown_is_retained_blocks_restart_and_reconciles():
    async def case():
        svc, _, cloud, _ = service()
        p = await svc.start("owner", "shop", "request", consent=True)
        seats(cloud, p)
        await svc.ready("owner", "shop", "request", p["generation"], 1, True, True, True)
        cloud.fail_delete = True
        failed = await svc.end("owner", "shop", "request", p["generation"])
        assert failed["state"] == "cleanup_pending" and not failed["dispatch_deleted"]
        with pytest.raises(LifecycleError):
            await svc.start("owner", "shop", "new", consent=True)
        cloud.fail_delete = False
        assert (await svc.end("owner", "shop", "request", p["generation"]))["state"] == "ended"
        assert cloud.deleted == ["dispatch-1"]

    run(case())


def test_create_response_loss_is_reconciled_without_second_dispatch():
    async def case():
        svc, _, cloud, _ = service()
        p = await svc.start("owner", "shop", "request", consent=True)
        seats(cloud, p)
        cloud.fail_create = True
        result = await svc.ready("owner", "shop", "request", p["generation"], 1, True, True, True)
        assert result["state"] in {"ended", "cleanup_pending"}
        assert len(cloud.created) == 1
        await svc.sweep()
        assert cloud.deleted == ["dispatch-1"]

    run(case())


def test_expiry_missing_worker_disconnect_and_wrong_identity_preserve_manual_state():
    async def case():
        svc, authority, cloud, now = service()
        p = await svc.start("owner", "shop", "request", consent=True)
        with pytest.raises(LifecycleError):
            await svc.end("intruder", "shop", "request", p["generation"])
        seats(cloud, p)
        await svc.ready("owner", "shop", "request", p["generation"], 1, True, True, True)
        with pytest.raises(LifecycleError):
            await svc.worker_ready("shop", p["generation"], "forged", 1, runtime_ready=True)
        now[0] = 10
        await svc.sweep()
        assert (await svc.status("owner", "shop", "request"))["state"] == "ended"
        assert authority.rev == 1 and cloud.deleted == ["dispatch-1"]

    run(case())


def test_active_disconnect_expiry_refresh_and_old_end_cannot_end_new_generation():
    async def case():
        svc, authority, cloud, now = service()
        p = await svc.start("owner", "shop", "one", consent=True)
        seats(cloud, p)
        await svc.ready("owner", "shop", "one", p["generation"], 1, True, True, True)
        seats(cloud, p, agent=True)
        proof = json.loads(cloud.created[0]["metadata"])["worker_proof"]
        await svc.worker_ready("shop", p["generation"], proof, 1, runtime_ready=True)
        now[0] = 15
        refreshed = await svc.refresh("owner", "shop", "one", p["generation"], consent=True)
        assert refreshed["binding"] == p["binding"] and len(cloud.created) == 1
        cloud.people = [p for p in cloud.people if p["attributes"]["foodease.role"] != "user"]
        await svc.sweep()
        assert (await svc.status("owner", "shop", "one"))["state"] == "ended"
        second = await svc.start("owner", "shop", "two", consent=True)
        await svc.end("owner", "shop", "one", p["generation"])
        assert (await svc.status("owner", "shop", "two"))["state"] == "preparing"
        assert second["generation"] != p["generation"] and authority.rev == 1

    run(case())


def test_wrong_role_or_stale_context_does_not_dispatch():
    async def case():
        svc, authority, cloud, _ = service()
        p = await svc.start("owner", "shop", "request", consent=True)
        seats(cloud, p)
        cloud.people[0]["attributes"]["foodease.role"] = "user"
        with pytest.raises(LifecycleError, match="binding"):
            await svc.ready("owner", "shop", "request", p["generation"], 1, True, True, True)
        seats(cloud, p)
        authority.rev = 2
        with pytest.raises(LifecycleError, match="fresh_context"):
            await svc.ready("owner", "shop", "request", p["generation"], 1, True, True, True)
        assert not cloud.created

    run(case())


def test_unresolved_create_is_not_claimed_ended_and_never_retried():
    async def case():
        svc, _, cloud, _ = service()

        async def lost(**kwargs):
            cloud.created.append(kwargs)
            raise TimeoutError()

        cloud.create_dispatch = lost
        p = await svc.start("owner", "shop", "request", consent=True)
        seats(cloud, p)
        result = await svc.ready("owner", "shop", "request", p["generation"], 1, True, True, True)
        assert result["state"] == "cleanup_pending" and not result["dispatch_deleted"]
        await svc.sweep()
        assert len(cloud.created) == 1
        with pytest.raises(LifecycleError):
            await svc.start("owner", "shop", "different", consent=True)

    run(case())


def test_cancelled_http_request_does_not_cancel_dispatch_ownership():
    async def case():
        svc, _, cloud, _ = service()
        cloud.release_create = asyncio.Event()
        p = await svc.start("owner", "shop", "request", consent=True)
        seats(cloud, p)
        task = asyncio.create_task(
            svc.ready("owner", "shop", "request", p["generation"], 1, True, True, True)
        )
        await cloud.create_entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        ending = asyncio.create_task(svc.end("owner", "shop", "request", p["generation"]))
        cloud.release_create.set()
        assert (await ending)["state"] == "ended"
        assert cloud.deleted == ["dispatch-1"]

    run(case())


@pytest.mark.parametrize("expiry", ["idle", "absolute", "shopping"])
def test_active_generation_expires_and_cannot_refresh_or_greet(expiry):
    async def case():
        svc, authority, cloud, now = service()
        p = await svc.start("owner", "shop", "request", consent=True)
        seats(cloud, p)
        await svc.ready("owner", "shop", "request", p["generation"], 1, True, True, True)
        seats(cloud, p, agent=True)
        proof = json.loads(cloud.created[0]["metadata"])["worker_proof"]
        await svc.worker_ready("shop", p["generation"], proof, 1, runtime_ready=True)
        if expiry == "shopping":
            authority.expired = True
        else:
            now[0] = 400 if expiry == "absolute" else 20
        await svc.sweep()
        status = await svc.status("owner", "shop", "request")
        assert status["state"] == "ended" and not status["greeting_allowed"]
        assert cloud.deleted == ["dispatch-1"]
        with pytest.raises(LifecycleError):
            await svc.refresh("owner", "shop", "request", p["generation"], consent=True)

    run(case())


def test_livekit_wrapper_uses_installed_delete_signature_and_not_found_room(monkeypatch):
    from types import SimpleNamespace

    from livekit import api

    from foodease_session.assist import LiveKitDispatchClient

    async def case():
        calls = []

        async def delete_dispatch(dispatch_id, room):
            calls.append((dispatch_id, room))

        async def delete_room(request):
            raise api.TwirpError(code="not_found", msg="room absent", status=404)

        async def close():
            calls.append("closed")

        client = SimpleNamespace(
            agent_dispatch=SimpleNamespace(delete_dispatch=delete_dispatch),
            room=SimpleNamespace(delete_room=delete_room),
            aclose=close,
        )
        monkeypatch.setattr(api, "LiveKitAPI", lambda *args: client)
        wrapper = LiveKitDispatchClient("wss://example.livekit.cloud", "test", "fake")
        await wrapper.delete_dispatch(dispatch_id="did", room="foodease-v2-room")
        await wrapper.delete_room("foodease-v2-room")
        assert calls == [("did", "foodease-v2-room"), "closed", "closed"]

    run(case())
