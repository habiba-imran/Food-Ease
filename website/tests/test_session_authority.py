"""Phase 2: actual HTTP authority, isolation, confirmation and concurrency."""

from __future__ import annotations

import copy
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from fastapi.testclient import TestClient

from foodease_website.app import create_app
from foodease_website.domain import FoodEaseDomain
from foodease_website.sessions import SessionError, SessionStore


def session(client: TestClient) -> str:
    response = client.post("/api/v2/app/sessions", json={})
    assert response.status_code == 201
    sid = response.json()["session_id"]
    client.headers["X-FoodEase-Session"] = sid
    return sid


def context(client: TestClient) -> dict:
    response = client.get("/api/v2/app/context")
    assert response.status_code == 200
    return response.json()


def message(
    sid: str, revision: int, operation: str, arguments: dict | None = None, action_id: str = "a"
) -> dict:
    return {
        "schema_version": "2.0",
        "session_id": sid,
        "event_id": f"request-{action_id}",
        "turn_id": "turn-1",
        "timestamp": "2026-10-17T12:00:00Z",
        "context_revision": revision,
        "type": "agent.action_request",
        "payload": {"action_id": action_id, "operation": operation, "arguments": arguments or {}},
    }


def action(
    client: TestClient,
    operation: str,
    arguments: dict | None = None,
    action_id: str = "a",
    revision: int | None = None,
) -> dict:
    state = context(client)
    response = client.post(
        "/api/v2/app/action",
        json=message(
            state["session_id"],
            state["revision"] if revision is None else revision,
            operation,
            arguments,
            action_id,
        ),
    )
    assert response.status_code == 200, response.text
    return response.json()


def add(client: TestClient, action_id: str = "add") -> dict:
    return action(
        client, "cart.add_item", {"item_id": "wrap-hot-chicken", "quantity": 1}, action_id
    )


def test_two_owners_and_two_tabs_are_isolated_and_reload_attaches() -> None:
    app = create_app()
    first, second = TestClient(app), TestClient(app)
    sid = session(first)
    other = session(second)
    assert sid != other
    assert add(first)["payload"]["status"] == "success"
    assert not context(second)["cart"]["lines"]
    assert second.post("/api/v2/app/sessions/attach", json={"session_id": sid}).status_code == 403
    assert first.post("/api/v2/app/sessions/attach", json={"session_id": sid}).status_code == 200
    assert context(first)["cart"]["total"] == 900
    tab_two = session(first)
    assert tab_two != sid and not context(first)["cart"]["lines"]
    first.headers["X-FoodEase-Session"] = sid
    assert context(first)["cart"]["total"] == 900
    assert first.cookies.get("foodease_owner")


def test_all_thirteen_operations_share_manual_and_v2_authority() -> None:
    from foodease_contract.models import ActionResultEvent, ContextSnapshot

    client = TestClient(create_app())
    sid = session(client)
    operations = [
        ("navigate", {"target": "menu"}),
        ("filter_menu", {"tags": ["vegetarian"], "max_price_pkr": 800}),
        ("search_menu", {"query": "wrap"}),
        ("select_item", {"item_id": "wrap-veg"}),
        ("get_item_details", {"item_id": "wrap-veg"}),
        ("cart.add_item", {"item_id": "wrap-hot-chicken", "quantity": 2}),
        ("cart.set_quantity", {"item_id": "wrap-hot-chicken", "quantity": 1}),
        ("cart.remove_item", {"item_id": "wrap-hot-chicken"}),
        ("undo_last_reversible_action", {}),
        ("get_cart", {}),
        ("get_current_context", {}),
        ("checkout.get_summary", {}),
    ]
    summary = None
    for index, (operation, arguments) in enumerate(operations):
        result = action(client, operation, arguments, str(index))
        parsed = ActionResultEvent.model_validate(result)
        assert parsed.session_id == sid and parsed.payload.status == "success"
        summary = result["payload"]
    assert summary is not None
    # Manual and agent-facing endpoints hit the same state and confirmation gate.
    manual = client.get("/api/app/context").json()
    assert manual["cart"]["total"] == 900
    result = action(
        client,
        "checkout.submit_demo_order",
        {
            "confirmed": True,
            "confirmation_token": summary["confirmation_token"],
            "summary_revision": summary["verified_state"]["summary_revision"],
        },
        "submit",
    )
    assert result["payload"]["verified_state"]["order"]["total"] == 900
    assert ContextSnapshot.model_validate(context(client)).route == "confirmation"
    assert not context(client)["cart"]["lines"]
    lookup = client.get("/api/v2/app/actions/submit", headers={"X-FoodEase-Event-Id": "lookup-1"})
    assert lookup.json()["state"] == "found" and lookup.json()["result"] == result


