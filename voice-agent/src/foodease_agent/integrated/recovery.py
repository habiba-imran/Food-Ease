"""Dependency degradation and fresh-state recovery; no business-write retries."""

from __future__ import annotations

import asyncio
import time
from collections import deque
from typing import Any


class RuntimeRecovery:
    def __init__(self, runtime: Any):
        self.runtime = runtime
        self.speech_failed = False
        self.room_lost = False
        self.was_paused = False
        # Event observations only. These are NOT audible-stop latency measurements.
        self.observations: deque[dict] = deque(maxlen=128)

    def observe(self, kind: str, **fields) -> None:
        self.observations.append({"kind": kind, "monotonic": time.monotonic(), **fields})

    def revoke(self) -> None:
        runtime = self.runtime
        runtime.epoch += 1
        if runtime.active_turn:
            runtime.active_turn.discarded = True
        runtime._invalidate_confirmation()
        runtime.references.clear()
        runtime.references_stale = True
        runtime.browse.reset([], runtime.snapshot.revision)
        runtime.details.clear()
        runtime.last_cart_item = runtime._last_completed = None
        runtime._interrupt()

    def provider_error(self, event: Any) -> None:
        runtime, error = self.runtime, event.error
        if runtime.closed or getattr(error, "recoverable", True):
            return
        kind = getattr(error, "type", "unknown")
        self.observe("provider_error", component=kind)
        self.revoke()
        speech = kind in {"stt_error", "tts_error"}
        if speech:
            # The SDK emits before deciding to close. Retain a silent text lane;
            # never restart a failed STT stream or invoke failed TTS for a warning.
            error.recoverable = True
            self.speech_failed = True
            runtime.mode = runtime._announced_mode = "typed"
            runtime.paused = runtime.muted = runtime.typed_audio = False
            runtime._set_audio()
            message = "Voice is unavailable. You can type your request or browse yourself."
        else:
            runtime.mode = "manual"
            runtime.end_local()
            message = "Assistance is unavailable. Please continue using the page controls."
        runtime._publish(
            "agent.error", {"code": "not_available", "message": message, "fatal": not speech}
        )

        async def notify():
            try:
                await runtime.adapter.publish_control(
                    "switch_mode", "typed" if speech else "manual"
                )
            except Exception:
                # If notification fails, fail closed locally; no hidden working mic.
                runtime.end_local()

        task = asyncio.create_task(notify())
        runtime._output_tasks.add(task)
        task.add_done_callback(runtime._output_tasks.discard)

    def room_reconnecting(self, *args) -> None:
        runtime = self.runtime
        if runtime.closed or self.room_lost:
            return
        self.was_paused = runtime.paused
        self.room_lost = True
        self.revoke()
        runtime.paused = True
        runtime._set_audio()

    def room_reconnected(self, *args) -> None:
        runtime = self.runtime
        if runtime.closed or not self.room_lost:
            return
        self.room_lost = False
        if self.was_paused or runtime.mode not in {"voice", "typed"}:
            return
        task = asyncio.create_task(self.resume())
        runtime._background.add(task)
        task.add_done_callback(runtime._background.discard)

    async def resume(self) -> bool:
        runtime = self.runtime
        if runtime.closed or self.room_lost:
            return False
        self.revoke()
        runtime.paused = True
        runtime._set_audio()
        epoch = runtime.epoch
        try:
            # Finish lookups before fetching the snapshot: a pending operation may
            # commit while its receipt is being recovered.
            for owned in tuple(runtime.pending.values()):
                await runtime.broker.reconcile(owned)
            fresh = await runtime.adapter.get_snapshot()
            if (
                fresh.session_id != runtime.snapshot.session_id
                or fresh.revision < runtime.snapshot.revision
            ):
                raise ValueError("stale recovery context")
            if runtime.closed or runtime.epoch != epoch:
                return False
            runtime.on_context(fresh)
            runtime.paused = runtime.muted = runtime.tips_paused = False
            runtime._set_audio()
            return True
        except Exception:
            runtime._publish(
                "agent.error",
                {
                    "code": "not_available",
                    "message": (
                        "The current page could not be checked. Assistance stays paused; "
                        "manual controls remain available."
                    ),
                    "fatal": False,
                },
            )
            return False
