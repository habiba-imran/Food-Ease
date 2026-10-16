"""Versioned, owner-bound lifecycle routes. Room/dispatch IDs are never inputs."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, Request
from foodease_contract.models import Id, Model, Revision
from pydantic import StrictBool

from foodease_session.lifecycle import AssistanceService, LifecycleError


class Start(Model):
    request_id: Id
    consent: StrictBool


class End(Model):
    request_id: Id
    generation: Id | None = None


class Bound(Model):
    request_id: Id
    generation: Id


class Ready(Bound):
    context_revision: Revision
    media_ready: StrictBool
    playback_ready: StrictBool
    app_ready: StrictBool


class Refresh(Bound):
    consent: StrictBool


class WorkerReady(Model):
    session_id: Id
    generation: Id
    context_revision: Revision
    runtime_ready: StrictBool


def router() -> APIRouter:
    routes = APIRouter()

    def service(request: Request) -> AssistanceService:
        value = request.app.state.assistance
        if value is None:
            raise LifecycleError(503, "assistance_not_configured")
        return value

    def owner(request: Request) -> str:
        value = request.cookies.get("foodease_owner", "")
        if (
            not value
            or len(value) > 128
            or not all(c.isascii() and (c.isalnum() or c in "-_") for c in value)
        ):
            raise LifecycleError(401, "owner_required")
        return value

    @routes.post("/v2/session")
    @routes.post("/v2/assist/start")
    async def start(
        request: Request, body: Start, x_foodease_session: Annotated[Id, Header()]
    ) -> dict:
        return await service(request).start(
            owner(request), x_foodease_session, body.request_id, consent=body.consent
        )

    @routes.post("/v2/token")
    async def refresh(
        request: Request, body: Refresh, x_foodease_session: Annotated[Id, Header()]
    ) -> dict:
        return await service(request).refresh(
            owner(request),
            x_foodease_session,
            body.request_id,
            body.generation,
            consent=body.consent,
        )

    @routes.post("/v2/assist/ready")
    async def ready(
        request: Request, body: Ready, x_foodease_session: Annotated[Id, Header()]
    ) -> dict:
        return await service(request).ready(
            owner(request),
            x_foodease_session,
            body.request_id,
            body.generation,
            body.context_revision,
            body.media_ready,
            body.playback_ready,
            body.app_ready,
        )

    @routes.post("/v2/assist/end")
    async def end(request: Request, body: End, x_foodease_session: Annotated[Id, Header()]) -> dict:
        return await service(request).end(
            owner(request), x_foodease_session, body.request_id, body.generation
        )

    @routes.get("/v2/assist/status/{request_id}")
    async def status(
        request: Request, request_id: Id, x_foodease_session: Annotated[Id, Header()]
    ) -> dict:
        return await service(request).status(owner(request), x_foodease_session, request_id)

    @routes.post("/v2/assist/worker-ready")
    async def worker_ready(
        request: Request, body: WorkerReady, x_foodease_worker_proof: Annotated[Id, Header()]
    ) -> dict:
        return await service(request).worker_ready(
            body.session_id,
            body.generation,
            x_foodease_worker_proof,
            body.context_revision,
            runtime_ready=body.runtime_ready,
        )

    return routes
