import json
from types import SimpleNamespace

from foodease_agent.production_metrics import metric_record


def test_metrics_are_seconds_at_source_and_not_claimed_as_audible_latency():
    event = SimpleNamespace(
        metrics=SimpleNamespace(
            type="llm_metrics",
            ttft=0.25,
            duration=1.5,
            speech_id="turn-one",
            transcript="private",
            api_key="secret",
        )
    )
    result = metric_record(event)
    assert result["ttft_ms"] == 250
    assert result["duration_ms"] == 1500
    assert "private" not in json.dumps(result) and "secret" not in json.dumps(result)
    assert "audible_ttfa_ms" not in result


def test_unavailable_and_nonfinite_metrics_are_not_fabricated():
    result = metric_record(
        SimpleNamespace(metrics=SimpleNamespace(type="tts_metrics", ttfb=-1, duration=float("nan")))
    )
    assert "ttfb_ms" not in result and "duration_ms" not in result


def test_prewarmed_vad_is_reused_without_constructing_another(monkeypatch):
    from foodease_agent import session
    from test_phase5_voice import _settings

    marker = object()
    for name in ("build_stt", "build_tts", "build_llm"):
        monkeypatch.setattr(session, name, lambda *args: marker)
    monkeypatch.setattr(
        session.silero.VAD, "load", lambda: (_ for _ in ()).throw(AssertionError("cold VAD"))
    )
    bundle = session.build_session_kwargs(_settings(assistant_language="ur"), prewarmed_vad=marker)
    assert bundle.session_kwargs["vad"] is marker


def test_current_message_metrics_exclude_text_and_server_playback_as_audible_measurement():
    result = metric_record(
        SimpleNamespace(
            item=SimpleNamespace(
                role="assistant",
                content=["private"],
                metrics={"llm_node_ttft": 0.2, "tts_node_ttfb": 0.4, "playback_latency": 0.01},
            )
        )
    )
    assert result["llm_node_ttft_ms"] == 200
    assert result["tts_node_ttfb_ms"] == 400
    assert "playback_latency_ms" not in result
    assert "private" not in json.dumps(result)
