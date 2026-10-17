from pathlib import Path

from foodease_website.catalog import load_catalog
from foodease_website.domain import FoodEaseDomain


def make_domain() -> FoodEaseDomain:
    root = Path(__file__).resolve().parents[2]
    return FoodEaseDomain(load_catalog(root / "zainab-pack" / "catalog-seed.json"))


def test_available_filter_is_authoritative_and_budget_includes_boundary() -> None:
    domain = make_domain()
    result = domain.execute_action(
        "available",
        "filter_menu",
        {
            "tags": ["available"],
            "category": None,
            "max_price_pkr": 800.0,
        },
        context_revision=domain.revision,
    )
    assert result["status"] == "success"
    assert all(
        row["available"] and row["price"] <= 800 for row in result["verified_state"]["items"]
    )
    assert all(row.available for row in domain.visible_items())
    assert domain.snapshot()["filter_tags"] == ["available"]


def test_filter_menu_uses_real_catalog_tags_and_prices() -> None:
    domain = make_domain()

    result = domain.execute_action(
        "filter-1",
        "filter_menu",
        {"tags": ["vegetarian"], "max_price_pkr": 800},
        context_revision=domain.revision,
    )

    ids = [item["item_id"] for item in result["verified_state"]["items"]]
    assert result["status"] == "success"
    assert "wrap-veg" in ids
    assert "roll-paneer" in ids
    assert all(item["price"] <= 800 for item in result["verified_state"]["items"])


def test_cart_add_and_set_quantity_are_authoritative() -> None:
    domain = make_domain()
    revision = domain.revision

    add = domain.execute_action(
        "add-1",
        "cart.add_item",
        {"item_id": "wrap-hot-chicken", "quantity": 2},
        context_revision=revision,
    )
    set_qty = domain.execute_action(
        "qty-1",
        "cart.set_quantity",
        {"item_id": "wrap-hot-chicken", "quantity": 1},
        context_revision=domain.revision,
    )

    assert add["status"] == "success"
    assert set_qty["status"] == "success"
    assert set_qty["verified_state"]["lines"][0]["quantity"] == 1
    assert set_qty["verified_state"]["total"] == 900


def test_duplicate_action_id_does_not_duplicate_mutation() -> None:
    domain = make_domain()

    first = domain.execute_action(
        "add-dup",
        "cart.add_item",
        {"item_id": "drink-cola", "quantity": 1},
        context_revision=domain.revision,
    )
    second = domain.execute_action(
        "add-dup",
        "cart.add_item",
        {"item_id": "drink-cola", "quantity": 1},
        context_revision=domain.revision,
    )

    assert first == second
    assert domain.cart["drink-cola"].quantity == 1


def test_stale_revision_rejects_mutation_without_changing_cart() -> None:
    domain = make_domain()
    stale_revision = domain.revision
    domain.execute_action(
        "nav-1",
        "navigate",
        {"target": "menu"},
        context_revision=domain.revision,
    )

    result = domain.execute_action(
        "add-stale",
        "cart.add_item",
        {"item_id": "drink-cola", "quantity": 1},
        context_revision=stale_revision,
    )

    assert result["status"] == "stale_context"
    assert domain.cart == {}


def test_checkout_requires_current_confirmation_and_creates_one_demo_order() -> None:
    domain = make_domain()
    domain.execute_action(
        "add-1",
        "cart.add_item",
        {"item_id": "drink-cola", "quantity": 1},
        context_revision=domain.revision,
    )
    summary = domain.execute_action(
        "summary-1",
        "checkout.get_summary",
        {},
        context_revision=domain.revision,
    )
    submit = domain.execute_action(
        "submit-1",
        "checkout.submit_demo_order",
        {
            "confirmed": True,
            "confirmation_token": summary["confirmation_token"],
            "summary_revision": summary["verified_state"]["summary_revision"],
        },
        context_revision=domain.revision,
    )
    duplicate = domain.execute_action(
        "submit-1",
        "checkout.submit_demo_order",
        {
            "confirmed": True,
            "confirmation_token": summary["confirmation_token"],
            "summary_revision": summary["verified_state"]["summary_revision"],
        },
        context_revision=domain.revision,
    )

    assert submit["status"] == "success"
    assert submit == duplicate
    assert submit["verified_state"]["demo_order_id"].startswith("DEMO-")
    assert domain.demo_order_count == 1
    assert domain.cart == {}
