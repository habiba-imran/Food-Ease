"""Interruption reconciliation (VA-03 / R5) — speech cancel ≠ action cancel."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class AssistantUtteranceStatus(StrEnum):
    COMPLETE = "complete"
    INTERRUPTED = "interrupted"


@dataclass
class PendingAction:
    action_id: str
    operation: str


@dataclass
class AssistantUtterance:
    text_spoken: str
    status: AssistantUtteranceStatus
    full_intended: str = ""


@dataclass
class InterruptionReconciler:
    """Tracks in-flight mutations and truncates assistant transcript on barge-in."""

    pending: dict[str, PendingAction] = field(default_factory=dict)
    chat_heard: list[str] = field(default_factory=list)
    last_utterance: AssistantUtterance | None = None
    speaking_intervals: list[tuple[float, float]] = field(default_factory=list)
    _speak_start: float | None = None

    def register_pending(self, action_id: str, operation: str) -> None:
        self.pending[action_id] = PendingAction(action_id=action_id, operation=operation)

    def resolve_pending(self, action_id: str) -> PendingAction | None:
        return self.pending.pop(action_id, None)

    def on_assistant_start(self, now: float) -> None:
        if self._speak_start is not None:
            # Overlap — close previous without end (should not happen if gated)
            self.speaking_intervals.append((self._speak_start, now))
        self._speak_start = now

    def on_assistant_stop(self, now: float) -> None:
        if self._speak_start is not None:
            self.speaking_intervals.append((self._speak_start, now))
            self._speak_start = None

    def on_barge_in(self, *, spoken_so_far: str, full_intended: str) -> AssistantUtterance:
        """Audio stops; transcript marked interrupted; pending actions stay."""
        utt = AssistantUtterance(
            text_spoken=spoken_so_far,
            status=AssistantUtteranceStatus.INTERRUPTED,
            full_intended=full_intended,
        )
        self.last_utterance = utt
        if spoken_so_far.strip():
            self.chat_heard.append(spoken_so_far.strip())
        return utt

    def on_complete(self, text: str) -> AssistantUtterance:
        utt = AssistantUtterance(
            text_spoken=text,
            status=AssistantUtteranceStatus.COMPLETE,
            full_intended=text,
        )
        self.last_utterance = utt
        if text.strip():
            self.chat_heard.append(text.strip())
        return utt

    def late_result_reply(self, action_id: str, *, success: bool) -> str | None:
        """Short status or silence for a result arriving after barge-in."""
        pending = self.resolve_pending(action_id)
        if pending is None:
            return None  # silence — already announced or unknown
        if success:
            return "Done."
        return "That last request did not go through."

    @staticmethod
    def intervals_overlap(intervals: list[tuple[float, float]]) -> bool:
        ordered = sorted(intervals, key=lambda x: x[0])
        for i in range(1, len(ordered)):
            prev_end = ordered[i - 1][1]
            cur_start = ordered[i][0]
            if cur_start < prev_end:
                return True
        return False
