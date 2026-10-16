"""FastAPI app for the FoodEase website."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from foodease_website.catalog import CatalogSeed, load_catalog
from foodease_website.config import Settings, load_settings
from foodease_website.domain import FoodEaseDomain

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


def create_app(settings: Settings | None = None) -> FastAPI:
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
    app.state.domain = FoodEaseDomain(catalog)

    app.mount(
        "/static",
        StaticFiles(directory=str(package_root / "static")),
        name="static",
    )

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "app_name": cfg.app_name,
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
    def app_context() -> dict[str, object]:
        return app.state.domain.snapshot()

    @app.post("/api/app/action")
    async def app_action(request: Request) -> dict[str, object]:
        body = await request.json()
        return app.state.domain.execute_action(
            action_id=str(body.get("action_id", "")),
            operation=str(body.get("operation", "")),
            arguments=body.get("arguments") or {},
            context_revision=body.get("context_revision"),
        )

    return app


app = create_app()


def get_catalog(app_instance: FastAPI) -> CatalogSeed:
    return app_instance.state.catalog
