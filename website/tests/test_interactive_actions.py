"""Interactive actions use the existing authoritative cart, never model prices."""

from test_domain import make_domain


def act(domain, operation, args=None, action_id=None):
    return domain.execute_action(
        action_id or f"action-{len(domain.action_log)}",
        operation,
        args or {},
        context_revision=domain.revision,
    )


def test_increase_rechecks_current_stock_but_decrease_and_remove_still_work():
    domain = make_domain()
    act(domain, "cart.add_item", {"item_id": "drink-cola", "quantity": 2})
    domain.menu_by_id["drink-cola"].available = False
    assert (
        act(domain, "cart.set_quantity", {"item_id": "drink-cola", "quantity": 3})["error_code"]
        == "out_of_stock"
    )
    assert domain.cart["drink-cola"].quantity == 2
    assert (
        act(domain, "cart.set_quantity", {"item_id": "drink-cola", "quantity": 1})["status"]
        == "success"
    )
    assert act(domain, "cart.remove_item", {"item_id": "drink-cola"})["status"] == "success"


def test_clear_requires_review_token_is_atomic_idempotent_and_reversible():
    domain = make_domain()
    act(domain, "cart.add_item", {"item_id": "drink-cola", "quantity": 2})
    act(domain, "cart.add_item", {"item_id": "side-fries", "quantity": 1})
    before = domain.cart_summary()
    assert (
        act(
            domain,
            "cart.clear",
            {"confirmed": True, "confirmation_token": "invented", "summary_revision": 0},
        )["status"]
        != "success"
    )
    review = act(domain, "cart.get_clear_summary")
    assert domain.cart_summary() == before
    args = {
        "confirmed": True,
        "confirmation_token": review["confirmation_token"],
        "summary_revision": review["verified_state"]["summary_revision"],
    }
    first = act(domain, "cart.clear", args, "clear-once")
    assert first["status"] == "success" and not domain.cart
    assert act(domain, "cart.clear", args, "clear-once") == first
    assert act(domain, "undo_last_reversible_action")["verified_state"] == before


def test_clear_and_checkout_tokens_cannot_be_cross_used_or_survive_cart_edit():
    domain = make_domain()
    act(domain, "cart.add_item", {"item_id": "drink-cola"})
    for review_op, wrong_op in [
        ("cart.get_clear_summary", "checkout.submit_demo_order"),
        ("checkout.get_summary", "cart.clear"),
    ]:
        review = act(domain, review_op)
        args = {
            "confirmed": True,
            "confirmation_token": review["confirmation_token"],
            "summary_revision": review["verified_state"]["summary_revision"],
        }
        assert act(domain, wrong_op, args)["status"] != "success"
        assert domain.cart and domain.demo_order_count == 0
    review = act(domain, "cart.get_clear_summary")
    act(domain, "cart.set_quantity", {"item_id": "drink-cola", "quantity": 2})
    assert (
        act(
            domain,
            "cart.clear",
            {
                "confirmed": True,
                "confirmation_token": review["confirmation_token"],
                "summary_revision": review["verified_state"]["summary_revision"],
            },
        )["status"]
        != "success"
    )
    assert domain.cart["drink-cola"].quantity == 2


def test_category_navigation_clears_conflicting_search_and_popular_uses_existing_menu():
    domain = make_domain()
    act(domain, "search_menu", {"query": "juice"})
    assert act(domain, "navigate", {"target": "burgers"})["status"] == "success"
    assert domain.category == "burgers" and not domain.search_query
    assert domain.visible_items()
    assert act(domain, "navigate", {"target": "popular"})["status"] == "success"
    assert domain.category is None and domain.route == "menu"