@pytest.mark.parametrize(
    "arguments",
    [
        {"item_id": "drink-cola", "quantity": True},
        {"item_id": "drink-cola", "quantity": "2"},
        {"item_id": "drink-cola", "quantity": 1.5},
        {"item_id": "drink-cola", "quantity": 0},
        {"item_id": "drink-cola", "quantity": 100},
        {"item_id": "drink-cola", "price": 1},
    ],
)
def test_manual_argument_validation_precedes_domain(arguments: dict) -> None:
    client = TestClient(create_app())
    session(client)
    before = context(client)
    response = client.post(
        "/api/app/action",
        json={
            "action_id": "bad",
            "operation": "cart.add_item",
            "arguments": arguments,
            "context_revision": before["revision"],
        },
    )
    assert response.status_code == 422
    assert context(client) == before


def test_malformed_missing_revision_unknown_fields_and_cross_session_fail_safely() -> None:
    client = TestClient(create_app())
    sid = session(client)
    for raw in (b"{", b"[]", b'"text"', b'{"action_id":"a"}'):
        assert client.post("/api/app/action", content=raw).status_code in {400, 422}
    request = message(sid, 1, "get_cart")
    for field, value in (
        ("session_id", "foreign"),
        ("schema_version", "1.0"),
        ("context_revision", None),
        ("unknown", True),
    ):
        bad = copy.deepcopy(request)
        bad[field] = value
        assert client.post("/api/v2/app/action", json=bad).status_code in {403, 422}
    assert client.post("/api/v2/app/action", content=b"x" * 15000).status_code == 413
    assert not context(client)["cart"]["lines"]


def test_duplicate_conflict_stale_and_future_requests() -> None:
    client = TestClient(create_app())
    sid = session(client)
    request = message(sid, 1, "cart.add_item", {"item_id": "drink-cola"})
    first = client.post("/api/v2/app/action", json=request).json()
    assert client.post("/api/v2/app/action", json=request).json() == first
    changed = copy.deepcopy(request)
    changed["payload"]["arguments"]["quantity"] = 2
    conflict = client.post("/api/v2/app/action", json=changed).json()
    assert conflict["payload"]["error_code"] == "idempotency_conflict"
    for revision in (0, context(client)["revision"] + 1):
        result = action(
            client, "cart.add_item", {"item_id": "drink-cola"}, f"bad-{revision}", revision
        )
        assert result["payload"]["status"] == "stale_context"
    assert context(client)["cart"]["lines"][0]["quantity"] == 1
    assert (
        action(client, "get_cart", action_id="old-read", revision=0)["payload"]["status"]
        == "success"
    )
    assert (
        action(
            client, "get_cart", action_id="future-read", revision=context(client)["revision"] + 1
        )["payload"]["status"]
        == "stale_context"
    )
    # Exercise the safety rule with simulated stock loss; the shipped menu is fully available.
    shopping = client.app.state.sessions._sessions[sid]
    shopping.domain.menu_by_id["burger-soldout"].available = False
    assert (
        action(client, "cart.add_item", {"item_id": "burger-soldout"}, "soldout")["payload"][
            "error_code"
        ]
        == "out_of_stock"
    )


