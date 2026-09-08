"""Pluggable engine surface (app/integrations/engines_router.py).

With an empty .env every engine is ``disabled`` and must degrade to a 200
response, never a 500.
"""

from __future__ import annotations

_ENGINE_NAMES = {"claim_classifier", "av_deepfake", "claim_extractor", "source_credibility"}


def test_engine_status_lists_all_four(client):
    response = client.get("/engines/status")
    assert response.status_code == 200
    engines = response.json()["engines"]
    assert set(engines) == _ENGINE_NAMES
    for name, meta in engines.items():
        assert meta["engine"] == name
        assert "mode" in meta
        assert "enabled" in meta


def test_disabled_engine_infer_returns_200(client, monkeypatch):
    for suffix in ("MODE", "URL", "API_KEY", "LOCAL", "PATH", "TIMEOUT_SECONDS"):
        monkeypatch.delenv(f"ARGUS_CLAIM_CLASSIFIER_{suffix}", raising=False)
    response = client.post("/engines/claim_classifier/infer", json={"text": "hello"})
    assert response.status_code == 200
    body = response.json()
    assert body["engine"] == "claim_classifier"
    assert body["enabled"] is False
    assert "needs" in body  # tells the caller which env vars to set


def test_unknown_engine_is_404(client):
    response = client.post("/engines/not_a_real_engine/infer", json={})
    assert response.status_code == 404
