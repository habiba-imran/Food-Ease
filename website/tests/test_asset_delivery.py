from fastapi.testclient import TestClient

from foodease_website.app import create_app


def test_versioned_images_are_cached_and_validate_without_a_body():
    client = TestClient(create_app())
    url = "/static/img/catalog-v7/zinger-classic-320.webp"
    response = client.get(url)
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/webp"
    assert response.headers["cache-control"] == "public, max-age=31536000, immutable"
    cached = client.get(url, headers={"If-None-Match": response.headers["etag"]})
    assert cached.status_code == 304
    assert not cached.content
    assert cached.headers["cache-control"] == response.headers["cache-control"]


def test_cache_policy_does_not_leak_to_html_or_missing_images():
    client = TestClient(create_app())
    homepage = client.get("/")
    assert "immutable" not in homepage.headers.get("cache-control", "")
    assert "set-cookie" in homepage.headers
    missing = client.get("/static/img/catalog-v7/missing.webp")
    assert missing.status_code == 404
    assert "immutable" not in missing.headers.get("cache-control", "")
    private = client.get("/api/app/context")
    assert private.headers["cache-control"] == "no-store"
