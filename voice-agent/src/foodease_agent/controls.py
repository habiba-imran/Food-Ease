"""Control fast-path — deterministic, before the LLM. 'stop' never reaches the LLM."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class ControlIntent(StrEnum):
    STOP = "stop"
    PAUSE = "pause"
    RESUME = "resume"
    REPEAT = "repeat"
    SLOWER = "slower"
    FASTER = "faster"
    QUIETER = "quieter"
    LOUDER = "louder"
    MORE_DETAIL = "more_detail"
    LESS_DETAIL = "less_detail"
    HELP = "help"
    GO_BACK = "go_back"
    UNDO = "undo"
    BROWSE_SELF = "browse_self"
    SWITCH_TYPING = "switch_typing"
    GOODBYE = "goodbye"


@dataclass(frozen=True)
class ControlMatch:
    intent: ControlIntent
    raw: str


# High-precision patterns only (whole utterance / clear command).
_PATTERNS: list[tuple[ControlIntent, re.Pattern[str]]] = [
    (ControlIntent.STOP, re.compile(r"^\s*(stop|shut up|be quiet)\s*[.!?]?\s*$", re.I)),
    (ControlIntent.PAUSE, re.compile(r"^\s*(pause|hold on)\s*[.!?]?\s*$", re.I)),
    (ControlIntent.RESUME, re.compile(r"^\s*(resume|continue|go on)\s*[.!?]?\s*$", re.I)),
    (ControlIntent.REPEAT, re.compile(r"^\s*(repeat|say that again|what did you say)\s*[.!?]?\s*$", re.I)),
    (ControlIntent.SLOWER, re.compile(r"^\s*(slower|speak slower|slow down)\s*[.!?]?\s*$", re.I)),
    (ControlIntent.FASTER, re.compile(r"^\s*(faster|speak faster|speed up)\s*[.!?]?\s*$", re.I)),
    (ControlIntent.QUIETER, re.compile(r"^\s*(quieter|softer|volume down)\s*[.!?]?\s*$", re.I)),
    (ControlIntent.LOUDER, re.compile(r"^\s*(louder|volume up)\s*[.!?]?\s*$", re.I)),
    (ControlIntent.MORE_DETAIL, re.compile(r"^\s*(more detail|tell me more)\s*[.!?]?\s*$", re.I)),
    (ControlIntent.LESS_DETAIL, re.compile(r"^\s*(less detail|keep it short|briefly)\s*[.!?]?\s*$", re.I)),
    (ControlIntent.HELP, re.compile(r"^\s*(help|what can you do)\s*[.!?]?\s*$", re.I)),
    (ControlIntent.GO_BACK, re.compile(r"^\s*(go back|back)\s*[.!?]?\s*$", re.I)),
    (ControlIntent.UNDO, re.compile(r"^\s*(undo|undo that)\s*[.!?]?\s*$", re.I)),
    (
        ControlIntent.BROWSE_SELF,
        re.compile(r"^\s*(i'?ll browse myself|i will browse myself|let me browse)\s*[.!?]?\s*$", re.I),
    ),
    (
        ControlIntent.SWITCH_TYPING,
        re.compile(r"^\s*(switch to typing|i'?ll type|let me type)\s*[.!?]?\s*$", re.I),
    ),
    (
        ControlIntent.GOODBYE,
        re.compile(r"^\s*(that'?s all|goodbye|good bye|bye|i'?m done)\s*[.!?]?\s*$", re.I),
    ),
]


def match_control(utterance: str) -> ControlMatch | None:
    text = utterance.strip()
    if not text:
        return None
    for intent, pattern in _PATTERNS:
        if pattern.match(text):
            return ControlMatch(intent=intent, raw=text)
    return None
