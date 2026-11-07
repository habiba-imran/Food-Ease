"""Allowlisted SDK stage timings; never transcripts, keys or caller-heard claims."""

from __future__ import annotations

import json
import logging
import math

logger = logging.getLogger("foodease.performance")


def metric_record(event) -> dict:
    if item := getattr(event, "item", None):
        result = {"source": "livekit_message_metrics", "role": getattr(item, "role", "unknown")}
        for name in (
            "transcription_delay",
            "end_of_turn_delay",
            "on_user_turn_completed_delay",
            "llm_node_ttft",
            "llm_node_ttfs",
            "tts_node_ttfb",
        ):
            value = getattr(item, "metrics", {}).get(name)
            if isinstance(value, (int, float)) and math.isfinite(value) and value >= 0:
                result[name + "_ms"] = round(value * 1000, 2)
        return result
    metric = event.metrics
    result = {"source": "livekit_sdk", "metric_type": metric.type}
    for name in (
        "duration",
        "ttft",
        "ttfb",
        "end_of_utterance_delay",
        "transcription_delay",
        "on_user_turn_completed_delay",
        "audio_duration",
        "acquire_time",
    ):
        value = getattr(metric, name, None)
        if isinstance(value, (int, float)) and math.isfinite(value) and value >= 0:
            result[name + "_ms"] = round(value * 1000, 2)
    if speech_id := getattr(metric, "speech_id", None):
        result["speech_id"] = speech_id
    return result


def log_metrics(event) -> None:
    result = metric_record(event)
    if not any(key.endswith("_ms") for key in result):
        return
    logger.info("foodease_stage_metrics %s", json.dumps(result, separators=(",", ":")))
