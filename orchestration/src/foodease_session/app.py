"""FastAPI application for FoodEase session/token minting + assist gate."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from foodease_session.assist import (
    AssistError,
    AssistRegistry,
    DispatchClient,
    LiveKitDispatchClient,
    assist_metadata,
)
from foodease_session.config import ConfigError, Settings, load_settings
from foodease_session.lifecycle import AssistanceService, HttpShoppingAuthority, LifecycleError
from foodease_session.lifecycle_api import router as lifecycle_router
from foodease_session.mint import MintError, Role, mint_pair, mint_token
from foodease_session.models import (
    AssistEndRequest,
    AssistEndResponse,
    AssistStartRequest,
    AssistStartResponse,
    ErrorBody,
    HealthResponse,
    ParticipantToken,
    SessionCreateRequest,
    SessionCreateResponse,
    TokenMintRequest,
    TokenMintResponse,
)
from foodease_session.policy import PolicyError, new_session_id, normalize_room, resolve_identity
from foodease_session.rate_limit import RateLimiter

logger = logging.getLogger("foodease.session")


def _expires_at(ttl_seconds: int) -> str:
    return (datetime.now(UTC) + timedelta(seconds=ttl_seconds)).isoformat()


def create_app(
    settings: Settings | None = None,
    *,
    dispatch_client: DispatchClient | None = None,
    assistance_service: AssistanceService | None = None,
) -> FastAPI:
    try:
        cfg = settings or load_settings()
    except ConfigError:
        cfg = None

    @asynccontextmanager
    async def lifespan(app_instance: FastAPI):
        service = app_instance.state.assistance

        async def sweep():
            while True:
                await asyncio.sleep(1)
                await service.sweep()

        task = asyncio.create_task(sweep()) if service is not None else None
        try:
            yield
        finally:
            if task is not None:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
                if service is not None:
                    await service.close()

    app = FastAPI(
        title="FoodEase Session API",
        version="1.1.0",
        lifespan=lifespan,
        description=(
            "Short-lived LiveKit JWTs + consent-gated agent dispatch (no shopping logic)."
        ),
    )
    app.state.settings = cfg
    app.state.registry = AssistRegistry()
    if dispatch_client is not None:
        app.state.dispatch = dispatch_client
    elif cfg is not None:
        app.state.dispatch = LiveKitDispatchClient(
            url=cfg.livekit_url,
            api_key=cfg.livekit_api_key,
            api_secret=cfg.livekit_api_secret,
        )
    else:
        app.state.dispatch = None
    app.state.assistance = assistance_service
    if (
        assistance_service is None
        and cfg is not None
        and isinstance(app.state.dispatch, LiveKitDispatchClient)
    ):
        app.state.assistance = AssistanceService(
            cfg, HttpShoppingAuthority(cfg.website_base_url), app.state.dispatch
        )
    app.include_router(lifecycle_router())

    @app.exception_handler(LifecycleError)
    async def lifecycle_error(request: Request, exc: LifecycleError) -> JSONResponse:
        return JSONResponse({"error": exc.code}, status_code=exc.status)

    limiter = RateLimiter(
        max_requests=(cfg.rate_limit_requests if cfg else 60),
        window_seconds=(cfg.rate_limit_window_seconds if cfg else 60),
    )
    app.state.limiter = limiter

    if cfg and cfg.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(cfg.cors_origins),
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Content-Type", "X-FoodEase-Session"],
        )

    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        if request.url.path.startswith("/v1/") and (cfg is None or not cfg.enable_legacy_api):
            return JSONResponse({"error": "legacy_api_disabled_use_bound_v2"}, status_code=410)
        origin = request.headers.get("origin")
        if (
            request.url.path.startswith("/v2/")
            and origin
            and (cfg is None or origin not in cfg.cors_origins)
        ):
            return JSONResponse({"error": "unauthorized_origin"}, status_code=403)
        if request.url.path == "/healthz":
            return await call_next(request)
        client = request.client.host if request.client else "unknown"
        if not limiter.allow(client):
            logger.warning("rate_limited path=%s ip=%s", request.url.path, client)
            return JSONResponse(
                status_code=429,
                content=ErrorBody(error="rate_limited", detail="Too many requests").model_dump(),
            )
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/healthz", response_model=HealthResponse)
    def healthz() -> HealthResponse:
        return HealthResponse()

    def _require_settings() -> Settings:
        s: Settings | None = app.state.settings
        if s is None:
            raise ConfigError("session service not configured (missing LIVEKIT_* env)")
        return s

    @app.post("/v1/session", response_model=SessionCreateResponse)
    def create_session(body: SessionCreateRequest) -> SessionCreateResponse | JSONResponse:
        try:
            s = _require_settings()
            room = normalize_room(body.room)
            session_id = new_session_id()
            voice_allowed = bool(body.consent)
            user_identity = resolve_identity(body.user_identity, prefix="user")
            app_identity = resolve_identity(body.app_identity, prefix="app")

            tokens = mint_pair(
                api_key=s.livekit_api_key,
                api_secret=s.livekit_api_secret,
                room=room,
                user_identity=user_identity,
                app_identity=app_identity,
                ttl_seconds=s.token_ttl_seconds,
                include_user=voice_allowed,
                include_app=bool(body.include_app_token),
            )
            user_pt = ParticipantToken(**tokens["user"]) if "user" in tokens else None
            app_pt = ParticipantToken(**tokens["app"]) if "app" in tokens else None

            logger.info(
                "session_created session_id=%s room=%s voice_allowed=%s include_app=%s",
                session_id,
                room,
                voice_allowed,
                body.include_app_token,
            )
            return SessionCreateResponse(
                session_id=session_id,
                room=room,
                livekit_url=s.livekit_url,
                expires_at=_expires_at(s.token_ttl_seconds),
                ttl_seconds=s.token_ttl_seconds,
                voice_allowed=voice_allowed,
                user=user_pt,
                app=app_pt,
            )
        except (ConfigError, PolicyError, MintError) as exc:
            logger.info("session_rejected detail=%s", type(exc).__name__)
            return JSONResponse(
                status_code=400 if not isinstance(exc, ConfigError) else 500,
                content=ErrorBody(error=type(exc).__name__, detail=str(exc)).model_dump(),
            )

    @app.post("/v1/token", response_model=TokenMintResponse)
    def mint_one(body: TokenMintRequest) -> TokenMintResponse | JSONResponse:
        try:
            s = _require_settings()
            room = normalize_room(body.room)
            if body.role == "user" and not body.consent:
                return JSONResponse(
                    status_code=403,
                    content=ErrorBody(
                        error="consent_required",
                        detail="Minting a user (mic) token requires consent=true",
                    ).model_dump(),
                )
            role = Role(body.role)
            identity = resolve_identity(
                body.identity,
                prefix="user" if role is Role.USER else "app",
            )
            jwt = mint_token(
                api_key=s.livekit_api_key,
                api_secret=s.livekit_api_secret,
                role=role,
                room=room,
                identity=identity,
                ttl_seconds=s.token_ttl_seconds,
            )
            logger.info("token_minted role=%s room=%s identity=%s", body.role, room, identity)
            return TokenMintResponse(
                room=room,
                livekit_url=s.livekit_url,
                expires_at=_expires_at(s.token_ttl_seconds),
                ttl_seconds=s.token_ttl_seconds,
                participant=ParticipantToken(identity=identity, token=jwt, role=body.role),
            )
        except (ConfigError, PolicyError, MintError) as exc:
            code = 500 if isinstance(exc, ConfigError) else 400
            return JSONResponse(
                status_code=code,
                content=ErrorBody(error=type(exc).__name__, detail=str(exc)).model_dump(),
            )

    @app.post("/v1/assist/start", response_model=AssistStartResponse)
    async def assist_start(body: AssistStartRequest) -> AssistStartResponse | JSONResponse:
        try:
            if not body.consent:
                return JSONResponse(
                    status_code=403,
                    content=ErrorBody(
                        error="consent_required",
                        detail="Start assistance requires consent=true (WEB-01)",
                    ).model_dump(),
                )
            s = _require_settings()
            room = normalize_room(body.room)
            session_id = new_session_id()
            user_identity = resolve_identity(body.user_identity, prefix="user")
            app_identity = resolve_identity(body.app_identity, prefix="app")

            tokens = mint_pair(
                api_key=s.livekit_api_key,
                api_secret=s.livekit_api_secret,
                room=room,
                user_identity=user_identity,
                app_identity=app_identity,
                ttl_seconds=s.token_ttl_seconds,
                include_user=True,
                include_app=bool(body.include_app_token),
            )
            user_pt = ParticipantToken(**tokens["user"])
            app_pt = ParticipantToken(**tokens["app"]) if "app" in tokens else None

            dispatch_id: str | None = None
            if s.livekit_agent_dispatch:
                client: DispatchClient | None = app.state.dispatch
                if client is None:
                    raise AssistError("dispatch client not configured")
                dispatch_id = await client.create_dispatch(
                    agent_name=s.foodease_agent_name,
                    room=room,
                    metadata=assist_metadata(session_id=session_id),
                )
                app.state.registry.remember(
                    session_id=session_id, room=room, dispatch_id=dispatch_id
                )
            else:
                logger.warning(
                    "assist_start without LiveKit dispatch "
                    "(LIVEKIT_AGENT_DISPATCH=false) session_id=%s room=%s",
                    session_id,
                    room,
                )

            logger.info(
                "assist_started session_id=%s room=%s dispatch_id=%s",
                session_id,
                room,
                dispatch_id,
            )
            return AssistStartResponse(
                session_id=session_id,
                room=room,
                livekit_url=s.livekit_url,
                expires_at=_expires_at(s.token_ttl_seconds),
                ttl_seconds=s.token_ttl_seconds,
                voice_allowed=True,
                dispatch_id=dispatch_id,
                dispatch_enabled=s.livekit_agent_dispatch,
                user=user_pt,
                app=app_pt,
            )
        except (ConfigError, PolicyError, MintError, AssistError) as exc:
            code = 500 if isinstance(exc, (ConfigError, AssistError)) else 400
            if isinstance(exc, AssistError):
                code = 502
            logger.info("assist_start_rejected detail=%s", type(exc).__name__)
            return JSONResponse(
                status_code=code,
                content=ErrorBody(error=type(exc).__name__, detail=str(exc)).model_dump(),
            )

    @app.post("/v1/assist/end", response_model=AssistEndResponse)
    async def assist_end(body: AssistEndRequest) -> AssistEndResponse | JSONResponse:
        try:
            s = _require_settings()
            room = normalize_room(body.room)
            registry: AssistRegistry = app.state.registry
            dispatch_id = registry.resolve(
                session_id=body.session_id, room=room, dispatch_id=body.dispatch_id
            )
            deleted = False
            if dispatch_id and s.livekit_agent_dispatch:
                client: DispatchClient | None = app.state.dispatch
                if client is None:
                    raise AssistError("dispatch client not configured")
                try:
                    await client.delete_dispatch(dispatch_id=dispatch_id, room=room)
                    deleted = True
                except AssistError:
                    # Idempotent: already gone still counts as ended
                    logger.info("assist_end delete soft-fail dispatch_id=%s", dispatch_id)
                    deleted = False
            registry.forget(session_id=body.session_id, room=room, dispatch_id=dispatch_id)
            logger.info(
                "assist_ended room=%s dispatch_id=%s cart_preserved=true",
                room,
                dispatch_id,
            )
            return AssistEndResponse(
                room=room,
                ended=True,
                cart_preserved=True,
                dispatch_id=dispatch_id,
                dispatch_deleted=deleted,
            )
        except (ConfigError, PolicyError, AssistError) as exc:
            code = 500 if isinstance(exc, ConfigError) else 400
            if isinstance(exc, AssistError):
                code = 502
            return JSONResponse(
                status_code=code,
                content=ErrorBody(error=type(exc).__name__, detail=str(exc)).model_dump(),
            )

    return app


try:
    app = create_app()
except ConfigError:
    app = create_app(settings=None)
