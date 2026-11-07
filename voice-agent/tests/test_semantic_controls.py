"""Free-form input reaches the model; structured controls validate ownership and state."""

from types import SimpleNamespace

import pytest
from livekit.agents import StopResponse

from test_integrated_runtime import call, control, turn

pytest_plugins = ("test_integrated_runtime",)


@pytest.mark.parametrize(
    "text",
    [
        "goodbye",
        "I'm all finished here, thank you",
        "let's leave it there for today",
        "اب مجھے مزید مدد نہیں چاہیے، بات ختم کر دیں",
        "بس ابھی کے لیے ہماری بات پوری ہو گئی",
        "ab aap ja sakti hain, meri madad ho gayi",
        "I'd like to close this conversation",
    ],
)
async def test_ending_language_is_interpreted_by_model_then_ends_through_tool(runtime, text):
    context = await turn(runtime, text)
    assert not runtime.closed and not runtime.adapter.requests
    with pytest.raises(StopResponse):
        await runtime.agent.conversation_control(context, "end")
    assert runtime.closed and not runtime.session.input.enabled
    assert runtime.adapter.controls == [("end", None)]


@pytest.mark.parametrize(
    "text",
    [
        "don't end the conversation",
        "no juice, show me dessert instead",
        "یہ مت بند کریں، ابھی مجھے کھانا چننا ہے",
        "that's all for the drinks, what desserts are there?",
    ],
)
async def test_negation_and_declining_one_menu_group_do_not_automatically_end(runtime, text):
    await turn(runtime, text)
    assert not runtime.closed and not runtime.adapter.controls


async def test_stale_speech_cannot_end_a_newer_turn(runtime):
    old = await turn(runtime, "we can wrap things up")
    await turn(runtime, "actually continue")
    result = await runtime.agent.conversation_control(old, "end")
    assert result["status"] != "success" and not runtime.closed


async def test_control_cannot_run_from_another_session(runtime):
    context = await turn(runtime, "finish helping")
    forged = SimpleNamespace(session=object(), speech_handle=context.speech_handle)
    result = await runtime.agent.conversation_control(forged, "end")
    assert result["status"] != "success" and not runtime.closed


async def test_invalid_intent_is_not_an_arbitrary_application_operation(runtime):
    context = await turn(runtime, "help me")
    result = await runtime.agent.conversation_control(context, "checkout.submit_demo_order")
    assert result["status"] != "success"
    assert not runtime.adapter.requests and not runtime.closed


async def test_onboarding_model_has_only_control_tool_and_cannot_shop(runtime):
    runtime.mode = "choosing"
    context = await turn(runtime, "I'd prefer you to talk me through the ordering process")
    assert runtime.session.generated[-1]["tools"] == ["conversation_control"]
    assert "page" not in runtime.reasoning_data()
    result = await runtime.agent.cart_add_item(context, runtime.snapshot.visible_items[0].item_id)
    assert result["status"] != "success" and not runtime.adapter.requests
    with pytest.raises(StopResponse):
        await runtime.agent.conversation_control(context, "voice")
    assert runtime.mode == "voice"
    assert runtime.adapter.controls == [("switch_mode", "voice")]


async def test_unknown_control_is_rejected_before_any_effect(runtime):
    context = await turn(runtime, "do something unsupported")
    assert (await runtime.agent.conversation_control(context, "open_camera"))["status"] != "success"
    assert not runtime.adapter.requests and not runtime.adapter.controls


async def test_pause_allows_semantic_resume_but_not_shopping(runtime):
    context = await turn(runtime, "give me a little breathing room")
    with pytest.raises(StopResponse):
        await runtime.agent.conversation_control(context, "pause")
    assert runtime.paused
    context = await turn(runtime, "let's carry on from where we were")
    assert runtime.session.generated[-1]["tools"] == ["conversation_control"]
    result = await runtime.agent.search_menu(context, "burger")
    assert result["status"] != "success" and not runtime.adapter.requests
    with pytest.raises(StopResponse):
        await runtime.agent.conversation_control(context, "resume")
    assert not runtime.paused