def test_checkout_binding_survives_navigation_but_not_cart_change_or_cross_session() -> None:
    client = TestClient(create_app())
    session(client)
    add(client)
    summary = action(client, "checkout.get_summary", action_id="summary")["payload"]
    args = {
        "confirmed": True,
        "confirmation_token": summary["confirmation_token"],
        "summary_revision": summary["verified_state"]["summary_revision"],
    }
    assert not args["confirmation_token"].startswith("confirm_")
    action(client, "navigate", {"target": "menu"}, "navigate")
    receipt = action(client, "checkout.submit_demo_order", args, "submit")
    assert receipt["payload"]["status"] == "success"
    assert (
        action(client, "undo_last_reversible_action", action_id="undo")["payload"]["status"]
        == "rejected"
    )
    add(client, "add-again")
    assert (
        action(client, "checkout.submit_demo_order", args, "reuse")["payload"]["status"]
        == "rejected"
    )
    fresh = action(client, "checkout.get_summary", action_id="summary-new")["payload"]
    new_args = {
        "confirmed": True,
        "confirmation_token": fresh["confirmation_token"],
        "summary_revision": fresh["verified_state"]["summary_revision"],
    }
    other_sid = session(client)
    add(client, "other-add")
    assert (
        action(client, "checkout.submit_demo_order", new_args, "cross")["payload"]["status"]
        == "rejected"
    )
    assert context(client)["session_id"] == other_sid


def test_cart_edit_and_missing_or_wrong_binding_cannot_submit() -> None:
    client = TestClient(create_app())
    session(client)
    add(client)
    summary = action(client, "checkout.get_summary", action_id="summary")["payload"]
    args = {
        "confirmed": True,
        "confirmation_token": summary["confirmation_token"],
        "summary_revision": summary["verified_state"]["summary_revision"],
    }
    for missing in ("confirmation_token", "summary_revision"):
        bad = dict(args)
        bad.pop(missing)
        request = message(
            context(client)["session_id"],
            context(client)["revision"],
            "checkout.submit_demo_order",
            bad,
        )
        assert client.post("/api/v2/app/action", json=request).status_code == 422
    action(client, "cart.set_quantity", {"item_id": "wrap-hot-chicken", "quantity": 2}, "edit")
    assert (
        action(client, "checkout.submit_demo_order", args, "submit")["payload"]["status"]
        == "rejected"
    )
    assert context(client)["cart"]["total"] == 1750


def test_search_filter_back_and_context_are_truthful() -> None:
    client = TestClient(create_app())
    session(client)
    action(client, "navigate", {"target": "burgers"}, "burgers")
    action(client, "select_item", {"item_id": "burger-veg"}, "select")
    action(client, "navigate", {"target": "back"}, "back")
    assert context(client)["route"] == "menu" and context(client)["category"] == "burgers"
    action(client, "select_item", {"item_id": "burger-veg"}, "select-again")
    action(client, "search_menu", {"query": "not-in-menu"}, "search")
    assert context(client)["focus_item_id"] is None
    action(
        client,
        "filter_menu",
        {"tags": ["spicy"], "category": "wraps", "max_price_pkr": 1000},
        "filter",
    )
    state = context(client)
    assert state["category"] == "wraps" and state["max_price_pkr"] == 1000
    assert (
        action(client, "filter_menu", {"tags": ["invented"]}, "invalid-tag")["payload"]["status"]
        == "rejected"
    )


