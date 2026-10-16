from pathlib import Path

from foodease_website.catalog import load_catalog


def test_catalog_seed_loads_from_pack() -> None:
    root = Path(__file__).resolve().parents[2]
    catalog = load_catalog(root / "zainab-pack" / "catalog-seed.json")

    assert catalog.currency == "PKR"
    assert catalog.service_fee_pkr == 50
    assert catalog.item_count == 28
    assert len(catalog.items) == 28
    assert any(item.item_id == "wrap-hot-chicken" for item in catalog.items)


def test_catalog_summary_counts_available_items() -> None:
    root = Path(__file__).resolve().parents[2]
    catalog = load_catalog(root / "zainab-pack" / "catalog-seed.json")
    summary = catalog.summary()

    assert summary["item_count"] == 28
    assert summary["available_item_count"] == 27
    assert "burgers" in summary["categories"]
