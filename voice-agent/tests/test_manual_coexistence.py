"""Manual browsing cooperates with speech without rescuing old tool authority."""

import asyncio
from types import SimpleNamespace

import pytest

from foodease_agent.integrated.agent import IntegratedFoodEaseAgent
from foodease_agent.integrated.output import guarded_output
from foodease_agent.integrated.runtime import LiveConversationRuntime
from test_integrated_runtime import Session, Speech, WebsiteAdapter, turn


class Boundary:
    def __init__(self):
        self.handlers = {}

    def on(self, event, callback):
        self.handlers[event] = callback

    def off(self, event, callback):
        self.handlers.pop(event, None)

    def finish_sentence(self):
        self.handlers["playback_finished"](SimpleNamespace(interrupted=False))


class PlayingSession(Session):
    def __init__(self):
        super().__init__()
        self.output.audio = Boundary()

    def say(self, text, **kwargs):
        handle = Speech(text)
        self.spoken.append(text)
        self.handles.append(handle)
        self.emit("speech_created", speech_handle=handle, source="say", user_initiated=True)
        return handle


@pytest.fixture
async def playing():
    runtime = LiveConversationRuntime(
        IntegratedFoodEaseAgent(language="ur"), PlayingSession(), WebsiteAdapter()
    )
    await runtime.prepare()
    await runtime.select_mode("voice")
    yield runtime
    await runtime.close()


async def settle():
    for _ in range(8):
        await asyncio.sleep(0)


async def test_cart_add_does_not_cut_off_menu_reading_but_old_tools_lose_permission(playing):
    context = await turn(playing, "برگر کی قیمتیں بتائیں")
    speech = playing.say("زنگر برگر چھ سو پچاس روپے ہے۔ ایک اور قسم بھی ہے۔", scope="menu")
    await playing.adapter.manual("cart.add_item", {"item_id": "drink-cola", "quantity": 1})
    playing.on_context(await playing.adapter.get_snapshot(), source_turn="manual-cart")
    assert not speech.interrupted
    before = len(playing.adapter.requests)
    result = await playing.agent.cart_add_item(context, "drink-cola", 2)
    assert result["status"] != "success"
    assert len(playing.adapter.requests) == before
    assert playing.snapshot.cart.lines[0].quantity == 1


async def test_new_category_finishes_current_sentence_then_acknowledges_latest_view(playing):
    speech = playing.say("پہلا کھانا ہے۔ پرانے حصے کا دوسرا کھانا ہے۔", scope="menu")
    await playing.adapter.manual("navigate", {"target": "karahi"})
    playing.on_context(await playing.adapter.get_snapshot(), source_turn="manual-category")
    assert not speech.interrupted
    playing.session.output.audio.finish_sentence()
    await settle()
    assert speech.interrupted
    assert "کڑاہی" in playing.session.spoken[-1]


async def test_cart_change_stops_old_total_immediately_and_reads_fresh_cart(playing):
    await playing.adapter.manual("cart.add_item", {"item_id": "drink-cola", "quantity": 1})
    playing.on_context(await playing.adapter.get_snapshot(), source_turn="manual-setup")
    speech = playing.say("کل رقم ایک سو روپے ہے۔", scope="cart")
    await playing.adapter.manual("cart.set_quantity", {"item_id": "drink-cola", "quantity": 2})
    playing.on_context(await playing.adapter.get_snapshot(), source_turn="manual-quantity")
    assert speech.interrupted
    await settle()
    assert playing.snapshot.cart.lines[0].quantity == 2
    assert playing.session.spoken[-1] != "کل رقم ایک سو روپے ہے۔"


async def test_stop_and_new_user_turn_cancel_pending_manual_followup(playing):
    speech = playing.say("پہلا جملہ۔ دوسرا جملہ۔", scope="menu")
    await playing.adapter.manual("navigate", {"target": "burgers"})
    playing.on_context(await playing.adapter.get_snapshot(), source_turn="manual-category")
    await playing.handle_control("stop")
    before = len(playing.session.spoken)
    assert speech.interrupted
    playing.session.output.audio.finish_sentence()
    await settle()
    assert len(playing.session.spoken) == before


async def test_greeting_survives_unrelated_cart_change(playing):
    speech = playing.say("میں حاضر ہوں۔ آپ کیا کھانا چاہیں گے؟")
    await playing.adapter.manual("cart.add_item", {"item_id": "drink-cola", "quantity": 1})
    playing.on_context(await playing.adapter.get_snapshot(), source_turn="manual-add")
    await settle()
    assert not speech.interrupted
    assert len(playing.session.spoken) == 1


