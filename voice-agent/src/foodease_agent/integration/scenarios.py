"""IR-01…IR-05 — MockAdapter-backed integration scenarios."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass, field

from foodease_agent.adapters.mock import MockAdapter, ScenarioConfig, ScenarioMode
from foodease_agent.contract.enums import ActionResultStatus, Operation, ProductState
from foodease_agent.contract.models import ActionRequestPayload
from foodease_agent.dialogue_planner import DialogueSuitePlanner
from foodease_agent.engine import ConversationEngine
from foodease_agent.faults import FAULTS


@dataclass
class ScenarioResult:
    id: str
    title: str
    ok: bool
    detail: str = ""
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _req(action_id: str, operation: Operation, **arguments: object) -> ActionRequestPayload:
    return ActionRequestPayload(action_id=action_id, operation=operation, arguments=arguments)


async def ir01_stale_revision() -> ScenarioResult:
    app = MockAdapter(default_timeout_s=0.05)
    app.set_scenario(ScenarioConfig(mode=ScenarioMode.STALE_CONTEXT))
    result = await app.submit_action(
        _req("ir01", Operation.CART_ADD_ITEM, item_id="wrap-veg", quantity=1)
    )
    snap = await app.get_snapshot()
    ok = (
        result.status == ActionResultStatus.STALE_CONTEXT
        and result.action_id == "ir01"
        and snap.cart.lines == []
    )
    return ScenarioResult(
        id="IR-01",
        title="Stale context_revision rejects mutation",
        ok=ok,
        detail=f"status={result.status.value} lines={len(snap.cart.lines)}",
    )


async def ir02_duplicate_action_id() -> ScenarioResult:
    app = MockAdapter()
    first = await app.submit_action(
        _req("ir02-dup", Operation.CART_ADD_ITEM, item_id="drink-cola", quantity=1)
    )
    second = await app.submit_action(
        _req("ir02-dup", Operation.CART_ADD_ITEM, item_id="drink-cola", quantity=1)
    )
    snap = await app.get_snapshot()
    qty = sum(line.quantity for line in snap.cart.lines)
    ok = (
        first.status == ActionResultStatus.SUCCESS
        and first.model_dump(mode="json") == second.model_dump(mode="json")
        and qty == 1
    )
    return ScenarioResult(
        id="IR-02",
        title="Duplicate action_id is idempotent",
        ok=ok,
        detail=f"qty={qty} same_payload={first.model_dump() == second.model_dump()}",
    )


async def ir03_checkout_confirm() -> ScenarioResult:
    app = MockAdapter()
    await app.submit_action(
        _req("ir03-seed", Operation.CART_ADD_ITEM, item_id="drink-cola", quantity=1)
    )
    engine = ConversationEngine(adapter=app, planner=DialogueSuitePlanner())
    await engine.handle_text("checkout")
    mid = await app.get_snapshot()
    # Silence / non-yes must not submit
    await engine.handle_text("hmm")
    after_hmm = await app.get_snapshot()
    r = await engine.handle_text("yes")
    after_yes = await app.get_snapshot()
    demo_ok = "demo" in r.assistant_text.lower() and (
        after_yes.route == "order_confirmation"
        or "demo order" in r.assistant_text.lower()
        or any(t.status == ActionResultStatus.SUCCESS for t in r.tool_results)
    )
    # Cart still had items before yes
    ok = bool(mid.cart.lines) and after_hmm.route != "order_confirmation" and demo_ok
    return ScenarioResult(
        id="IR-03",
        title="Checkout requires explicit confirmation",
        ok=ok,
        detail=f"route_after_hmm={after_hmm.route} assistant={r.assistant_text[:80]!r}",
    )


async def ir04_mic_denied_manual() -> ScenarioResult:
    FAULTS.reset()
    FAULTS.mic_denied = True
    try:
        engine = ConversationEngine(adapter=MockAdapter(), planner=DialogueSuitePlanner())
        blocked = await engine.handle_text("show burgers")
        voice_blocked = blocked.state == ProductState.MUTED_PAUSED
        # Manual / typed continue after clearing mic fault
        FAULTS.mic_denied = False
        cont = await engine.handle_text("show burgers")
        manual_ok = bool(cont.assistant_text.strip()) and cont.state != ProductState.MUTED_PAUSED
        ok = voice_blocked and manual_ok
        return ScenarioResult(
            id="IR-04",
            title="Mic denied then manual/typed continue",
            ok=ok,
            detail=f"blocked_state={blocked.state.value} continue_ok={manual_ok}",
        )
    finally:
        FAULTS.reset()


async def ir05_cart_invalidates_confirm() -> ScenarioResult:
    app = MockAdapter()
    await app.submit_action(
        _req("ir05-seed", Operation.CART_ADD_ITEM, item_id="drink-cola", quantity=1)
    )
    engine = ConversationEngine(adapter=app, planner=DialogueSuitePlanner())
    await engine.handle_text("checkout")
    awaiting = engine.confirmation.state.value == "awaiting"
    await app.simulate_cart_change("drink-cola", quantity=2)
    engine.confirmation.on_cart_or_revision_change((await app.get_snapshot()).revision)
    invalidated = engine.confirmation.state.value == "none"
    # Old "yes" must not place order without fresh summary — force a yes after invalidate
    # without re-checkout: confirmation machine should refuse
    r = await engine.handle_text("yes")
    snap = await app.get_snapshot()
    not_submitted = snap.route != "order_confirmation" or "demo" not in r.assistant_text.lower()
    # After invalidate, yes alone should not succeed as demo order
    ok = awaiting and invalidated and (
        engine.confirmation.state.value != "submitted"
    )
    return ScenarioResult(
        id="IR-05",
        title="Cart change invalidates checkout confirmation",
        ok=ok,
        detail=(
            f"awaiting={awaiting} invalidated={invalidated} "
            f"state={engine.confirmation.state.value} route={snap.route} "
            f"not_auto_submit={not_submitted}"
        ),
    )


SCENARIOS: list[tuple[str, Callable[[], Awaitable[ScenarioResult]]]] = [
    ("IR-01", ir01_stale_revision),
    ("IR-02", ir02_duplicate_action_id),
    ("IR-03", ir03_checkout_confirm),
    ("IR-04", ir04_mic_denied_manual),
    ("IR-05", ir05_cart_invalidates_confirm),
]


async def run_all() -> list[ScenarioResult]:
    FAULTS.reset()
    results: list[ScenarioResult] = []
    for _sid, fn in SCENARIOS:
        FAULTS.reset()
        results.append(await fn())
    FAULTS.reset()
    return results
