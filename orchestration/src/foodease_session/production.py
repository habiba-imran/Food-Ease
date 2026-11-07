"""Single-process Render service: existing cart authority + bound session/token API.

Sessions deliberately expire on process restart. Run one instance and one ASGI worker;
multi-instance persistence requires an external transactional state store first.
"""

from __future__ import annotations

import os
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import replace

from fastapi import FastAPI
from foodease_website.app import create_app as create_website
from foodease_website.config import load_settings as website_settings
from foodease_website.sessions import SessionError

from foodease_session.app import create_app as create_session
from foodease_session.assist import LiveKitDispatchClient
from foodease_session.config import load_settings
from foodease_session.lifecycle import AssistanceService, LifecycleError


class LocalAuthority:
    def __init__(self, sessions):
        self.sessions = sessions

    async def check(self, owner: str, sid: str) -> dict:
        try:
            return self.sessions.context(owner, sid)
        except SessionError as error:
            raise LifecycleError(error.status, "shopping_session_unavailable") from None


def create_backend(*, settings=None, cloud=None) -> FastAPI:
    if os.environ.get("FOODEASE_BACKEND_URL"):
        raise RuntimeError(
            "FOODEASE_BACKEND_URL belongs on Vercel only; backend proxy loop refused"
        )
    cfg = settings or load_settings()
    website = create_website(
        replace(website_settings(), enable_mock_agent=False, orchestration_base_url="/assist")
    )
    dispatch = cloud or LiveKitDispatchClient(
        cfg.livekit_url, cfg.livekit_api_key, cfg.livekit_api_secret
    )
    service = AssistanceService(cfg, LocalAuthority(website.state.sessions), dispatch)
    sessions = create_session(cfg, assistance_service=service)

    @asynccontextmanager
    async def lifespan(app):
        async with AsyncExitStack() as stack:
            await stack.enter_async_context(website.router.lifespan_context(website))
            await stack.enter_async_context(sessions.router.lifespan_context(sessions))
            yield

    app = FastAPI(title="FoodEase production backend", lifespan=lifespan)
    app.state.website, app.state.sessions = website, sessions

    @app.get("/healthz")
    async def health():
        return {"status": "ok", "service": "foodease-backend", "session_storage": "single_process"}

    app.mount("/assist", sessions)
    app.mount("/", website)
    return app
