"""Catalog loading for the frozen FoodEase seed menu."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class MenuItem(BaseModel):
    item_id: str
    name: str
    unit_price_pkr: float = Field(ge=0)
    category: str
    tags: list[str] = Field(default_factory=list)
    available: bool = True
    description: str
    ingredients: list[str] | None = None
    currency: str = "PKR"


class CatalogSeed(BaseModel):
    schema_version: str = "1.0"
    source: str | None = None
    currency: str = "PKR"
    service_fee_pkr: float = Field(default=0, ge=0)
    notes: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    item_count: int
    items: list[MenuItem]

    def summary(self) -> dict[str, Any]:
        available_count = sum(1 for item in self.items if item.available)
        return {
            "currency": self.currency,
            "service_fee_pkr": self.service_fee_pkr,
            "category_count": len(self.categories),
            "item_count": len(self.items),
            "declared_item_count": self.item_count,
            "available_item_count": available_count,
            "categories": self.categories,
        }


def load_catalog(path: Path) -> CatalogSeed:
    data = json.loads(path.read_text(encoding="utf-8"))
    catalog = CatalogSeed.model_validate(data)
    if catalog.item_count != len(catalog.items):
        raise ValueError(
            f"catalog item_count={catalog.item_count} does not match items={len(catalog.items)}"
        )
    item_ids = [item.item_id for item in catalog.items]
    if len(item_ids) != len(set(item_ids)):
        raise ValueError("catalog contains duplicate item_id values")
    return catalog

