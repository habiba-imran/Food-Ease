"""Natural Urdu regressions use real shopping authority, with no paid providers."""

import asyncio

import pytest

from foodease_agent.integrated.conversation import reference_item
from foodease_agent.integrated.output import checked_sentence
from foodease_agent.integrated.policy import explicit_yes, has_reference
from foodease_agent.reference import PresentedItem
from foodease_agent.speech_text.shaping import shape_assistant_reply
from test_integrated_runtime import call, control, turn

pytest_plugins = ("test_urdu_assistant",)


@pytest.mark.parametrize("text", ["doosra wala", "pehla wala", "uske do kar do", "isko hata do"])
def test_roman_urdu_references_are_validated_in_code(text):
    assert has_reference(text)
    rows = [PresentedItem("one", "One", 100), PresentedItem("two", "Two", 200)]
    assert reference_item(text, rows, "two") == ("one" if "pehla" in text else "two")


@pytest.mark.parametrize("text", ["haan kar do", "ji haan", "jee haan", "han", "جی ہاں،"])
def test_short_roman_and_spoken_urdu_confirmation(text):
    assert explicit_yes(text)


@pytest.mark.parametrize(
    "text", ["haan lekin ek kar do", "ji haan magar nahi", "haan?", "nahi haan"]
)
def test_corrections_and_questions_are_not_confirmation(text):
    assert not explicit_yes(text)


async def test_urdu_budget_drinks_multi_cart_update_remove_and_total(urdu):
    burgers = await call(
        urdu, "filter_menu", category="burgers", max_price_pkr=700, price_exclusive=True
    )
    assert burgers["facts"]["items"]
    assert all(row["price"] < 700 for row in burgers["facts"]["items"])
    drinks = await call(
        urdu, "filter_menu", category="drinks", max_price_pkr=500, price_exclusive=True
    )
    assert all(row["price"] < 500 for row in drinks["facts"]["items"])
    assert (await call(urdu, "cart_add_item", item_id="drink-mango", quantity=2))[
        "status"
    ] == "success"
    assert (await call(urdu, "cart_add_item", item_id="drink-cola", quantity=2))[
        "status"
    ] == "success"
    await call(urdu, "cart_set_quantity", item_id="drink-cola", quantity=1)
    await call(urdu, "cart_remove_item", item_id="drink-cola")
    result = await call(urdu, "get_cart")
    assert len(urdu.snapshot.cart.lines) == 1
    assert urdu.snapshot.cart.lines[0].quantity == 2
    assert result["facts"]["total"] == urdu.snapshot.cart.total == 450
    assert "چار سو پچاس روپے" in result["say"]


async def test_urdu_categories_manual_choice_and_unavailable_item(urdu):
    await control(urdu, "read_categories", "saari categories batao")
    assert "برگر" in urdu.session.spoken[-1] and "مشروبات" in urdu.session.spoken[-1]
    # Shipped catalog currently has every item available; simulate real stock loss.
    sold_out = urdu.snapshot.visible_items[0]
    shopping = urdu.adapter.store._sessions[urdu.adapter.session_id]
    shopping.domain.menu_by_id[sold_out.item_id].available = False
    result = await call(urdu, "cart_add_item", item_id=sold_out.item_id, quantity=1)
    assert result["status"] != "success" and not urdu.snapshot.cart.lines
    await control(urdu, "manual", "main khud order karoon gi")
    assert urdu.mode == "manual" and not urdu.session.input.enabled


async def test_roman_ordinal_uses_delivered_order_and_duplicate_mutation_is_blocked(urdu):
    result = await call(urdu, "filter_menu", category="drinks", read_all=True)
    urdu.say(result["say"])
    await asyncio.sleep(0)
    wanted = urdu.references.items[1].item_id
    context = await turn(urdu, "doosra wala ek add kar do")
    first = await urdu.agent.cart_add_item(
        context, item_id=urdu.references.items[0].item_id, quantity=1
    )
    again = await urdu.agent.cart_add_item(context, item_id=wanted, quantity=1)
    assert first["status"] == "success" and again["status"] != "success"
    assert urdu.snapshot.cart.lines[0].item_id == wanted
    assert urdu.snapshot.cart.lines[0].quantity == 1


@pytest.mark.parametrize(
    "text", ["ایڈ کر دیا!", "جی، برگر کارٹ میں آ گیا ہے۔", "ہو گیا!", "آرڈر ہو گیا۔"]
)
async def test_natural_success_wording_cannot_bypass_outcome_guard(urdu, text):
    await turn(urdu, "ایک برگر ایڈ کریں")
    assert "تصدیق" in checked_sentence(urdu, urdu.active_turn, text)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("**قیمت** PKR 1,500.50 ہے۔", "ایک ہزار پانچ سو اعشاریہ پانچ صفر"),
        ('[warm] <emotion value="calm"/> جی، بولیے۔', "جی، بولیے۔"),
    ],
)
def test_speech_removes_director_markup_and_normalizes_currency(text, expected):
    spoken = shape_assistant_reply(text, language="ur").spoken_text
    assert expected in spoken
    assert not any(mark in spoken for mark in ("*", "<", ">", "[", "]", "PKR", "warm"))


async def test_price_sort_uses_verified_rows_and_remembers_delivered_order(urdu):
    result = await call(urdu, "filter_menu", category="drinks", sort_by="price_asc")
    rows = result["facts"]["items"]
    assert [row["price"] for row in rows] == sorted(row["price"] for row in rows)
    assert rows[0]["name"] in {row.name for row in urdu.snapshot.visible_items}
    urdu.say(result["say"])
    await asyncio.sleep(0)
    assert urdu.references.items[0].item_id == rows[0]["item_id"]
    assert [row.item_id for row in urdu.references.items] == [row["item_id"] for row in rows[:3]]


async def test_invalid_sort_cannot_mutate_filters(urdu):
    result = await call(urdu, "filter_menu", sort_by="invented", clear_search=True)
    assert result["status"] != "success" and not urdu.adapter.requests


async def test_roman_quantity_correction_updates_last_real_cart_item(urdu):
    await call(urdu, "cart_add_item", item_id="drink-mango", quantity=1)
    context = await turn(urdu, "uske do kar do")
    result = await urdu.agent.cart_set_quantity(context, item_id="drink-cola", quantity=2)
    assert result["status"] == "success"
    assert urdu.snapshot.cart.lines[0].item_id == "drink-mango"
    assert urdu.snapshot.cart.lines[0].quantity == 2
    # A quantity update is not a witness for claiming a separate add succeeded.
    assert "تصدیق" in checked_sentence(urdu, urdu.active_turn, "ایڈ کر دیا!")
