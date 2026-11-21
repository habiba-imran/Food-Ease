"""Scripted semantic tool decisions with real shared website state; no providers."""

import asyncio
import re

import pytest

from foodease_agent.integrated.agent import IntegratedFoodEaseAgent
from foodease_agent.integrated.output import checked_sentence
from foodease_agent.integrated.runtime import LiveConversationRuntime
from test_integrated_runtime import Session, WebsiteAdapter, call, turn


@pytest.fixture
async def urdu():
    adapter = WebsiteAdapter()
    runtime = LiveConversationRuntime(IntegratedFoodEaseAgent(language="ur"), Session(), adapter)
    await runtime.prepare()
    await runtime.select_mode("voice")
    yield runtime
    await runtime.close()


async def test_clear_needs_later_delivered_urdu_confirmation_and_correct_purpose(urdu):
    await call(
        urdu, "cart_add_item", text="دو کولا کارٹ میں شامل کر دو", item_id="drink-cola", quantity=2
    )
    assert (await call(urdu, "cart_clear", text="کارٹ خالی کر دو"))["status"] != "success"
    result = await call(urdu, "cart_get_clear_summary", text="کارٹ خالی کر دو")
    assert "خالی" in result["say"] and not re.search(r"[A-Za-z]", result["say"])
    await asyncio.sleep(0)
    assert urdu.snapshot.cart.lines and urdu.confirmation.summary_spoken
    context = await turn(urdu, "جی ہاں")
    assert (await urdu.agent.checkout_submit_demo_order(context))["status"] != "success"
    assert urdu.snapshot.cart.lines
    assert (await urdu.agent.cart_clear(context))["status"] == "success"
    assert not urdu.snapshot.cart.lines


async def test_clear_same_turn_or_changed_cart_cannot_consume_consent(urdu):
    await call(urdu, "cart_add_item", item_id="drink-cola", quantity=1)
    context = await turn(urdu, "کارٹ خالی کر دو")
    await urdu.agent.cart_get_clear_summary(context)
    await asyncio.sleep(0)
    assert (await urdu.agent.cart_clear(context))["status"] != "success"
    await call(urdu, "cart_get_clear_summary")
    await asyncio.sleep(0)
    await urdu.adapter.manual("cart.add_item", {"item_id": "drink-cola", "quantity": 1})
    urdu.on_context(await urdu.adapter.get_snapshot())
    assert (await call(urdu, "cart_clear", text="haan"))["status"] != "success"
    assert urdu.snapshot.cart.lines[0].quantity == 2


async def test_urdu_and_roman_followups_use_delivered_catalog_and_same_cart(urdu):
    result = await call(
        urdu,
        "filter_menu",
        text="سستا برگر دکھاؤ",
        category="burgers",
        tags=["available"],
        sort_by="price_asc",
    )
    urdu.say(result["say"])
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    first = urdu.references.items[0].item_id
    added = await call(
        urdu, "cart_add_item", text="pehle wale do add kar do", item_id=first, quantity=2
    )
    assert added["status"] == "success"
    assert urdu.snapshot.cart.lines[0].item_id == first
    assert urdu.snapshot.cart.lines[0].quantity == 2
    assert not re.search(r"[A-Za-z]", added["say"])


async def test_unverified_clear_and_navigation_success_are_not_spoken(urdu):
    await turn(urdu, "کارٹ کھول دو")
    for text in ["کارٹ خالی کر دیا ہے۔", "کارٹ کھول دیا ہے۔", "برگر سیکشن کھول دیا ہے۔"]:
        assert "تصدیق" in checked_sentence(urdu, urdu.active_turn, text)
