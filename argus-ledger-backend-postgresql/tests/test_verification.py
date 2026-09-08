"""Verification pipeline routes (app/integrations/router.py).

These assert the "nothing configured yet" contract: the routes answer 200 with a
structured body and the unavailable providers listed in ``warnings`` — the state
the project is in until the AI engineer ships an endpoint.
"""

from __future__ import annotations

import base64

# 1x1 transparent PNG.
_PNG_1x1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)

_RESULT_KEYS = {"status", "confidence", "claims", "sources", "media_analysis", "warnings", "engines"}


def test_verify_text_degrades_to_warnings(client):
    response = client.post("/verification/text", json={"text": "The sky is green today."})
    assert response.status_code == 200
    body = response.json()
    assert _RESULT_KEYS <= body.keys()
    assert isinstance(body["warnings"], list)
    assert body["status"] in {"INSUFFICIENT_EVIDENCE", "UNCERTAIN"}


def test_verify_text_body_required(client):
    assert client.post("/verification/text", json={}).status_code == 422


def test_verify_url_smoke(client):
    response = client.post(
        "/verification/url", json={"url": "https://example.com/article"}
    )
    assert response.status_code == 200
    assert "warnings" in response.json()


def test_verify_image_smoke(client):
    response = client.post(
        "/verification/image",
        files={"file": ("x.png", _PNG_1x1, "image/png")},
        data={"text": "optional context"},
    )
    assert response.status_code == 200
    body = response.json()
    assert _RESULT_KEYS <= body.keys()
    assert isinstance(body["media_analysis"], dict)
