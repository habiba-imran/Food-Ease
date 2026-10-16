"""Real localhost HTTP conformance; no browser, worker or paid providers.

Run with the website Python environment and a disposable standalone server.
"""

from __future__ import annotations

import argparse
import copy
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx
from foodease_contract.models import ActionResultEvent, ContextSnapshot, LookupResponse


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:18080")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    url = urlparse(args.base_url)
    if url.scheme != "http" or url.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Disposable localhost only")
    trace = []
    with (
        httpx.Client(base_url=args.base_url, trust_env=False) as client,
        httpx.Client(base_url=args.base_url, trust_env=False) as stranger,
    ):

        def create(shopper: httpx.Client) -> str:
            response = shopper.post("/api/v2/app/sessions", json={})
            assert response.status_code == 201
            sid = response.json()["session_id"]
            shopper.headers["X-FoodEase-Session"] = sid
            return sid

        sid, other_sid = create(client), create(stranger)
        assert sid != other_sid

        def context() -> dict:
            response = client.get("/api/v2/app/context")
            response.raise_for_status()
            return ContextSnapshot.model_validate(response.json()).model_dump(mode="json")

        def action(operation: str, arguments: dict | None = None) -> dict:
            state = context()
            index = len(trace) + 1
            request = {
                "schema_version": "2.0",
                "session_id": sid,
                "event_id": f"http-request-{index}",
                "turn_id": "http-smoke",
                "timestamp": datetime.now(UTC).isoformat(),
                "context_revision": state["revision"],
                "type": "agent.action_request",
                "payload": {
                    "action_id": f"http-{index}",
                    "operation": operation,
                    "arguments": arguments or {},
                },
            }
            response = client.post("/api/v2/app/action", json=request)
            response.raise_for_status()
            result = ActionResultEvent.model_validate(response.json()).model_dump(mode="json")
            assert result["reply_to"] == request["event_id"]
            assert result["payload"]["action_id"] == request["payload"]["action_id"]
            assert result["payload"]["status"] == "success", result
            trace.append({"request": request, "result": result})
            return result["payload"]

        action("navigate", {"target": "menu"})
        action("filter_menu", {"tags": ["vegetarian"], "max_price_pkr": 800})
        action("search_menu", {"query": "wrap"})
        action("select_item", {"item_id": "wrap-veg"})
        action("get_item_details", {"item_id": "wrap-veg"})
        action("cart.add_item", {"item_id": "wrap-hot-chicken", "quantity": 2})
        action("cart.set_quantity", {"item_id": "wrap-hot-chicken", "quantity": 1})
        action("cart.remove_item", {"item_id": "wrap-hot-chicken"})
        action("undo_last_reversible_action")
        assert action("get_cart")["verified_state"]["total"] == 900
        action("get_current_context")
        summary = action("checkout.get_summary")
        action(
            "checkout.submit_demo_order",
            {
                "confirmed": True,
                "confirmation_token": summary["confirmation_token"],
                "summary_revision": summary["verified_state"]["summary_revision"],
            },
        )
        receipt = trace[-1]["result"]
        before = context()
        lookup = client.get(
            "/api/v2/app/actions/http-13", headers={"X-FoodEase-Event-Id": "lookup-request"}
        )
        found = LookupResponse.model_validate(lookup.json())
        assert found.state == "found" and found.reply_to == "lookup-request"
        assert found.result is not None and found.result.model_dump(mode="json") == receipt
        assert client.post("/api/v2/app/action", json=trace[-1]["request"]).json() == receipt
        assert context() == before and not before["cart"]["lines"]
        assert stranger.get("/api/v2/app/context").json()["cart"]["lines"] == []
        assert (
            stranger.post("/api/v2/app/sessions/attach", json={"session_id": sid}).status_code
            == 403
        )
        assert (
            client.post("/api/v2/app/sessions/attach", json={"session_id": sid}).status_code == 200
        )
        assert client.get("/api/app/context").json() == before
        # Both entry points use the same canonical validator and revision gate.
        malformed = {
            "action_id": "bad",
            "operation": "cart.add_item",
            "arguments": {"item_id": "drink-cola", "quantity": True},
            "context_revision": before["revision"],
        }
        assert client.post("/api/app/action", json=malformed).status_code == 422

    redacted = copy.deepcopy(trace)
    for exchange in redacted:
        for event in exchange.values():
            payload = event["payload"]
            if "confirmation_token" in payload:
                payload["confirmation_token"] = (
                    "[redacted]" if payload["confirmation_token"] else None
                )
            if "confirmation_token" in payload.get("arguments", {}):
                payload["arguments"]["confirmation_token"] = "[redacted]"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {
                "mode": "actual-localhost-http",
                "operations": 13,
                "receipt_lookup": "pass",
                "session_isolation": "pass",
                "reload_attachment": "pass",
                "trace": redacted,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        "PASS real HTTP: 13 operations, isolated owners, reload attachment, receipt lookup/replay"
    )


if __name__ == "__main__":
    main()
