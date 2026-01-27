"""OpenAPI/Swagger contract smoke tests."""


def test_openapi_is_generated(client):
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    payload = resp.json()

    assert payload.get("openapi")
    info = payload.get("info") or {}
    assert info.get("title") == "AiutoX ERP API"

    paths = payload.get("paths") or {}

    # Core system
    assert "/healthz" in paths

    # Auth
    assert "/api/v1/auth/login" in paths

    # Business (a few key routes)
    assert "/api/v1/products" in paths
    assert "/api/v1/tasks/" in paths
    assert "/api/v1/calendar/calendars" in paths
