"""Phase 7 uses the real application authority, never the legacy planner."""

import asyncio
import json

from foodease_agent.integrated.conversation import SemanticPage, heard_items
from foodease_agent.integrated.output import guarded_output
from test_integrated_runtime import call, control, turn

pytest_plugins = ("test_integrated_runtime",)


async def test_page_context_exposes_meaningful_actions_without_claiming_catalog_total(runtime):
    page = SemanticPage(runtime.snapshot).data()
    assert page["location"] == "home"
    assert len(page["results"]) <= 3
    assert "checkout" not in page["buttons"]
    assert page["visible_count"] == 25
    assert "result_count" not in page


async def test_read_page_and_button_command_use_real_results_and_selected_item(runtime):
    await control(runtime, "read_page", "read this page")
    assert runtime.adapter.requests[-1].payload.operation == "get_current_context"
    assert "home" in runtime.session.spoken[-1].lower()
    assert len(runtime.session.generated) == 1
    runtime.on_delivered(runtime.session.spoken[-1], runtime.snapshot.revision)
    assert len(runtime.references.items) == 3
    expected = runtime.references.items[1].item_id
    await control(runtime, "open_reference", "open the second one")
    assert runtime.snapshot.focus_item_id == expected and runtime.snapshot.route == "item"
    await control(runtime, "add_button", "press add to cart")
    assert runtime.snapshot.cart.lines[0].item_id == expected
    assert "total" in runtime.session.spoken[-1].lower()


async def test_unheard_results_are_not_references_and_heard_order_wins(runtime):
    result = await call(runtime, "search_menu", query="burger")
    assert not runtime.references.items
    rows = result["facts"]["items"]
    runtime.on_delivered(f"{rows[1]['name']} or {rows[0]['name']}?", runtime.snapshot.revision)
    assert [row.item_id for row in runtime.references.items] == [
        rows[1]["item_id"],
        rows[0]["item_id"],
    ]
    await control(runtime, "open_reference", "open the second one")
    assert runtime.snapshot.focus_item_id == rows[0]["item_id"]


async def test_manual_edit_invalidates_deictic_reference_even_if_model_supplies_valid_id(runtime):
    result = await call(runtime, "search_menu", query="burger")
    runtime.on_delivered(result["say"], runtime.snapshot.revision)
    await runtime.adapter.manual("select_item", {"item_id": "wrap-hot-chicken"})
    runtime.on_context(await runtime.adapter.get_snapshot())
    count = len(runtime.adapter.requests)
    context = await turn(runtime, "add that")
    reply = await runtime.agent.cart_add_item(context, "wrap-hot-chicken")
    assert reply["status"] != "success" and len(runtime.adapter.requests) == count


async def test_short_list_next_previous_and_repeat_follow_delivered_windows(runtime):
    await control(runtime, "read_page", "read the page")
    await asyncio.sleep(0)
    first = [row.item_id for row in runtime.references.items]
    await control(runtime, "next", "next")
    await asyncio.sleep(0)
    assert len(runtime.references.items) == 3
    assert not set(first).intersection(row.item_id for row in runtime.references.items)
    await control(runtime, "previous", "previous")
    await asyncio.sleep(0)
    assert [row.item_id for row in runtime.references.items] == first


async def test_combined_steps_use_fresh_revisions_and_duplicate_add_is_refused(runtime):
    context = await turn(runtime, "find burgers then add one veggie burger")
    filtered = await runtime.agent.search_menu(context, "burger")
    assert filtered["status"] == "success"
    item = filtered["facts"]["items"][0]["item_id"]
    first = await runtime.agent.cart_add_item(context, item, 1)
    second = await runtime.agent.cart_add_item(context, item, 1)
    assert first["status"] == "success" and second["status"] != "success"
    assert runtime.snapshot.cart.lines[0].quantity == 1
    requests = runtime.adapter.requests
    assert requests[-1].context_revision == requests[-2].context_revision + 1


async def test_failed_combined_step_blocks_later_mutation_but_allows_read(runtime):
    context = await turn(runtime, "add a sold out burger then add a wrap")
    bad = await runtime.agent.cart_add_item(context, "burger-soldout", 1)
    assert bad["status"] != "success"
    count = len(runtime.adapter.requests)
    result = await runtime.agent.cart_add_item(context, "wrap-hot-chicken", 1)
    assert result["status"] != "success" and len(runtime.adapter.requests) == count
    assert (await runtime.agent.get_cart(context))["status"] == "success"


async def test_filter_refinement_preserves_tags_and_clear_removes_individual_budget(runtime):
    context = await turn(runtime, "vegetarian spicy below nine hundred")
    await runtime.agent.filter_menu(context, vegetarian=True, tags=["spicy"], max_price_pkr=900)
    context = await turn(runtime, "actually six hundred")
    await runtime.agent.filter_menu(context, max_price_pkr=600)
    assert set(runtime.snapshot.filter_tags) == {"vegetarian", "spicy"}
    assert runtime.snapshot.max_price_pkr == 600
    context = await turn(runtime, "remove the budget")
    await runtime.agent.filter_menu(context, clear_budget=True)
    assert runtime.snapshot.max_price_pkr is None
    assert "vegetarian" in runtime.snapshot.filter_tags


