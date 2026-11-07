"""Urdu provider wiring, localized delivery and code-owned safety; no provider calls."""

import asyncio
import re
from dataclasses import replace

import pytest

from foodease_agent.config import ConfigError, load_config
from foodease_agent.integrated.agent import IntegratedFoodEaseAgent
from foodease_agent.integrated.runtime import LiveConversationRuntime
from foodease_agent.session import build_session_kwargs, build_stt, build_tts
from test_config import _complete_environ
from test_integrated_runtime import Session, WebsiteAdapter, call, control, turn
from test_phase5_voice import _settings


@pytest.fixture
async def urdu():
    adapter = WebsiteAdapter()
    runtime = LiveConversationRuntime(IntegratedFoodEaseAgent(language="ur"), Session(), adapter)
    await runtime.prepare()
    await runtime.select_mode("voice")
    yield runtime
    adapter.release.set()
    await runtime.close()


def test_existing_installation_defaults_to_urdu_without_editing_private_env():
    environ = _complete_environ()
    environ.pop("ASSISTANT_LANGUAGE", None)
    settings = load_config(environ=environ)
    assert settings.assistant_language == "ur"
    assert settings.urdu_stt_model == "whisper-large-v3-turbo"


def test_urdu_requires_its_recognition_key_even_with_gemini():
    environ = _complete_environ(ASSISTANT_LANGUAGE="ur", LLM_PROVIDER="gemini")
    environ.pop("GROQ_API_KEY")
    with pytest.raises(ConfigError, match="GROQ_API_KEY"):
        load_config(environ=environ)


def test_urdu_stt_and_tts_use_actual_language_settings(monkeypatch):
    from foodease_agent import session

    captured = {}
    monkeypatch.setattr(session.groq, "STT", lambda **kwargs: captured.update(stt=kwargs))
    monkeypatch.setattr(session.cartesia, "TTS", lambda **kwargs: captured.update(tts=kwargs))
    settings = replace(_settings(), assistant_language="ur", groq_api_key="<groq-key>")
    build_stt(settings, "A")
    build_tts(settings)
    assert captured["stt"]["model"] == "whisper-large-v3-turbo"
    assert captured["stt"]["language"] == captured["tts"]["language"] == "ur"
    assert captured["tts"]["word_timestamps"] is False


def test_urdu_uses_vad_without_english_turn_detector(monkeypatch):
    from foodease_agent import session

    marker = object()
    for name in ("build_stt", "build_tts", "build_llm"):
        monkeypatch.setattr(session, name, lambda *args: marker)
    monkeypatch.setattr(session.silero.VAD, "load", lambda: marker)
    monkeypatch.setattr(session.inference, "TurnDetector", lambda: pytest.fail("English detector"))
    bundle = build_session_kwargs(replace(_settings(), assistant_language="ur"))
    assert bundle.session_kwargs["turn_handling"]["turn_detection"] == "vad"
    assert bundle.session_kwargs["use_tts_aligned_transcript"] is False


async def test_urdu_opening_and_voice_choice_never_generate_english(urdu):
    urdu.mode = None
    await urdu.open_mode_choice()
    assert "خوش آمدید" in urdu.session.spoken[-1]
    await control(urdu, "voice", "میں آواز سے آرڈر کرنا چاہتی ہوں")
    assert urdu.mode == "voice"
    assert len(urdu.session.generated) == 1 and not urdu.adapter.requests
    assert all(not re.search(r"[A-Za-z]", text) for text in urdu.session.spoken)


async def test_urdu_tools_deliver_catalog_prices_and_heard_references(urdu):
    result = await call(urdu, "search_menu", text="جوس کون سے ہیں؟", query="juice", read_all=True)
    assert "آم کا جوس" in result["say"] and "دو سو روپے" in result["say"]
    urdu.say(result["say"])
    await asyncio.sleep(0)
    assert [row.item_id for row in urdu.references.items] == ["drink-mango"]
    await control(urdu, "open_reference", "پہلا کھولیں")
    assert urdu.snapshot.focus_item_id == "drink-mango"


async def test_urdu_stop_intent_runs_validated_control_and_blocks_further_actions(urdu):
    await turn(urdu, "کچھ کھانے کو بتائیں")
    await control(urdu, "stop", "رک جائیں۔")
    assert len(urdu.session.generated) == 2
    assert urdu.active_turn.discarded
    assert not urdu.adapter.requests


async def test_urdu_cart_confirmation_requires_delivered_summary_and_exact_consent(urdu):
    await call(urdu, "cart_add_item", item_id="drink-mango", quantity=2)
    summary = await call(urdu, "checkout_get_summary")
    await asyncio.sleep(0)
    assert "آم کا جوس" in summary["say"] and "چار سو پچاس روپے" in summary["say"]
    assert not re.search(r"[A-Za-z]", summary["say"])
    assert urdu.confirmation.summary_spoken
    context = await turn(urdu, "جی ہاں، لیکن ایک کر دیں")
    assert (await urdu.agent.checkout_submit_demo_order(context))["status"] != "success"
    await call(urdu, "checkout_get_summary")
    await asyncio.sleep(0)
    context = await turn(urdu, "جی ہاں")
    assert (await urdu.agent.checkout_submit_demo_order(context))["status"] == "success"


