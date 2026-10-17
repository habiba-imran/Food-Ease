"""One revision-aware action lane; caller/speech cancellation cannot cancel writes."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from foodease_contract.models import (
    READ_OPERATIONS,
    ActionRequestEvent,
    ActionResultEvent,
    assert_correlated,
)

from foodease_agent.adapters.integrated import action_request
from foodease_agent.integrated.policy import Turn, safe_failure

logger = logging.getLogger("foodease.integrated.actions")


@dataclass
class OwnedAction:
    request: ActionRequestEvent
    result: ActionResultEvent | None = None
    task: asyncio.Task | None = None
    lookup_state: str | None = None


class IntegratedActionBroker:
    def __init__(self, runtime: Any):
        self.runtime = runtime
        self.pending: dict[str, OwnedAction] = {}
        self.tasks: set[asyncio.Task] = set()
        self.results: dict[str, ActionResultEvent] = {}
        self.lock = asyncio.Lock()
        self.reconciliation_tasks: set[asyncio.Task] = set()

    def trace(self, stage: str, request: ActionRequestEvent) -> None:
        gate = self.runtime.gate
        logger.info(
            "foodease_action %s",
            json.dumps(
                {
                    "source": os.environ.get("FOODEASE_EVIDENCE_KIND", "runtime_unattested"),
                    "session_id": request.session_id,
                    "turn_id": request.turn_id,
                    "action_id": request.payload.action_id,
                    "operation": request.payload.operation,
                    "generation": gate.startup.generation if gate is not None else None,
                    "context_revision": request.context_revision,
                    "stage": stage,
                },
                ensure_ascii=True,
                separators=(",", ":"),
            ),
        )

    async def run(self, turn: Turn, operation: str, arguments: dict | Callable[[], dict]) -> dict:
        async with self.lock:
            runtime = self.runtime
            if not runtime.authorized(turn):
                return safe_failure("inactive_turn")
            mutating = operation not in READ_OPERATIONS
            if turn.steps >= 8 or mutating and turn.blocked:
                return safe_failure("step_blocked")
            if self.pending:
                return safe_failure("pending")
            try:
                fresh = await runtime.adapter.get_snapshot()
                runtime.on_context(fresh)
            except Exception:
                return safe_failure("not_available")
            if not runtime.authorized(turn) or turn.revision != fresh.revision:
                return safe_failure("stale_context")
            args = arguments if isinstance(arguments, dict) else arguments()
            if operation == "checkout.submit_demo_order":
                args = runtime.consume_confirmation(turn)
                if args is None:
                    return safe_failure("confirmation_required")
            try:
                request = action_request(fresh.session_id, turn.id, fresh.revision, operation, args)
            except (ValueError, TypeError):
                if mutating:
                    turn.blocked = True
                return safe_failure("invalid_arguments")
            key = json.dumps([operation, request.payload.arguments], sort_keys=True)
            if mutating and key in turn.effects:
                return safe_failure("step_blocked")
            owned = OwnedAction(request)
            turn.steps += 1
            if mutating:
                turn.effects.add(key)
            action_id = request.payload.action_id
            # Registration precedes task creation and the very first transport await.
            self.pending[action_id] = owned
            self.trace("registered", request)
            if operation not in READ_OPERATIONS:
                runtime.reconciler.register_pending(action_id, operation)
            owned.task = asyncio.create_task(self._execute(owned, turn))
            self.tasks.add(owned.task)
            owned.task.add_done_callback(self.tasks.discard)
            return await asyncio.shield(owned.task)

    async def _execute(self, owned: OwnedAction, turn: Turn) -> dict:
        request, runtime = owned.request, self.runtime
        if not runtime.authorized(turn):
            # The owned task may first run *after* a queued revocation. Nothing
            # has entered the transport yet, so this is a known local rejection.
            self.pending.pop(request.payload.action_id, None)
            self.trace("not_submitted", request)
            runtime.reconciler.resolve_pending(request.payload.action_id)
            return safe_failure("inactive_turn")
        try:
            result = await runtime.adapter.submit(request)
            # Even an in-process adapter must pass the production validation gate.
            result = ActionResultEvent.model_validate(result.model_dump(mode="json"))
            assert_correlated(request, result)
            if result.context_revision < request.context_revision:
                raise ValueError("regressive result")
        except Exception:
            # A transport/validation failure does not prove a rejected business write.
            outcome = await self.reconcile(owned, turn)
        else:
            if result.payload.status != "timeout_unknown":
                return await self._finish(owned, result, turn)
            outcome = await self.reconcile(owned, turn)
        if request.payload.action_id in self.pending:
            task = asyncio.create_task(self._follow_up(owned))
            self.reconciliation_tasks.add(task)
            task.add_done_callback(self.reconciliation_tasks.discard)
        return outcome

    async def _follow_up(self, owned: OwnedAction) -> None:
        # Finite read-only reconciliation, including after speech ends. No submit
        # retry and no late announcement under a newer/missing turn identity.
        for delay in (0.5, 1.5, 3.0):
            await asyncio.sleep(delay)
            if owned.request.payload.action_id not in self.pending:
                return
            await self.reconcile(owned)

    async def reconcile(self, owned: OwnedAction, turn: Turn | None = None) -> dict:
        try:
            lookup = await self.runtime.adapter.lookup(owned.request.payload.action_id)
            owned.lookup_state = lookup.state
            self.trace(f"lookup_{lookup.state}", owned.request)
            if lookup.state != "found" or lookup.result is None:
                answer = safe_failure("timeout_unknown")
                answer["recovery"] = {"state": lookup.state, "replay_allowed": False}
                answer["say"] = {
                    "not_seen": (
                        "The request is not registered yet. It may still arrive, "
                        "so I won’t send it again."
                    ),
                    "pending": (
                        "The application is still processing that request. I won’t send it again."
                    ),
                    "expired": (
                        "That outcome is no longer retained. I can’t verify whether it completed, "
                        "and won’t repeat it."
                    ),
                }.get(lookup.state, answer["say"])
                return answer
            result = ActionResultEvent.model_validate(lookup.result.model_dump(mode="json"))
            assert_correlated(owned.request, result)
            if result.payload.status == "timeout_unknown":
                return safe_failure("timeout_unknown")
            return await self._finish(owned, result, turn)
        except Exception:
            return safe_failure("timeout_unknown")

    async def _finish(
        self, owned: OwnedAction, result: ActionResultEvent, turn: Turn | None
    ) -> dict:
        runtime = self.runtime
        action_id = owned.request.payload.action_id
        owned.result = result
        self.trace(result.payload.status, owned.request)
        self.results[action_id] = result
        while len(self.results) > 64:
            del self.results[next(iter(self.results))]
        self.pending.pop(action_id, None)
        runtime.reconciler.resolve_pending(action_id)
        # A late terminal result is retained, never announced as a new request.
        if turn is None or not runtime.authorized(turn, revision=False):
            return safe_failure("inactive_turn")
        try:
            fresh = await runtime.adapter.get_snapshot()
            runtime.on_context(
                fresh, source_turn=turn.id if fresh.revision == result.context_revision else None
            )
        except Exception:
            runtime.discard_turn(turn.id)
            return safe_failure("not_available")
        if (
            not runtime.authorized(turn, revision=False)
            or fresh.revision != result.context_revision
        ):
            return safe_failure("stale_context")
        turn.revision = fresh.revision
        if result.payload.status != "success":
            turn.blocked = True
            return safe_failure(result.payload.error_code or "not_available")
        return await runtime.verified_result(turn, result, owned.request)

    async def drain(self) -> None:
        if self.tasks:
            await asyncio.gather(*(asyncio.shield(task) for task in tuple(self.tasks)))
