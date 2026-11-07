"""Supported local effects, with no user-language phrase matching."""

from typing import Literal, get_args

ConversationIntent = Literal[
    "end",
    "stop",
    "pause",
    "resume",
    "mute",
    "unmute",
    "repeat",
    "voice",
    "typed",
    "manual",
    "slower",
    "faster",
    "quieter",
    "louder",
    "more_detail",
    "less_detail",
    "help",
    "go_back",
    "undo",
    "pause_tips",
    "resume_tips",
    "next",
    "previous",
    "read_page",
    "read_categories",
    "read_cart",
    "open_reference",
    "add_button",
    "unsupported_button",
]

CONVERSATION_INTENTS = frozenset(get_args(ConversationIntent))
PAGE_INTENTS = frozenset(
    {
        "next",
        "previous",
        "read_page",
        "read_categories",
        "read_cart",
        "open_reference",
        "add_button",
        "unsupported_button",
    }
)
