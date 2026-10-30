"""FastAPI app for the FoodEase website."""

from __future__ import annotations

import json
import secrets
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from foodease_contract.models import MAX_WIRE_BYTES, ActionRequest, ActionRequestEvent, Id, Revision
from pydantic import BaseModel, ConfigDict, ValidationError
from starlette.concurrency import run_in_threadpool

from foodease_website.assets import PublicAssetFiles
from foodease_website.catalog import CatalogSeed, load_catalog
from foodease_website.config import Settings, load_settings
from foodease_website.sessions import SessionError, SessionStore, timestamp


class ManualAction(ActionRequest):
    context_revision: Revision


class Attachment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: Id


async def read_body(request: Request) -> dict:
    content = bytearray()
    async for chunk in request.stream():
        content.extend(chunk)
        if len(content) > MAX_WIRE_BYTES:
            raise SessionError(413, "payload_too_large")
    try:
        value = json.loads(content)
    except (ValueError, UnicodeDecodeError):
        raise SessionError(400, "invalid_json") from None
    if not isinstance(value, dict):
        raise SessionError(422, "invalid_arguments")
    return value


CATEGORY_LABELS = {
    "biryani": "Biryani",
    "burgers": "Burgers",
    "desserts": "Desserts",
    "drinks": "Drinks",
    "karahi": "Karahi",
    "platters": "Platters",
    "rolls": "Rolls",
    "sides": "Sides",
    "wraps": "Wraps",
}

PUBLIC_DESCRIPTIONS = {
    "side-fries": "Crispy fries tossed with house masala.",
}


def _public_description(item_id: str, description: str) -> str:
    return PUBLIC_DESCRIPTIONS.get(item_id, description)


def _category_cards(catalog: CatalogSeed) -> list[dict[str, object]]:
    cards: list[dict[str, object]] = []
    for category in catalog.categories:
        items = [item for item in catalog.items if item.category == category]
        available = sum(1 for item in items if item.available)
        sample = next((item.name for item in items if item.available), "Coming soon")
        cards.append(
            {
                "id": category,
                "label": CATEGORY_LABELS.get(category, category.title()),
                "count": len(items),
                "available": available,
                "sample": sample,
            }
        )
    return cards


def _featured_items(catalog: CatalogSeed) -> list[dict[str, object]]:
    preferred_ids = [
        "zinger-classic",
        "wrap-veg",
        "biryani-chicken",
        "dessert-gulab",
    ]
    by_id = {item.item_id: item for item in catalog.items}
    featured = [by_id[item_id] for item_id in preferred_ids if item_id in by_id]
    return [
        {
            "item_id": item.item_id,
            "name": item.name,
            "price": item.unit_price_pkr,
            "category": CATEGORY_LABELS.get(item.category, item.category.title()),
            "tags": item.tags,
            "available": item.available,
            "description": _public_description(item.item_id, item.description),
        }
        for item in featured
    ]


def _menu_items(catalog: CatalogSeed) -> list[dict[str, object]]:
    return [
        {
            "item_id": item.item_id,
            "name": item.name,
            "price": item.unit_price_pkr,
            "category": CATEGORY_LABELS.get(item.category, item.category.title()),
            "category_id": item.category,
            "tags": item.tags,
            "available": item.available,
            "description": _public_description(item.item_id, item.description),
        }
        for item in catalog.items
    ]