def test_lookup_pending_found_and_rollback_without_reexecution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    store = app.state.sessions
    owner = store.new_owner()
    sid = store.create(owner).session_id
    request = message(sid, 1, "cart.add_item", {"item_id": "drink-cola"})
    entered, release = Event(), Event()
    original = FoodEaseDomain.execute_action

    def slow(self, *args, **kwargs):
        entered.set()
        assert release.wait(5)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(FoodEaseDomain, "execute_action", slow)
    with ThreadPoolExecutor() as pool:
        first = pool.submit(store.submit, owner, sid, request)
        assert entered.wait(5)
        assert store.lookup(owner, sid, "a", "lookup").state == "pending"
        second = pool.submit(store.submit, owner, sid, request)
        release.set()
        assert first.result() == second.result()
    assert store.context(owner, sid)["cart"]["lines"][0]["quantity"] == 1
    assert store.lookup(owner, sid, "a", "lookup").state == "found"
    before = store.context(owner, sid)
    assert store.lookup(owner, sid, "missing", "lookup").state == "not_seen"
    assert store.context(owner, sid) == before


def test_transaction_rolls_back_if_execution_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()
    store = app.state.sessions
    owner = store.new_owner()
    sid = store.create(owner).session_id
    before = store.context(owner, sid)
    original = FoodEaseDomain.execute_action

    def broken(self, *args, **kwargs):
        original(self, *args, **kwargs)
        raise RuntimeError("private provider detail must not escape")

    monkeypatch.setattr(FoodEaseDomain, "execute_action", broken)
    result = store.submit(owner, sid, message(sid, 1, "cart.add_item", {"item_id": "drink-cola"}))
    assert result.payload.status == "failed" and "private" not in result.model_dump_json()
    assert store.context(owner, sid) == before
    assert store.lookup(owner, sid, "a", "lookup").result == result


def test_expiry_restart_capacity_and_confirmation_timeout() -> None:
    app = create_app()
    now = [0.0]
    store = SessionStore(
        app.state.catalog,
        clock=lambda: now[0],
        idle_ttl=10,
        absolute_ttl=20,
        max_sessions=2,
        max_actions=2,
        confirmation_ttl=2,
    )
    owner = store.new_owner()
    sid = store.create(owner).session_id
    store.submit(owner, sid, message(sid, 1, "cart.add_item", {"item_id": "drink-cola"}))
    summary = store.submit(owner, sid, message(sid, 2, "checkout.get_summary", action_id="summary"))
    with pytest.raises(SessionError):
        store.submit(owner, sid, message(sid, 3, "get_cart", action_id="over-capacity"))
    assert store.lookup(owner, sid, "a", "lookup").state == "found"
    now[0] = 11
    assert store.lookup(owner, sid, "a", "lookup").state == "expired"
    restarted = SessionStore(app.state.catalog)
    with pytest.raises(SessionError):
        restarted.context(owner, sid)
    assert summary.payload.status == "success"


def test_foreign_origin_and_missing_owner_cannot_mutate_or_lookup() -> None:
    app = create_app()
    owner = TestClient(app)
    sid = session(owner)
    add(owner)
    stranger = TestClient(app)
    stranger.headers["X-FoodEase-Session"] = sid
    assert stranger.get("/api/v2/app/context").status_code in {401, 410}
    assert stranger.get("/api/v2/app/actions/add").status_code in {401, 410}
    assert (
        owner.post(
            "/api/app/action",
            headers={"Origin": "https://foreign.example"},
            json={
                "action_id": "csrf",
                "operation": "cart.remove_item",
                "arguments": {"item_id": "wrap-hot-chicken"},
                "context_revision": context(owner)["revision"],
            },
        ).status_code
        == 403
    )


def test_competing_actions_at_one_revision_commit_only_one() -> None:
    app = create_app()
    store = app.state.sessions
    owner = store.new_owner()
    sid = store.create(owner).session_id
    requests = [
        message(sid, 1, "cart.add_item", {"item_id": "drink-cola"}, f"race-{i}") for i in range(12)
    ]
    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(lambda raw: store.submit(owner, sid, raw), requests))
    assert sum(result.payload.status == "success" for result in results) == 1
    assert sum(result.payload.status == "stale_context" for result in results) == 11
    state = store.context(owner, sid)
    assert state["revision"] == 2 and state["cart"]["lines"][0]["quantity"] == 1