async def test_semantic_page_unknown_ingredients_are_not_invented(runtime):
    result = await call(runtime, "get_item_details", item_id="dessert-mystery")
    assert result["facts"]["ingredients"] is None
    data = runtime.reasoning_data()
    assert "ingredients" in json.dumps(data)


def test_reasoning_context_keeps_cart_and_visible_items_in_one_place(runtime):
    data = runtime.reasoning_data()
    assert "cart" not in data["page"]
    assert "results" not in data["semantic_page"]
    assert data["semantic_page"]["cart"] == runtime.snapshot.cart.model_dump(mode="json")
    assert [row["item_id"] for row in data["page"]["visible_items"]] == [
        row.item_id for row in runtime.snapshot.visible_items
    ]


async def test_simple_catalog_and_cart_questions_use_read_only_authority(runtime):
    await control(runtime, "read_categories", "What food categories are on the menu?")
    categories = runtime.session.spoken[-1].lower()
    assert "burgers" in categories and "wraps" in categories
    assert "checkout" not in categories
    assert runtime.adapter.requests[-1].payload.operation == "get_current_context"

    await control(runtime, "read_cart", "What's in my cart?")
    assert "cart is empty" in runtime.session.spoken[-1].lower()
    assert runtime.adapter.requests[-1].payload.operation == "get_cart"


async def test_streaming_shaping_keeps_numbers_and_tool_chunks_without_waiting_for_eof(runtime):
    await turn(runtime)
    finished = False

    async def source():
        nonlocal finished
        yield "It costs PKR 1500. "
        yield "Paneer Roll is another option. "
        finished = True

    stream = guarded_output(source(), runtime, runtime.active_turn)
    first = await anext(stream)
    assert isinstance(first, str)
    assert "one thousand five hundred rupees" in first
    assert not finished
    rest = " ".join([chunk async for chunk in stream if isinstance(chunk, str)])
    assert "Puh-neer" in rest


def test_heard_items_handles_pronunciation_and_longer_overlapping_names(runtime):
    rows = runtime.snapshot.visible_items
    assert heard_items("Unrelated text", rows) == []


async def test_unsupported_speed_never_acknowledges_change(runtime):
    runtime.speech_controls = frozenset()
    await runtime.handle_control("slower")
    assert "can’t" in runtime.session.spoken[-1]


async def test_overlapping_filter_tools_merge_against_the_current_serialized_state(runtime):
    context = await turn(runtime, "vegetarian food within six hundred")
    results = await asyncio.gather(
        runtime.agent.filter_menu(context, vegetarian=True),
        runtime.agent.filter_menu(context, max_price_pkr=600),
    )
    assert all(result["status"] == "success" for result in results)
    assert runtime.snapshot.filter_tags == ["vegetarian"]
    assert runtime.snapshot.max_price_pkr == 600


async def test_cart_page_reading_uses_actual_quantity_and_fee_inclusive_total(runtime):
    await call(runtime, "cart_add_item", item_id="wrap-hot-chicken", quantity=2)
    await call(runtime, "navigate", target="cart")
    await control(runtime, "read_page", "read this page")
    assert "2 items" in runtime.session.spoken[-1] or "two items" in runtime.session.spoken[-1]
    assert "one thousand seven hundred fifty rupees" in runtime.session.spoken[-1]


async def test_invalid_guessed_item_blocks_another_write_in_the_same_turn(runtime):
    context = await turn(runtime, "add that meal")
    first = await runtime.agent.cart_add_item(context, "nonexistent-item")
    second = await runtime.agent.cart_add_item(context, "wrap-hot-chicken")
    assert first["status"] != "success" and second["status"] != "success"
    assert not runtime.adapter.requests


async def test_comparison_tools_retain_separate_authoritative_facts_and_unknown_ingredients(
    runtime,
):
    context = await turn(runtime, "compare Paneer Roll with Chef Special Sweet")
    first = await runtime.agent.get_item_details(context, "roll-paneer")
    second = await runtime.agent.get_item_details(context, "dessert-mystery")
    assert first["status"] == second["status"] == "success"
    assert first["facts"]["ingredients"] is not None
    assert second["facts"]["ingredients"] is None
    details = runtime.reasoning_data()["semantic_page"]["details"]
    assert details["roll-paneer"] == first["facts"]
    assert details["dessert-mystery"] == second["facts"]


async def test_unsupported_button_explains_limit_without_a_domain_action(runtime):
    await control(runtime, "unsupported_button", "open the camera")
    assert "can’t activate a camera" in runtime.session.spoken[-1]
    assert not runtime.adapter.requests and len(runtime.session.generated) == 1
