"""Real SDK segmented playout; synthetic PCM and an explicitly driven sink."""

import asyncio
import struct
import time

from livekit import rtc
from livekit.agents import AgentSession, llm
from livekit.agents.voice.io import AudioOutput, AudioOutputCapabilities

from foodease_agent.integrated.agent import IntegratedFoodEaseAgent
from foodease_agent.integrated.runtime import LiveConversationRuntime
from test_integrated_runtime import WebsiteAdapter


class NoProvider(llm.LLM):
    def chat(self, **kwargs):
        raise AssertionError("Authored speech must not make another model request")


class SegmentedAgent(IntegratedFoodEaseAgent):
    async def tts_node(self, text, model_settings):
        spoken = "".join([chunk async for chunk in text])
        marker = 1 if "First sentence" in spoken else 2 if "Old second" in spoken else 3
        yield rtc.AudioFrame(struct.pack("<h", marker) * 2400, 24000, 1, 2400)


class DrivenSink(AudioOutput):
    def __init__(self):
        super().__init__(label="manual-test", capabilities=AudioOutputCapabilities(pause=False))
        self.frames = []
        self.flushed = asyncio.Event()
        self.finished = 0
        self.autoplay = False

    async def capture_frame(self, frame):
        await super().capture_frame(frame)
        self.frames.append(struct.unpack_from("<h", frame.data)[0])
        self.on_playback_started(created_at=time.time())

    def flush(self):
        super().flush()
        self.flushed.set()
        if self.autoplay and self.captured_playout_segments > self.finished:
            self.finish()

    def finish(self, *, interrupted=False):
        if self.captured_playout_segments > self.finished:
            self.finished += 1
            self.on_playback_finished(playback_position=0.1, interrupted=interrupted)

    def clear_buffer(self):
        self.finish(interrupted=True)


async def test_native_navigation_finishes_one_sentence_not_the_whole_old_reply():
    sink = DrivenSink()
    session = AgentSession(llm=NoProvider(), use_tts_aligned_transcript=False)
    session.output.audio = sink
    runtime = LiveConversationRuntime(SegmentedAgent(language="en"), session, WebsiteAdapter())
    await runtime.prepare()
    await runtime.select_mode("voice")
    await session.start(agent=runtime.agent)
    try:
        handle = runtime.say("First sentence. Old second sentence.", scope="menu")
        await asyncio.wait_for(sink.flushed.wait(), 5)
        await runtime.adapter.manual("navigate", {"target": "karahi"})
        runtime.on_context(await runtime.adapter.get_snapshot(), source_turn="manual-category")
        assert not handle.interrupted
        assert sink.frames == [1]
        sink.autoplay = True
        sink.finish()
        await asyncio.wait_for(handle.wait_for_playout(), 5)
        for _ in range(200):
            if 3 in sink.frames and not runtime._background:
                break
            await asyncio.sleep(0.01)
        assert handle.interrupted
        assert 2 not in sink.frames, "The old second sentence must never reach the audio sink"
        assert 3 in sink.frames, "A fresh acknowledgment must reach the SDK audio sink"
    finally:
        sink.autoplay = True
        sink.finish()
        await runtime.close()
        await session.aclose()