@pytest.mark.parametrize("defect", ["wrong_action", "wrong_total", "wrong_context"])
def test_invalid_output_is_not_committed(monkeypatch: pytest.MonkeyPatch, defect: str) -> None:
    store = create_app().state.sessions
    owner = store.new_owner()
    sid = store.create(owner).session_id
    before = store.context(owner, sid)
    original = FoodEaseDomain.execute_action

    def corrupt(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        if defect == "wrong_action":
            result["action_id"] = "someone-else"
        elif defect == "wrong_total":
            result["verified_state"]["total"] = 0
        else:
            self.category = "x" * 100
        return result

    monkeypatch.setattr(FoodEaseDomain, "execute_action", corrupt)
    result = store.submit(owner, sid, message(sid, 1, "cart.add_item", {"item_id": "drink-cola"}))
    assert result.payload.status == "failed"
    assert store.context(owner, sid) == before
    assert store.lookup(owner, sid, "a", "lookup").result == result


def test_expired_and_incorrect_tokens_and_summary_revisions_preserve_cart() -> None:
    app = create_app()
    now = [0.0]
    store = SessionStore(app.state.catalog, clock=lambda: now[0], confirmation_ttl=2)
    client = TestClient(create_app(sessions=store))
    session(client)
    add(client)
    summary = action(client, "checkout.get_summary", action_id="summary")["payload"]
    args = {
        "confirmed": True,
        "confirmation_token": summary["confirmation_token"],
        "summary_revision": summary["verified_state"]["summary_revision"],
    }
    for index, bad in enumerate(
        (
            dict(args, confirmation_token="wrong"),
            dict(args, confirmation_token="\u2603"),
            dict(args, summary_revision=args["summary_revision"] + 1),
        )
    ):
        assert (
            action(client, "checkout.submit_demo_order", bad, f"bad-{index}")["payload"][
                "error_code"
            ]
            == "confirmation_expired"
        )
    now[0] = 2
    assert (
        action(client, "checkout.submit_demo_order", args, "expired")["payload"]["error_code"]
        == "confirmation_expired"
    )
    assert context(client)["cart"]["total"] == 900


def test_replay_after_lost_receipt_keeps_original_receipt_and_cannot_create_second_order() -> None:
    client = TestClient(create_app())
    sid = session(client)
    add(client)
    summary = action(client, "checkout.get_summary", action_id="summary")["payload"]
    args = {
        "confirmed": True,
        "confirmation_token": summary["confirmation_token"],
        "summary_revision": summary["verified_state"]["summary_revision"],
    }
    request = message(
        sid, context(client)["revision"], "checkout.submit_demo_order", args, "submit"
    )
    receipt = client.post("/api/v2/app/action", json=request).json()
    add(client, "later-cart")
    before = context(client)
    assert client.post("/api/v2/app/action", json=request).json() == receipt
    assert client.get("/api/v2/app/actions/submit").json()["result"] == receipt
    assert context(client) == before


def test_capacity_and_idle_absolute_expiry_are_bounded_and_lookup_does_not_extend_lifetime() -> (
    None
):
    app = create_app()
    now = [0.0]
    store = SessionStore(
        app.state.catalog, clock=lambda: now[0], idle_ttl=10, absolute_ttl=20, max_sessions=1
    )
    owner = store.new_owner()
    sid = store.create(owner).session_id
    with pytest.raises(SessionError, match="capacity"):
        store.create(owner)
    second_owner = store.new_owner()
    with pytest.raises(SessionError, match="capacity"):
        store.new_owner()
    now[0] = 9
    assert store.lookup(owner, sid, "unknown", "lookup").state == "not_seen"
    now[0] = 10
    assert store.lookup(owner, sid, "unknown", "lookup").state == "expired"
    replacement = store.create(second_owner).session_id
    assert replacement != sid
    now[0] = 19
    store.context(second_owner, replacement)
    now[0] = 20
    with pytest.raises(SessionError, match="expired"):
        store.context(second_owner, replacement)


def test_manual_cannot_skip_revision_or_confirmation_and_cookie_is_http_only() -> None:
    client = TestClient(create_app())
    response = client.post("/api/v2/app/sessions", json={})
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=strict" in response.headers["set-cookie"]
    client.headers["X-FoodEase-Session"] = response.json()["session_id"]
    for payload in (
        {"action_id": "a", "operation": "cart.add_item", "arguments": {"item_id": "drink-cola"}},
        {
            "action_id": "b",
            "operation": "checkout.submit_demo_order",
            "arguments": {"confirmed": True},
            "context_revision": 1,
        },
    ):
        assert client.post("/api/app/action", json=payload).status_code == 422
    assert context(client)["revision"] == 1


def test_pending_timeout_is_uncertain_and_does_not_replace_eventual_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = create_app().state.sessions
    owner = store.new_owner()
    shopping = store.create(owner)
    sid = shopping.session_id
    raw = message(sid, 1, "cart.add_item", {"item_id": "drink-cola"})
    entered, release = Event(), Event()
    original = FoodEaseDomain.execute_action

    def slow(self, *args, **kwargs):
        entered.set()
        assert release.wait(5)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(FoodEaseDomain, "execute_action", slow)
    with ThreadPoolExecutor() as pool:
        pending = pool.submit(store.submit, owner, sid, raw)
        assert entered.wait(5)
        # Simulate the wait deadline without adding five seconds to every test run.
        monkeypatch.setattr(shopping.actions["a"].done, "wait", lambda timeout: False)
        uncertain = store.submit(owner, sid, raw)
        assert uncertain.payload.status == "timeout_unknown"
        assert store.lookup(owner, sid, "a", "lookup").state == "pending"
        release.set()
        committed = pending.result()
    assert store.lookup(owner, sid, "a", "lookup").result == committed
    assert committed.payload.status == "success"
    assert store.context(owner, sid)["cart"]["lines"][0]["quantity"] == 1


def test_same_action_id_and_receipt_are_private_to_session() -> None:
    app = create_app()
    first, second = TestClient(app), TestClient(app)
    session(first)
    session(second)
    receipts = []
    for client in (first, second):
        add(client)
        summary = action(client, "checkout.get_summary", action_id="summary")["payload"]
        args = {
            "confirmed": True,
            "confirmation_token": summary["confirmation_token"],
            "summary_revision": summary["verified_state"]["summary_revision"],
        }
        receipts.append(action(client, "checkout.submit_demo_order", args, "submit"))
    assert (
        receipts[0]["payload"]["verified_state"]["demo_order_id"]
        != receipts[1]["payload"]["verified_state"]["demo_order_id"]
    )
    for client, receipt in zip((first, second), receipts, strict=True):
        assert client.get("/api/v2/app/actions/submit").json()["result"] == receipt


def test_invalid_items_navigation_and_cart_overflow_never_partially_mutate() -> None:
    client = TestClient(create_app())
    session(client)
    before = context(client)
    for index, operation in enumerate(
        (
            "select_item",
            "get_item_details",
            "cart.add_item",
            "cart.set_quantity",
            "cart.remove_item",
        )
    ):
        args = {"item_id": "does-not-exist"}
        if operation == "cart.set_quantity":
            args["quantity"] = 1
        result = action(client, operation, args, f"invalid-{index}")
        assert result["payload"]["status"] == "rejected"
        assert client.get(f"/api/v2/app/actions/invalid-{index}").json()["result"] == result
        assert context(client) == before
    assert (
        action(client, "navigate", {"target": "unknown-page"}, "invalid-nav")["payload"]["status"]
        == "rejected"
    )
    action(client, "cart.add_item", {"item_id": "drink-cola", "quantity": 99}, "max")
    full = context(client)
    assert (
        action(client, "cart.add_item", {"item_id": "drink-cola"}, "overflow")["payload"]["status"]
        == "rejected"
    )
    assert context(client) == full
