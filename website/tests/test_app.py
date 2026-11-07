from fastapi.testclient import TestClient

from foodease_website.app import create_app


def test_healthz() -> None:
    client = TestClient(create_app())

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "foodease-website"}


def test_catalog_summary_route() -> None:
    client = TestClient(create_app())

    response = client.get("/api/catalog/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["currency"] == "PKR"
    assert body["item_count"] == 28
    assert body["service_fee_pkr"] == 50


def test_homepage_uses_ordering_design_language() -> None:
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert "Start ordering" in response.text
    assert "POPULAR PICKS" in response.text
    assert "FoodEase ordering assistance" in response.text
    assert '<span>FULL OF</span> <span>FLAVOURS.</span>' in response.text
    assert "/static/vendor/food-experience.css" in response.text
    assert "data-immersive-stage" in response.text
    assert "Project acceptance evidence" in response.text
