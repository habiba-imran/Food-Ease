"""Shopping language is interpreted by the LLM; tools own menu facts and bounds."""

import pytest

from foodease_agent.integrated.conversation import heard_items
from test_integrated_runtime import turn

pytest_plugins = ("test_integrated_runtime",)


@pytest.mark.parametrize(
    "question",
    [
        "list items on the juice menu",
        "what beverages do you have?",
        "kuch peenay ko hai?",
        "مشروبات میں کیا ہے؟",
        "جوس کون سے ہیں؟",
        "کوئی ٹھنڈی چیز پینے کو ملے گی؟",
        "ہزار روپے سے کم کے سارے کھانے بتائیں",
        "list all items below 1000",
    ],
)
async def test_freeform_shopping_questions_reach_the_same_model_path(runtime, question):
    await turn(runtime, question)
    assert not runtime.adapter.requests
    assert len(runtime.session.generated) == 1


async def test_model_can_request_complete_strict_budget_results(runtime):
    context = await turn(runtime, "list all items below 1000")
    result = await runtime.agent.filter_menu(
        context,
        max_price_pkr=1000,
        price_exclusive=True,
        read_all=True,
    )
    assert result["status"] == "success"
    assert runtime.snapshot.max_price_pkr == 999.99
    rows = runtime.snapshot.visible_items
    assert len(rows) == 25 and all(row.price < 1000 for row in rows)
    assert heard_items(result["say"], rows) == rows
    assert not runtime.snapshot.cart.lines


async def test_category_and_product_search_remain_distinct_catalog_operations(runtime):
    context = await turn(runtime, "مشروبات میں کیا ہے؟")
    drinks = await runtime.agent.filter_menu(context, category="drinks", read_all=True)
    assert len(drinks["facts"]["items"]) == 4
    juice = await runtime.agent.search_menu(context, "juice", read_all=True)
    assert [row["name"] for row in juice["facts"]["items"]] == ["Mango Juice"]


async def test_unknown_category_cannot_be_invented_by_the_model(runtime):
    context = await turn(runtime, "جوس بتائیں")
    result = await runtime.agent.filter_menu(context, category="invented-category")
    assert result["status"] != "success"
    assert not runtime.snapshot.cart.lines


@pytest.mark.parametrize(
    ("exclusive", "ceiling", "includes_650"),
    [
        (True, 649.99, False),
        (False, 650, True),
    ],
)
async def test_price_boundary_is_enforced_by_tool_code(runtime, exclusive, ceiling, includes_650):
    context = await turn(runtime, "قیمت کی حد لگائیں")
    result = await runtime.agent.filter_menu(
        context, max_price_pkr=650, price_exclusive=exclusive, read_all=True
    )
    assert result["status"] == "success"
    assert runtime.snapshot.max_price_pkr == ceiling
    assert any(row.price == 650 for row in runtime.snapshot.visible_items) == includes_650


async def test_invalid_exclusive_price_does_not_clear_existing_search(runtime):
    context = await turn(runtime, "find burgers")
    await runtime.agent.search_menu(context, "burger")
    count = len(runtime.adapter.requests)
    result = await runtime.agent.filter_menu(
        context, max_price_pkr=0, price_exclusive=True, clear_search=True
    )
    assert result["status"] != "success"
    assert len(runtime.adapter.requests) == count
    assert runtime.snapshot.search_query == "burger"


async def test_new_catalog_item_and_category_need_no_voice_keyword_rules(runtime):
    from foodease_website.sessions import SessionStore

    catalog = runtime.adapter.store.catalog.model_copy(deep=True)
    new_item = catalog.items[0].model_copy(
        update={
            "item_id": "seasonal-tamarind-cooler",
            "name": "Sparkling Tamarind Cooler",
            "category": "seasonal-specials",
            "unit_price_pkr": 275,
        }
    )
    catalog.items.append(new_item)
    catalog.categories.append("seasonal-specials")
    catalog.item_count = len(catalog.items)
    runtime.adapter.store = SessionStore(catalog)
    runtime.adapter.owner = runtime.adapter.store.new_owner()
    runtime.adapter.session_id = runtime.adapter.store.create(runtime.adapter.owner).session_id
    await runtime.prepare()
    assert "seasonal-specials" in runtime.reasoning_data()["page"]["valid_navigation_targets"]
    context = await turn(runtime, "show the new seasonal refreshments")
    result = await runtime.agent.filter_menu(context, category="seasonal-specials", read_all=True)
    assert [row["name"] for row in result["facts"]["items"]] == [new_item.name]
    assert result["facts"]["items"][0]["price"] == 275
    assert (await runtime.agent.cart_add_item(context, new_item.item_id, 1))["status"] == "success"
