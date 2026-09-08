"""Health check and CORS preflight (frontend integration)."""


def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "argus-api"
    assert body["database"] == "ok"


def test_root_points_at_docs(client):
    assert client.get("/").json()["docs"] == "/docs"


def test_cors_preflight_allows_frontend_origin(client):
    resp = client.options(
        "/decisions",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://localhost:5173"
