"""Test campaign preparation/guarding; fixtures never constitute model evidence."""

import importlib.util
import json
import logging
from pathlib import Path

import pytest


@pytest.fixture
def campaign(monkeypatch):
    folder = Path(__file__).resolve().parents[2] / "orchestration/tools"
    monkeypatch.syspath_prepend(str(folder))
    spec = importlib.util.spec_from_file_location("campaign_p7", folder / "phase7_campaign.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_prepare_has_unrun_human_gate_and_preserves_ratings(campaign, tmp_path):
    cases = campaign.prepare(tmp_path)
    assert len(cases) >= 40
    assert sum(len(case["utterances"]) for case in cases) >= 40
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["real_model_turns"] == 0
    assert manifest["human_listeners"] == 0
    assert manifest["model_quality_gate"] == "not_evaluated"
    ratings = tmp_path / "listening-ratings.csv"
    original = ratings.read_bytes()
    assert b"live_audio_reference" in original
    ratings.write_bytes(original + b"preserved reviewer note\n")
    campaign.prepare(tmp_path)
    assert ratings.read_bytes() == original + b"preserved reviewer note\n"


def test_live_campaign_requires_explicit_cost_flag(campaign, monkeypatch, tmp_path):
    monkeypatch.setattr("sys.argv", ["campaign", "--output", str(tmp_path), "--live"])
    with pytest.raises(SystemExit) as error:
        campaign.main()
    assert error.value.code == 2


def test_live_campaign_without_environment_key_cannot_start(campaign, monkeypatch, tmp_path):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setattr(
        "sys.argv",
        [
            "campaign",
            "--output",
            str(tmp_path),
            "--live",
            "--allow-provider-cost",
            "--model",
            "test-only-model",
            "--thinking-level",
            "minimal",
        ],
    )
    with pytest.raises(SystemExit) as error:
        campaign.main()
    assert error.value.code == 2


async def test_campaign_driver_with_local_model_fixture_uses_real_http_authority(
    campaign, monkeypatch, tmp_path
):
    from livekit.agents import llm
    from livekit.plugins import google

    class LocalLLM(llm.LLM):
        def __init__(self, **kwargs):
            super().__init__()

        def chat(self, *, chat_ctx, tools=None, conn_options, **kwargs):
            return LocalStream(
                self, chat_ctx=chat_ctx, tools=tools or [], conn_options=conn_options
            )

    class LocalStream(llm.LLMStream):
        async def _run(self):
            has_output = any(
                isinstance(item, llm.FunctionCallOutput) for item in self._chat_ctx.items
            )
            delta = (
                llm.ChoiceDelta(content="Your cart is empty.")
                if has_output
                else llm.ChoiceDelta(
                    tool_calls=[
                        llm.FunctionToolCall(name="get_cart", arguments="{}", call_id="fixture")
                    ]
                )
            )
            self._event_ch.send_nowait(llm.ChatChunk(id="fixture", delta=delta))

    monkeypatch.setattr(google, "LLM", LocalLLM)
    cases = [
        {
            "id": "LOCAL-FIXTURE",
            "source": "not-real-model-evidence",
            "utterances": ["Please review my basket."],
            "setup": [],
            "expected_operations": ["get_cart"],
            "forbidden_operations": ["checkout.submit_demo_order"],
        }
    ]
    previous_logging = logging.root.manager.disable
    try:
        await campaign.run(
            tmp_path, cases, model="test-local-fixture", thinking="minimal", request_limit=4
        )
    finally:
        logging.disable(previous_logging)
    result = json.loads((tmp_path / "results.json").read_text())[0]
    assert "error_type" not in result
    assert result["required_operations_observed"]
    assert result["final_cart"]["total"] == 0
    assert result["turns"][0]["assistant"] == "Your cart is empty."
