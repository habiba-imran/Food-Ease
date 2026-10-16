"""Local HTTP manual-operation smoke; this is NOT browser or voice evidence.

Requires a fresh, disposable standalone website on localhost:18080. No worker,
session service or provider is used. Never run against an existing shopper cart.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:18080")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    parsed = urlparse(args.base_url)
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"} or parsed.scheme != "http":
        raise ValueError("Only a disposable local HTTP website is supported")

    trace = []
    with httpx.Client(base_url=args.base_url, timeout=10, trust_env=False) as client:
        home = client.get("/")
        home.raise_for_status()
        assert "FoodEase" in home.text
        health = client.get("/healthz")
        health.raise_for_status()
        assert health.json()["service"] == "foodease-website"

        def snapshot() -> dict:
            response = client.get("/api/app/context")
            response.raise_for_status()
            return response.json()

        initial = snapshot()
        if initial["revision"] != 1 or initial["cart"]["lines"]:
            raise RuntimeError("Refusing to modify a non-fresh website domain; restart test server")

        def action(name: str, operation: str, arguments: dict | None = None) -> dict:
            before = snapshot()
            request = {
                "action_id": f"phase0-{name}",
                "operation": operation,
                "arguments": arguments or {},
                "context_revision": before["revision"],
            }
            response = client.post("/api/app/action", json=request)
            response.raise_for_status()
            result = response.json()
            assert result["action_id"] == request["action_id"]
            trace.append({"request": request, "result": result, "context": snapshot()})
            return result

        assert action("empty-checkout", "checkout.get_summary")["status"] == "rejected"
        assert action("menu", "navigate", {"target": "menu"})["status"] == "success"
        matches = action("filter", "filter_menu", {"tags": ["vegetarian"], "max_price_pkr": 800})
        items = matches["verified_state"]["items"]
        assert items and all(item["price"] <= 800 for item in items)
        assert all("vegetarian" in item["descriptors"] for item in items)
        assert action("clear", "filter_menu", {"tags": [], "category": None})["status"] == "success"
        assert action("search", "search_menu", {"query": "wrap"})["status"] == "success"
        selected = action("select", "select_item", {"item_id": "wrap-hot-chicken"})
        assert selected["status"] == "success"
        details = action("details", "get_item_details", {"item_id": "wrap-hot-chicken"})
        price = details["verified_state"]["price"]
        assert price == 850
        added = action("add", "cart.add_item", {"item_id": "wrap-hot-chicken", "quantity": 2})
        assert added["verified_state"]["lines"][0]["quantity"] == 2
        assert added["verified_state"]["total"] == 1750
        changed = action("quantity", "cart.set_quantity", {
            "item_id": "wrap-hot-chicken", "quantity": 1,
        })
        assert changed["verified_state"]["total"] == 900
        cart = action("cart", "get_cart")
        assert cart["verified_state"]["lines"][0]["quantity"] == 1
        summary = action("summary", "checkout.get_summary")
        assert summary["verified_state"]["total"] == 900
        submitted = action("submit", "checkout.submit_demo_order", {
            "confirmed": True, "confirmation_token": summary["confirmation_token"],
            "summary_revision": summary["verified_state"]["summary_revision"],
        })
        assert submitted["status"] == "success"
        assert submitted["verified_state"]["demo"] is True
        assert submitted["verified_state"]["order"]["total"] == 900
        repeated = action("submit", "checkout.submit_demo_order", {
            "confirmed": True, "confirmation_token": summary["confirmation_token"],
            "summary_revision": summary["verified_state"]["summary_revision"],
        })
        assert repeated == submitted
        final = snapshot()
        assert final["route"] == "confirmation" and final["cart"]["lines"] == []

    report = {
        "mode": "actual-website-http-only",
        "browser_verified": False,
        "voice_verified": False,
        "provider_calls": 0,
        "base_url": args.base_url,
        "result": "pass",
        "demo_order_id": submitted["verified_state"]["demo_order_id"],
        "total_pkr": 900,
        "trace": trace,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"PASS actual website HTTP order: {report['demo_order_id']}, PKR 900")
    print("Browser/microphone/voice not tested; no providers called.")


if __name__ == "__main__":
    main()