async def test_ending_during_pending_cart_write_does_not_cancel_or_repeat_it(runtime):
    import asyncio

    item = runtime.snapshot.visible_items[0].item_id
    runtime.adapter.release.clear()
    pending = asyncio.create_task(call(runtime, "cart_add_item", item_id=item, quantity=1))
    await runtime.adapter.started.wait()
    await control(runtime, "end", "that's enough assistance for now")
    assert runtime.closed and not runtime.session.input.enabled
    runtime.adapter.release.set()
    await pending
    await runtime.drain()
    assert len(runtime.adapter.requests) == 1
    assert (await runtime.adapter.get_snapshot()).cart.lines[0].quantity == 1


async def test_duplicate_control_or_business_action_after_control_is_rejected(runtime):
    context = await control(runtime, "read_page", "orient me here")
    count = len(runtime.adapter.requests)
    assert (await runtime.agent.conversation_control(context, "next"))["status"] != "success"
    assert (await runtime.agent.cart_add_item(context, runtime.snapshot.visible_items[0].item_id))[
        "status"
    ] != "success"
    assert len(runtime.adapter.requests) == count


async def test_onboarding_can_clarify_through_model_without_authorizing_shopping(runtime):
    from foodease_agent.integrated.output import checked_sentence

    runtime.mode = "choosing"
    context = await turn(runtime, "maybe, I'm not sure which way to do this")
    question = "Would you prefer speaking or typing?"
    assert checked_sentence(runtime, runtime.active_turn, question) == question
    assert (await runtime.agent.conversation_control(context, "read_cart"))["status"] != "success"
    assert not runtime.adapter.requests


async def test_muted_input_cannot_bypass_control_only_lane_to_change_cart(runtime):
    await control(runtime, "mute", "I need a quiet moment")
    context = await turn(runtime, "change my cart", source="text")
    assert runtime.session.generated[-1]["tools"] == ["conversation_control"]
    assert (await runtime.agent.cart_add_item(context, runtime.snapshot.visible_items[0].item_id))[
        "status"
    ] != "success"
    assert (await runtime.agent.conversation_control(context, "undo"))["status"] != "success"
    assert not runtime.adapter.requests


async def test_real_sdk_invokes_control_tool_and_stops_without_followup_generation():
    import asyncio
    from uuid import uuid4

    from livekit.agents import AgentSession, llm
    from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS

    from foodease_agent.integrated.agent import IntegratedFoodEaseAgent
    from foodease_agent.integrated.runtime import LiveConversationRuntime
    from test_integrated_runtime import WebsiteAdapter

    class LocalLLM(llm.LLM):
        def __init__(self):
            super().__init__()
            self.calls = 0

        def chat(self, *, chat_ctx, tools=None, conn_options=DEFAULT_API_CONNECT_OPTIONS, **kwargs):
            self.calls += 1
            return LocalStream(
                self, chat_ctx=chat_ctx, tools=tools or [], conn_options=conn_options
            )

    class LocalStream(llm.LLMStream):
        async def _run(self):
            self._event_ch.send_nowait(
                llm.ChatChunk(
                    id=uuid4().hex,
                    delta=llm.ChoiceDelta(
                        tool_calls=[
                            llm.FunctionToolCall(
                                name="conversation_control",
                                arguments='{"intent":"end"}',
                                call_id=uuid4().hex,
                            )
                        ],
                    ),
                )
            )

    provider, adapter = LocalLLM(), WebsiteAdapter()
    session = AgentSession(llm=provider)
    runtime = LiveConversationRuntime(IntegratedFoodEaseAgent(), session, adapter)
    await runtime.prepare()
    await runtime.select_mode("typed")
    try:
        await session.start(agent=runtime.agent)
        handle = await runtime.input_text(
            "let's leave it here", "native-end", runtime.snapshot.revision
        )
        await asyncio.wait_for(handle.wait_for_playout(), 5)
        assert runtime.closed and adapter.controls == [("end", None)]
        assert provider.calls == 1
        assert not adapter.requests
    finally:
        await runtime.close()
        await session.aclose()
