"""VA-17 recovery — honest user-facing behavior for every recoverable situation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from foodease_agent.contract.enums import ProductState
from foodease_agent.product_state import ProductStateMachine


class Va17Situation(StrEnum):
    MIC_DENIED = "mic_denied"
    NO_SPEECH = "no_speech"
    LOW_CONFIDENCE = "low_confidence"
    TWO_MATCHING = "two_matching"
    FALSE_INTERRUPTION = "false_interruption"
    STT_DOWN = "stt_down"
    TTS_DOWN = "tts_down"
    LLM_DOWN = "llm_down"
    ACTION_REJECTED = "action_rejected"
    ACTION_TIMEOUT = "action_timeout"
    CONNECTION_LOSS = "connection_loss"
    GUI_SWITCH_MID_TURN = "gui_switch_mid_turn"
    STOP_DURING_CHECKOUT = "stop_during_checkout"


@dataclass(frozen=True)
class RecoveryResult:
    situation: Va17Situation
    assistant_text: str
    state: ProductState
    offer_typed: bool = False
    preserve_app_state: bool = True
    may_retry_mutation: bool = False  # always False for mutations (R4)


# One plain line + next step (Phase 8.5)
_MESSAGES: dict[Va17Situation, RecoveryResult] = {
    Va17Situation.MIC_DENIED: RecoveryResult(
        Va17Situation.MIC_DENIED,
        "Microphone access is off. You can type your request or browse the menu yourself.",
        ProductState.MUTED_PAUSED,
        offer_typed=True,
    ),
    Va17Situation.NO_SPEECH: RecoveryResult(
        Va17Situation.NO_SPEECH,
        "",  # idle tips handle limited prompts; then quiet
        ProductState.READY_LISTENING,
    ),
    Va17Situation.LOW_CONFIDENCE: RecoveryResult(
        Va17Situation.LOW_CONFIDENCE,
        "I didn’t catch that clearly. Please say it again, or pick one option.",
        ProductState.READY_LISTENING,
        offer_typed=True,
    ),
    Va17Situation.TWO_MATCHING: RecoveryResult(
        Va17Situation.TWO_MATCHING,
        "Which one did you mean? Say the name or the first or second.",
        ProductState.READY_LISTENING,
    ),
    Va17Situation.FALSE_INTERRUPTION: RecoveryResult(
        Va17Situation.FALSE_INTERRUPTION,
        "",  # resume — no new request; context kept
        ProductState.ASSISTANT_SPEAKING,
    ),
    Va17Situation.STT_DOWN: RecoveryResult(
        Va17Situation.STT_DOWN,
        "Speech recognition is unavailable. Please type instead — I won’t invent what you said.",
        ProductState.ERROR,
        offer_typed=True,
    ),
    Va17Situation.TTS_DOWN: RecoveryResult(
        Va17Situation.TTS_DOWN,
        "I can’t speak right now, but the text reply is on screen. You can retry or browse manually.",
        ProductState.READY_LISTENING,
        offer_typed=True,
    ),
    Va17Situation.LLM_DOWN: RecoveryResult(
        Va17Situation.LLM_DOWN,
        "The language model is unavailable or out of quota. Your cart is unchanged.",
        ProductState.ERROR,
        offer_typed=True,
    ),
    Va17Situation.ACTION_REJECTED: RecoveryResult(
        Va17Situation.ACTION_REJECTED,
        "That request was rejected. You can try another item or check the cart.",
        ProductState.READY_LISTENING,
    ),
    Va17Situation.ACTION_TIMEOUT: RecoveryResult(
        Va17Situation.ACTION_TIMEOUT,
        "I’m not sure that finished. I’ll check the cart before trying anything again.",
        ProductState.READY_LISTENING,
        may_retry_mutation=False,
    ),
    Va17Situation.CONNECTION_LOSS: RecoveryResult(
        Va17Situation.CONNECTION_LOSS,
        "Connection lost. Reconnecting from the latest menu and cart — I won’t replay uncertain actions.",
        ProductState.RECONNECTING,
    ),
    Va17Situation.GUI_SWITCH_MID_TURN: RecoveryResult(
        Va17Situation.GUI_SWITCH_MID_TURN,
        "Okay — I’ll follow the new screen and drop the old guidance.",
        ProductState.READY_LISTENING,
    ),
    Va17Situation.STOP_DURING_CHECKOUT: RecoveryResult(
        Va17Situation.STOP_DURING_CHECKOUT,
        "Stopped. I won’t place the order unless you confirm again.",
        ProductState.READY_LISTENING,
    ),
}


def recover(situation: Va17Situation, *, app_reason: str | None = None) -> RecoveryResult:
    base = _MESSAGES[situation]
    if situation == Va17Situation.ACTION_REJECTED and app_reason:
        return RecoveryResult(
            situation,
            f"{app_reason} You can try another item or check the cart.",
            base.state,
            offer_typed=base.offer_typed,
            preserve_app_state=True,
            may_retry_mutation=False,
        )
    return base


def apply_recovery(
    sm: ProductStateMachine,
    situation: Va17Situation,
    *,
    app_reason: str | None = None,
) -> RecoveryResult:
    result = recover(situation, app_reason=app_reason)
    if result.state != sm.state and result.assistant_text is not None:
        # STT down must never leave UI as listening
        if situation == Va17Situation.STT_DOWN:
            sm.transition(ProductState.ERROR, reason="stt_down")
        else:
            sm.transition(result.state, reason=situation.value)
    return result


ALL_VA17: tuple[Va17Situation, ...] = tuple(Va17Situation)