def create_app(
    settings: Settings | None = None, *, sessions: SessionStore | None = None
) -> FastAPI:
    cfg = settings or load_settings()
    catalog = load_catalog(cfg.catalog_seed_path)

    package_root = Path(__file__).resolve().parents[2]
    templates = Jinja2Templates(directory=str(package_root / "templates"))

    app = FastAPI(
        title="FoodEase Website",
        version="0.1.0",
        description="Accessible FoodEase shopping UI and future app-seat client.",
    )
    app.state.settings = cfg
    app.state.catalog = catalog
    store = sessions or SessionStore(catalog)
    app.state.sessions = store

    @app.exception_handler(SessionError)
    async def session_error(request: Request, exc: SessionError) -> JSONResponse:
        return JSONResponse({"error": exc.code}, status_code=exc.status)

    @app.exception_handler(ValidationError)
    async def invalid_body(request: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse({"error": "invalid_arguments"}, status_code=422)

    @app.middleware("http")
    async def protect_requests(request: Request, call_next):
        if request.method == "POST":
            origin = request.headers.get("origin")
            expected = f"{request.url.scheme}://{request.url.netloc}"
            if origin and origin != expected:
                return JSONResponse({"error": "unauthorized_origin"}, status_code=403)
        response = await call_next(request)
        if request.url.path.startswith("/api/app") or request.url.path.startswith("/api/v2/app"):
            response.headers["Cache-Control"] = "no-store"
        return response

    def owner(request: Request) -> str:
        return store.authorize_owner(request.cookies.get("foodease_owner"))

    def bootstrap_owner(request: Request) -> str:
        try:
            return owner(request)
        except SessionError as exc:
            if exc.status not in {401, 410}:
                raise
            return store.new_owner()

    def set_owner(response, request: Request, owner_id: str) -> None:
        response.set_cookie(
            "foodease_owner",
            owner_id,
            httponly=True,
            samesite="strict",
            secure=request.url.scheme == "https",
            max_age=int(store.absolute_ttl),
        )

    def session_id(request: Request, owner_id: str, *, legacy: bool = False) -> str:
        sid = request.headers.get("X-FoodEase-Session")
        if not sid and legacy:
            return store.default(owner_id).session_id
        if not sid:
            raise SessionError(401, "session_required")
        return sid

    app.mount(
        "/static",
        PublicAssetFiles(directory=str(package_root / "static")),
        name="static",
    )

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        owner_id = bootstrap_owner(request)
        response = templates.TemplateResponse(
            request,
            "index.html",
            {
                "app_name": cfg.app_name,
                "orchestration_base_url": cfg.orchestration_base_url.rstrip("/"),
                "catalog_summary": catalog.summary(),
                "category_cards": _category_cards(catalog),
                "featured_items": _featured_items(catalog),
                "menu_items": _menu_items(catalog),
                "features": {
                    "mock_agent": cfg.enable_mock_agent,
                    "three_d": cfg.enable_3d,
                    "ar": cfg.enable_ar,
                },
            },
        )
        set_owner(response, request, owner_id)
        return response

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "service": "foodease-website"}

    @app.get("/api/catalog/summary")
    def catalog_summary() -> dict[str, object]:
        return catalog.summary()

    @app.get("/api/catalog/items")
    def catalog_items() -> dict[str, object]:
        return {
            "currency": catalog.currency,
            "service_fee_pkr": catalog.service_fee_pkr,
            "items": [item.model_dump(mode="json") for item in catalog.items],
        }

    @app.get("/api/app/context")
    def app_context(request: Request) -> JSONResponse:
        owner_id = bootstrap_owner(request)
        result = store.context(owner_id, session_id(request, owner_id, legacy=True))
        response = JSONResponse(result)
        set_owner(response, request, owner_id)
        return response

    @app.post("/api/app/action")
    async def app_action(request: Request) -> dict[str, object]:
        body = ManualAction.model_validate(await read_body(request))
        owner_id = owner(request)
        sid = session_id(request, owner_id, legacy=True)
        payload = body.model_dump(mode="json", exclude={"context_revision"})
        event = {
            "schema_version": "2.0",
            "session_id": sid,
            "event_id": secrets.token_urlsafe(18),
            "turn_id": "manual",
            "timestamp": timestamp(),
            "context_revision": body.context_revision,
            "type": "agent.action_request",
            "payload": payload,
        }
        result = await run_in_threadpool(store.submit, owner_id, sid, event)
        return result.payload.model_dump(mode="json")

    @app.post("/api/v2/app/sessions", status_code=201)
    async def create_session(request: Request) -> JSONResponse:
        if await read_body(request):
            raise SessionError(422, "invalid_arguments")
        owner_id = bootstrap_owner(request)
        shopping = store.create(owner_id)
        response = JSONResponse({"session_id": shopping.session_id}, status_code=201)
        set_owner(response, request, owner_id)
        return response

    @app.post("/api/v2/app/sessions/attach")
    async def attach_session(request: Request) -> dict:
        body = Attachment.model_validate(await read_body(request))
        shopping = store.attach(owner(request), body.session_id)
        return {"session_id": shopping.session_id}

    @app.get("/api/v2/app/context")
    def v2_context(request: Request) -> dict:
        owner_id = owner(request)
        return store.context(owner_id, session_id(request, owner_id))

    @app.post("/api/v2/app/action")
    async def v2_action(request: Request) -> dict:
        raw = await read_body(request)
        ActionRequestEvent.model_validate(raw)
        owner_id = owner(request)
        result = await run_in_threadpool(store.submit, owner_id, session_id(request, owner_id), raw)
        return result.model_dump(mode="json")

    @app.get("/api/v2/app/actions/{action_id}")
    def lookup(request: Request, action_id: str) -> dict:
        owner_id = owner(request)
        return store.lookup(
            owner_id,
            session_id(request, owner_id),
            action_id,
            request.headers.get("X-FoodEase-Event-Id") or secrets.token_urlsafe(18),
        ).model_dump(mode="json")

    return app


app = create_app()


def get_catalog(app_instance: FastAPI) -> CatalogSeed:
    return app_instance.state.catalog
