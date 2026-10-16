"""Bounded, process-local shopping authority. No provider or transport dependency.

One action lock per session serializes copy/validate/commit. The separate record
lock permits read-only status lookup while execution is pending. Accepted action
IDs are retained for the session lifetime; capacity rejects new work, never evicts
an earlier outcome. A restart deliberately expires all attachments and results.
"""

from __future__ import annotations

import copy
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Event, RLock
from typing import Any

from foodease_contract.models import (
    ActionRequestEvent,
    ActionResultEvent,
    ContextSnapshot,
    LookupResponse,
    assert_correlated,
    request_fingerprint,
)

from foodease_website.catalog import CatalogSeed
from foodease_website.domain import FoodEaseDomain


class SessionError(Exception):
    def __init__(self, status: int, code: str) -> None:
        self.status = status
        self.code = code
        super().__init__(code)


@dataclass
class ActionRecord:
    fingerprint: str
    done: Event = field(default_factory=Event)
    result: ActionResultEvent | None = None


@dataclass
class ShoppingSession:
    session_id: str
    owner: str
    created: float
    touched: float
    domain: FoodEaseDomain
    actions: dict[str, ActionRecord] = field(default_factory=dict)
    action_lock: Any = field(default_factory=RLock)
    records_lock: Any = field(default_factory=RLock)


def timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class SessionStore:
    def __init__(
        self,
        catalog: CatalogSeed,
        *,
        clock: Callable[[], float] = time.monotonic,
        idle_ttl: float = 1800,
        absolute_ttl: float = 7200,
        max_sessions: int = 128,
        max_actions: int = 256,
        confirmation_ttl: float = 300,
    ) -> None:
        if min(idle_ttl, absolute_ttl, max_sessions, max_actions, confirmation_ttl) <= 0:
            raise ValueError("Session limits must be positive")
        self.catalog, self.clock = catalog, clock
        self.idle_ttl, self.absolute_ttl = idle_ttl, absolute_ttl
        self.max_sessions, self.max_actions = max_sessions, max_actions
        self.confirmation_ttl = confirmation_ttl
        self._sessions: dict[str, ShoppingSession] = {}
        self._owners: dict[str, float] = {}
        self._defaults: dict[str, str] = {}
        self._registry_lock = RLock()

    def _expired(self, session: ShoppingSession) -> bool:
        now = self.clock()
        return now - session.touched >= self.idle_ttl or now - session.created >= self.absolute_ttl

    def _cleanup(self) -> None:
        for sid, session in list(self._sessions.items()):
            with session.records_lock:
                busy = any(not record.done.is_set() for record in session.actions.values())
            if self._expired(session) and not busy:
                del self._sessions[sid]
        self._owners = {
            owner: created
            for owner, created in self._owners.items()
            if self.clock() - created < self.absolute_ttl
        }
        self._defaults = {
            owner: sid
            for owner, sid in self._defaults.items()
            if owner in self._owners and sid in self._sessions
        }

    def new_owner(self) -> str:
        with self._registry_lock:
            self._cleanup()
            if len(self._owners) >= self.max_sessions * 2:
                raise SessionError(429, "capacity_reached")
            owner = secrets.token_urlsafe(32)
            self._owners[owner] = self.clock()
            return owner

    def authorize_owner(self, owner: str | None) -> str:
        with self._registry_lock:
            if not owner:
                raise SessionError(401, "owner_required")
            created = self._owners.get(owner)
            if created is None or self.clock() - created >= self.absolute_ttl:
                raise SessionError(410, "session_expired")
            return owner

    def create(self, owner: str) -> ShoppingSession:
        with self._registry_lock:
            self.authorize_owner(owner)
            self._cleanup()
            if len(self._sessions) >= self.max_sessions:
                raise SessionError(429, "capacity_reached")
            sid = secrets.token_urlsafe(24)
            now = self.clock()
            session = ShoppingSession(
                sid,
                owner,
                now,
                now,
                FoodEaseDomain(
                    self.catalog,
                    session_id=sid,
                    clock=self.clock,
                    confirmation_ttl=self.confirmation_ttl,
                ),
            )
            self._sessions[sid] = session
            return session

    def _get(self, owner: str, sid: str, *, touch: bool = True) -> ShoppingSession:
        with self._registry_lock:
            self.authorize_owner(owner)
            session = self._sessions.get(sid)
            if session is None:
                raise SessionError(410, "session_expired")
            if session.owner != owner:
                raise SessionError(403, "session_mismatch")
            if self._expired(session):
                raise SessionError(410, "session_expired")
            if touch:
                session.touched = self.clock()
            return session

    def attach(self, owner: str, sid: str) -> ShoppingSession:
        return self._get(owner, sid)

    def default(self, owner: str) -> ShoppingSession:
        """Compatibility for older manual clients; browser tabs send an explicit ID."""
        with self._registry_lock:
            self.authorize_owner(owner)
            sid = self._defaults.get(owner)
            if sid:
                return self._get(owner, sid)
            session = self.create(owner)
            self._defaults[owner] = session.session_id
            return session

    def context(self, owner: str, sid: str) -> dict[str, Any]:
        session = self._get(owner, sid)
        with session.action_lock:
            self._get(owner, sid)
            return ContextSnapshot.model_validate(session.domain.snapshot()).model_dump(mode="json")

    @staticmethod
    def _result(request: ActionRequestEvent, revision: int, payload: dict) -> ActionResultEvent:
        return ActionResultEvent.model_validate(
            {
                "schema_version": "2.0",
                "session_id": request.session_id,
                "event_id": secrets.token_urlsafe(18),
                "turn_id": request.turn_id,
                "timestamp": timestamp(),
                "context_revision": revision,
                "type": "app.action_result",
                "reply_to": request.event_id,
                "payload": {"operation": request.payload.operation, **payload},
            }
        )

    def submit(self, owner: str, sid: str, raw: dict) -> ActionResultEvent:
        request = ActionRequestEvent.model_validate(raw)
        session = self._get(owner, sid)
        if request.session_id != sid:
            raise SessionError(403, "session_mismatch")
        fingerprint = request_fingerprint(sid, request.payload)
        action_id = request.payload.action_id
        with session.records_lock:
            record = session.actions.get(action_id)
            if record is not None and record.fingerprint != fingerprint:
                return self._result(
                    request,
                    session.domain.revision,
                    {
                        "action_id": action_id,
                        "status": "rejected",
                        "error_code": "idempotency_conflict",
                    },
                )
            duplicate = record is not None
            if record is None:
                if len(session.actions) >= self.max_actions:
                    raise SessionError(429, "action_capacity_reached")
                record = ActionRecord(fingerprint)
                session.actions[action_id] = record
        if duplicate:
            if not record.done.wait(5):
                return self._result(
                    request,
                    session.domain.revision,
                    {
                        "action_id": action_id,
                        "status": "timeout_unknown",
                        "error_code": "timeout",
                    },
                )
            assert record.result is not None
            return record.result.model_copy(deep=True)

        with session.action_lock:
            try:
                # Recheck lifetime after queueing; do not mutate an expired session.
                self._get(owner, sid)
                candidate = copy.deepcopy(session.domain)
                raw_result = candidate.execute_action(
                    action_id,
                    request.payload.operation,
                    request.payload.arguments,
                    context_revision=request.context_revision,
                )
                result = self._result(request, candidate.revision, raw_result)
                assert_correlated(request, result)
                ContextSnapshot.model_validate(candidate.snapshot())
                with session.records_lock:
                    session.domain = candidate
                    record.result = result
                    record.done.set()
            except Exception:
                # Domain code is local and effect-free outside this candidate. Do not
                # expose exception text or commit a partially mutated candidate.
                result = self._result(
                    request,
                    session.domain.revision,
                    {
                        "action_id": action_id,
                        "status": "failed",
                        "error_code": "internal",
                    },
                )
                with session.records_lock:
                    record.result = result
                    record.done.set()
            return result.model_copy(deep=True)

    def lookup(self, owner: str, sid: str, action_id: str, event_id: str) -> LookupResponse:
        # Does not touch idle lifetime, execute actions, or change domain revision.
        try:
            session = self._get(owner, sid, touch=False)
        except SessionError as exc:
            if exc.status != 410:
                raise
            self.authorize_owner(owner)
            session = None
        state, result = "expired", None
        if session is not None:
            with session.records_lock:
                record = session.actions.get(action_id)
                state = "not_seen" if record is None else "pending"
                if record is not None and record.result is not None:
                    state, result = "found", record.result.model_dump(mode="json")
        return LookupResponse.model_validate(
            {
                "schema_version": "2.0",
                "session_id": sid,
                "event_id": secrets.token_urlsafe(18),
                "reply_to": event_id,
                "timestamp": timestamp(),
                "action_id": action_id,
                "state": state,
                "result": result,
            }
        )