async def test_generated_scope_is_private_and_unrelated_cart_edit_preserves_small_talk(playing):
    await turn(playing, "آپ کیسی ہیں؟")
    handle = playing.session.handles[-1]

    async def chunks():
        yield "<voice_sc"
        yield "ope:general> میں ٹھیک ہوں۔ "

    text = "".join(
        [
            c
            async for c in guarded_output(chunks(), playing, playing.active_turn)
            if isinstance(c, str)
        ]
    )
    assert "voice_scope" not in text and "میں ٹھیک ہوں" in text
    await playing.adapter.manual("cart.add_item", {"item_id": "drink-cola", "quantity": 1})
    playing.on_context(await playing.adapter.get_snapshot(), source_turn="manual-add")
    assert not handle.interrupted
    assert not playing.authorized(playing.active_turn)
    assert playing.can_speak(playing.active_turn)


async def test_rapid_category_clicks_acknowledge_only_the_last_selection(playing):
    speech = playing.say("پہلا جملہ۔ دوسرا جملہ۔", scope="menu")
    for category in ("burgers", "karahi"):
        await playing.adapter.manual("navigate", {"target": category})
        playing.on_context(await playing.adapter.get_snapshot(), source_turn="manual-category")
    playing.session.output.audio.finish_sentence()
    await settle()
    assert speech.interrupted
    assert len(playing.session.spoken) == 2
    assert "کڑاہی" in playing.session.spoken[-1]


async def test_new_voice_input_cancels_a_manual_followup_already_reading_context(playing):
    playing.say("پہلا جملہ۔ دوسرا جملہ۔", scope="menu")
    await playing.adapter.manual("navigate", {"target": "burgers"})
    playing.on_context(await playing.adapter.get_snapshot(), source_turn="manual-category")
    original = playing.adapter.get_snapshot
    started, release = asyncio.Event(), asyncio.Event()

    async def delayed():
        started.set()
        await release.wait()
        return await original()

    playing.adapter.get_snapshot = delayed
    playing.session.output.audio.finish_sentence()
    await started.wait()
    await turn(playing, "رکیں، مجھے کچھ اور پوچھنا ہے")
    before = len(playing.session.spoken)
    release.set()
    await settle()
    assert len(playing.session.spoken) == before


async def test_cart_review_cannot_be_completed_or_confirmed_after_manual_quantity_change(playing):
    context = await turn(playing, "کولا شامل کرو")
    await playing.agent.cart_add_item(context, "drink-cola", 1)
    context = await turn(playing, "آرڈر کا جائزہ سناؤ")
    await playing.agent.checkout_get_summary(context)
    summary = playing.session.handles[-1]
    assert not playing.confirmation.summary_spoken
    await playing.adapter.manual("cart.set_quantity", {"item_id": "drink-cola", "quantity": 2})
    playing.on_context(await playing.adapter.get_snapshot(), source_turn="manual-quantity")
    assert summary.interrupted
    await settle()
    assert not playing.confirmation.summary_spoken
    context = await turn(playing, "جی ہاں")
    result = await playing.agent.checkout_submit_demo_order(context)
    assert result["status"] != "success"
    assert not any(
        r.payload.operation == "checkout.submit_demo_order" for r in playing.adapter.requests
    )


async def test_noop_context_revision_keeps_review_audio_and_delivery_but_not_old_tool_permission(
    playing,
):
    context = await turn(playing, "کولا شامل کرو")
    await playing.agent.cart_add_item(context, "drink-cola", 1)
    context = await turn(playing, "آرڈر کا جائزہ سناؤ")
    await playing.agent.checkout_get_summary(context)
    summary = playing.session.handles[-1]
    playing.on_context(
        playing.snapshot.model_copy(update={"revision": playing.snapshot.revision + 1}),
        source_turn="manual-noop",
    )
    assert not summary.interrupted
    summary.future.set_result(None)
    await settle()
    assert playing.confirmation.summary_spoken
    assert not playing.authorized(playing.active_turn)


async def test_cart_receipts_override_an_optimistic_model_scope(playing):
    context = await turn(playing, "کارٹ میں کیا ہے؟")
    await playing.agent.get_cart(context)
    playing.manual.generated_scope(playing.active_turn, "general")
    handle = context.speech_handle
    await playing.adapter.manual("cart.add_item", {"item_id": "drink-cola", "quantity": 1})
    playing.on_context(await playing.adapter.get_snapshot(), source_turn="manual-add")
    assert handle.interrupted