async def test_urdu_rate_limit_warning_uses_urdu(urdu):
    from types import SimpleNamespace

    error = SimpleNamespace(
        type="llm_error", recoverable=False, error=SimpleNamespace(status_code=429)
    )
    urdu.recovery.provider_error(SimpleNamespace(error=error))
    assert urdu.mode == "voice" and error.recoverable
    assert not re.search(r"[A-Za-z]", urdu.session.spoken[-1])


async def test_urdu_complete_budget_list_and_captions_remain_complete(urdu):
    from foodease_agent.integrated.conversation import heard_items

    result = await call(
        urdu, "filter_menu", max_price_pkr=1000, price_exclusive=True, read_all=True
    )
    assert result["status"] == "success"
    assert len(result["facts"]["items"]) == 25
    assert heard_items(result["say"], urdu.snapshot.visible_items) == urdu.snapshot.visible_items
    urdu.say(result["say"])
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    captions = [
        payload
        for event, payload, _ in urdu.adapter.events
        if event == "transcript.assistant" and payload["phase"] == "completed"
    ]
    assert captions[-1]["text"] == urdu.session.spoken[-1]
    assert not re.search(r"[A-Za-z]", captions[-1]["text"])


def test_catalog_presentation_labels_cover_current_items_without_synonym_logic():
    import json
    from pathlib import Path

    from foodease_agent.i18n import label

    catalog = json.loads(
        (Path(__file__).resolve().parents[2] / "zainab-pack/catalog-seed.json").read_text(
            encoding="utf-8"
        )
    )
    assert all(not re.search(r"[A-Za-z]", label(row["name"], "ur")) for row in catalog["items"])


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("قیمت 200 روپے ہے۔", "دو سو روپے"),
        ("قیمت 0.01 روپے ہے۔", "صفر اعشاریہ صفر ایک روپے"),
        ("قیمت 1500 روپے ہے۔", "ایک ہزار پانچ سو روپے"),
    ],
)
def test_urdu_numbers_do_not_pass_through_english_verbalizer(text, expected):
    from foodease_agent.speech_text.shaping import shape_assistant_reply

    assert expected in shape_assistant_reply(text, language="ur").spoken_text


async def test_urdu_streaming_output_blocks_unverified_outcomes_and_english(urdu):
    from foodease_agent.integrated.output import checked_sentence

    await turn(urdu, "جوس شامل کر دیں")
    blocked = checked_sentence(urdu, urdu.active_turn, "آم کا جوس ٹوکری میں شامل کر دیا ہے۔")
    assert "تصدیق" in blocked
    question = "کیا آم کا جوس شامل کر دوں؟"
    assert checked_sentence(urdu, urdu.active_turn, question) == question
    english = checked_sentence(urdu, urdu.active_turn, "How can I help?")
    assert not re.search(r"[A-Za-z]", english)


async def test_missing_catalog_translation_never_marks_summary_delivered(urdu, monkeypatch):
    from foodease_agent.i18n import urdu_resources

    await call(urdu, "cart_add_item", item_id="drink-mango", quantity=1)
    monkeypatch.delitem(urdu_resources()["labels"], "Mango Juice")
    result = await call(urdu, "checkout_get_summary")
    assert result["status"] != "success"
    assert not urdu.confirmation.summary_spoken


async def test_actual_urdu_provider_clients_construct_without_network():
    settings = replace(_settings(), assistant_language="ur", groq_api_key="<groq-key>")
    stt, tts = build_stt(settings, "A"), build_tts(settings)
    try:
        assert not stt.capabilities.streaming
        assert not tts.capabilities.aligned_transcript
    finally:
        await stt.aclose()
        await tts.aclose()


async def test_production_factory_passes_urdu_setting_to_agent_and_runtime(monkeypatch):
    from types import SimpleNamespace

    from foodease_agent.integrated import factory
    from foodease_agent.session import SessionBundle

    adapter = WebsiteAdapter()
    monkeypatch.setattr(
        factory, "load_config", lambda: replace(_settings(), assistant_language="ur")
    )
    monkeypatch.setattr(factory, "IntegratedRpcAdapter", lambda gate: adapter)
    monkeypatch.setattr(
        factory, "build_session_kwargs", lambda settings, **kwargs: SessionBundle({}, "B", False)
    )
    monkeypatch.setattr(factory, "AgentSession", lambda **kwargs: Session())
    runtime = await factory.create_integrated_runtime(
        SimpleNamespace(proc=SimpleNamespace(userdata={})),
        None,
        None,
    )
    try:
        assert runtime.language == runtime.agent.language == "ur"
        await runtime.open_mode_choice()
        assert "خوش آمدید" in runtime.session.spoken[-1]
    finally:
        await runtime.close()
