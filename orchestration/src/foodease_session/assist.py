"""LiveKit agent dispatch for consent-gated assistance."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Protocol

from livekit import api

logger = logging.getLogger("foodease.session.assist")


class AssistError(RuntimeError):
    """Dispatch / end failure."""


class DispatchClient(Protocol):
    async def create_dispatch(
        self, *, agent_name: str, room: str, metadata: str
    ) -> str: ...

    async def delete_dispatch(self, *, dispatch_id: str, room: str) -> None: ...


@dataclass
class LiveKitDispatchClient:
    """Thin wrapper around livekit.api AgentDispatchService."""

    url: str
    api_key: str
    api_secret: str

    def _http_url(self) -> str:
        # LiveKitAPI expects https:// host; wss:// → https://
        u = self.url.strip()
        if u.startswith("wss://"):
            return "https://" + u[len("wss://") :]
        if u.startswith("ws://"):
            return "http://" + u[len("ws://") :]
        return u

    async def create_dispatch(
        self, *, agent_name: str, room: str, metadata: str
    ) -> str:
        lk = api.LiveKitAPI(self._http_url(), self.api_key, self.api_secret)
        try:
            created = await lk.agent_dispatch.create_dispatch(
                api.CreateAgentDispatchRequest(
                    agent_name=agent_name,
                    room=room,
                    metadata=metadata,
                )
            )
            dispatch_id = str(created.id)
            logger.info(
                "dispatch_created dispatch_id=%s room=%s agent=%s",
                dispatch_id,
                room,
                agent_name,
            )
            return dispatch_id
        except Exception as exc:  # noqa: BLE001
            raise AssistError(f"CreateAgentDispatch failed: {exc}") from exc
        finally:
            await lk.aclose()

    async def delete_dispatch(self, *, dispatch_id: str, room: str) -> None:
        lk = api.LiveKitAPI(self._http_url(), self.api_key, self.api_secret)
        try:
            await lk.agent_dispatch.delete_dispatch(
                api.DeleteAgentDispatchRequest(dispatch_id=dispatch_id, room=room)
            )
            logger.info("dispatch_deleted dispatch_id=%s room=%s", dispatch_id, room)
        except Exception as exc:  # noqa: BLE001
            raise AssistError(f"DeleteAgentDispatch failed: {exc}") from exc
        finally:
            await lk.aclose()


@dataclass
class FakeDispatchClient:
    """In-memory client for unit tests."""

    created: list[dict[str, Any]]
    deleted: list[dict[str, str]]
    _n: int = 0

    def __init__(self) -> None:
        self.created = []
        self.deleted = []
        self._n = 0

    async def create_dispatch(
        self, *, agent_name: str, room: str, metadata: str
    ) -> str:
        self._n += 1
        did = f"AD_fake_{self._n}"
        self.created.append(
            {"id": did, "agent_name": agent_name, "room": room, "metadata": metadata}
        )
        return did

    async def delete_dispatch(self, *, dispatch_id: str, room: str) -> None:
        self.deleted.append({"dispatch_id": dispatch_id, "room": room})


def assist_metadata(*, session_id: str) -> str:
    return json.dumps(
        {
            "foodease.assist": True,
            "session_id": session_id,
            "schema_version": "1.0",
        }
    )


@dataclass
class AssistRegistry:
    """session_id / room → dispatch_id (demo in-memory)."""

    by_session: dict[str, str]
    by_room: dict[str, str]

    def __init__(self) -> None:
        self.by_session = {}
        self.by_room = {}

    def remember(self, *, session_id: str, room: str, dispatch_id: str) -> None:
        self.by_session[session_id] = dispatch_id
        self.by_room[room] = dispatch_id

    def resolve(self, *, session_id: str | None, room: str, dispatch_id: str | None) -> str | None:
        if dispatch_id:
            return dispatch_id
        if session_id and session_id in self.by_session:
            return self.by_session[session_id]
        return self.by_room.get(room)

    def forget(self, *, session_id: str | None, room: str, dispatch_id: str | None) -> None:
        if session_id:
            self.by_session.pop(session_id, None)
        if room in self.by_room and (
            dispatch_id is None or self.by_room.get(room) == dispatch_id
        ):
            self.by_room.pop(room, None)
